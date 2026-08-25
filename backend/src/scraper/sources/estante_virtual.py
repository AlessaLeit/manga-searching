"""Estante Virtual — livros novos e usados.

A busca é feita pela página de listagem, que vem renderizada no servidor
(HTML completo), então basta requests + BeautifulSoup, sem navegador.
O parâmetro `tipo-de-livro` permite pedir só novos ou só usados, o que torna
a condição um dado da própria fonte em vez de um palpite nosso.
"""
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


def _ofertas(card, tipo: str) -> int | None:
    """Lê "16 usados" / "13 novos" do bloco de variações do card."""
    for p in card.select(".product-item__variations__item"):
        texto = p.get_text(strip=True).lower()
        if tipo in texto and (m := re.search(r"(\d+)", texto)):
            return int(m.group(1))
    return None


def _extrair(html: str, condicao: Condicao, tipo: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    itens = []

    for card in soup.select("div.product-item"):
        nome = _texto(card.select_one(".product-item__name"))
        if not nome:
            continue

        link = card.select_one("a.product-item__link")
        href = link.get("href") if link else None

        itens.append({
            "nome": nome,
            "preco": _texto(card.select_one(".product-item__sale-price")),
            "loja": NOME,
            "condicao": condicao,
            "link": f"{BASE}{href}" if href and href.startswith("/") else href,
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
