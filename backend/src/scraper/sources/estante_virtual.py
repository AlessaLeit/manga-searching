"""Estante Virtual — livros novos e usados.

A busca é feita pela página de listagem, que vem renderizada no servidor
(HTML completo), então basta requests + BeautifulSoup, sem navegador.
O parâmetro `tipo-de-livro` permite pedir só novos ou só usados, o que torna
a condição um dado da própria fonte em vez de um palpite nosso.
"""
import json
import re

from bs4 import BeautifulSoup

from .. import http
from ..models import Condicao

NOME = "Estante Virtual"
BASE = "https://www.estantevirtual.com.br"
BUSCA = f"{BASE}/busca"

_TIPO_POR_CONDICAO = {Condicao.NOVO: "novo", Condicao.USADO: "usado"}


def _texto(no) -> str | None:
    return no.get_text(strip=True) if no else None


def _ano(card) -> int | None:
    bruto = _texto(card.select_one(".product-item__year"))
    if bruto and (m := re.search(r"(\d{4})", bruto)):
        return int(m.group(1))
    return None


_ESTADO = "__INITIAL_STATE__="
_CARREGANDO = "livro-loading"


def _chave_nome(nome: str) -> str:
    """Normaliza o título para casar card e estado embutido."""
    return " ".join(nome.lower().split())


def _produtos_embutidos(html: str) -> tuple[dict[str, dict], dict[str, dict]]:
    """Dados do estado embutido, indexados por slug e por nome.

    Indexar também por nome é o que resgata os produtos agrupados: esses cards
    vêm sem `<a>` nenhum (a Estante monta o link por JavaScript), então não há
    href para casar — mas o título bate exatamente com o `name` do estado.

    As <img> do HTML servido trazem todas o mesmo gif de carregamento: a
    Estante usa lazy loading (`v-lazy-image`), e a URL real só é escrita pelo
    JavaScript quando a imagem entra na tela — o que nunca acontece aqui,
    porque lemos o HTML cru, sem navegador.

    A URL existe, porém, no JSON que a página embute para hidratar o Vue
    (`__INITIAL_STATE__`). Ler de lá evita subir um Chromium só por causa da
    capa. O `productSlug` de cada produto é idêntico ao href do card, e é
    isso que usamos para casar os dois.
    """
    inicio = html.find(_ESTADO)
    if inicio == -1:
        return {}, {}

    try:
        # raw_decode lê só o objeto JSON e ignora o resto do script.
        estado, _ = json.JSONDecoder().raw_decode(html[inicio + len(_ESTADO):])
    except ValueError:
        return {}, {}

    por_slug: dict[str, dict] = {}
    por_nome: dict[str, dict] = {}

    for produto in estado.get("SearchPage", {}).get("parentSkus", []):
        dados = {"imagem": produto.get("image"),
                 "slug": produto.get("productSlug")}
        if dados["slug"]:
            por_slug[dados["slug"]] = dados
        if produto.get("name"):
            por_nome[_chave_nome(produto["name"])] = dados

    return por_slug, por_nome


def _imagem_do_card(card) -> str | None:
    """Reserva, caso a estrutura do estado mude.

    Só serve se a `<img>` já não for o gif de carregamento — a Estante usa
    lazy loading, então no HTML cru quase sempre é.
    """
    img = card.select_one("img")
    src = img.get("src") if img else None
    return src if src and _CARREGANDO not in src else None


def _ofertas(card, tipo: str) -> int | None:
    """Lê "16 usados" / "13 novos" do bloco de variações do card."""
    for p in card.select(".product-item__variations__item"):
        texto = p.get_text(strip=True).lower()
        if tipo in texto and (m := re.search(r"(\d+)", texto)):
            return int(m.group(1))
    return None


def _extrair(html: str, condicao: Condicao, tipo: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    # Uma leitura só do estado embutido, reaproveitada por todos os cards.
    por_slug, por_nome = _produtos_embutidos(html)
    itens = []

    for card in soup.select("div.product-item"):
        nome = _texto(card.select_one(".product-item__name"))
        if not nome:
            continue

        link = card.select_one("a.product-item__link")
        href = link.get("href") if link else None
        dados = por_slug.get(href) or por_nome.get(_chave_nome(nome)) or {}

        # Card de produto agrupado não traz `<a>`: o slug do estado é a única
        # fonte do link, senão a oferta chegaria ao usuário sem para onde ir.
        href = href or dados.get("slug")

        itens.append({
            "nome": nome,
            "preco": _texto(card.select_one(".product-item__sale-price")),
            "loja": NOME,
            "condicao": condicao,
            "link": f"{BASE}{href}" if href and href.startswith("/") else href,
            "imagem": dados.get("imagem") or _imagem_do_card(card),
            "autor": _texto(card.select_one(".product-item__author")),
            "ano": _ano(card),
            "ofertas": _ofertas(card, tipo),
        })

    return itens


def buscar(query: str, condicoes: set[Condicao], limite: int = 40) -> list[dict]:
    alvos = [c for c in (Condicao.NOVO, Condicao.USADO) if c in condicoes]
    if not alvos:
        return []

    # Divide a cota entre as condições pedidas para não estourar o limite.
    por_condicao = max(1, limite // len(alvos))
    itens: list[dict] = []

    for condicao in alvos:
        tipo = _TIPO_POR_CONDICAO[condicao]
        r = http.get(BUSCA, params={"q": query, "tipo-de-livro": tipo})
        if r is None:
            continue
        itens.extend(_extrair(r.text, condicao, tipo)[:por_condicao])

    return itens
