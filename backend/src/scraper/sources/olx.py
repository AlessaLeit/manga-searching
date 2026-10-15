"""OLX — anúncios de pessoas e lojas, novos e usados.

Duas descobertas definiram esta implementação:

1. A OLX responde 403 (Cloudflare) para `requests`. Só com navegador real o
   acesso passa, então a fonte usa o Playwright compartilhado.
2. A grade de resultados é virtualizada: os cards fora da tela são desmontados
   do DOM. Medindo, rolar a página fazia a contagem subir de 5 para 13 e cair
   de volta para 2 — raspar o DOM nunca veria os 50 anúncios.

A saída é ler o payload que o Next.js embute na página (`self.__next_f.push`),
que traz os anúncios estruturados: título, preço, link, imagem e — melhor que
qualquer inferência nossa — a condição declarada pelo anunciante.
"""
import json
import os
import urllib.parse as urlparse

from .. import navegador
from ..models import Condicao

NOME = "OLX"
BUSCA = "https://www.olx.com.br/brasil"

# Sobe um Chromium: o orquestrador consulta estas por último e dentro
# de uma sessão compartilhada, porque memória é o recurso escasso.
USA_NAVEGADOR = True


# Trecho que inicia cada pedaço do payload do Next.js.
_MARCA = 'self.__next_f.push([1,'
_CHAVE_ANUNCIOS = '"ads":'
# Propriedade do anúncio que carrega a condição declarada pelo anunciante.
_PROP_CONDICAO = "hobbies_condition"


# Link de anúncio da OLX termina com o id numérico ("...-1543540670").
_TEM_ANUNCIOS_JS = r"""
() => [...document.querySelectorAll('a[href]')]
        .some((a) => /olx\.com\.br\/.*-\d{6,}/.test(a.href))
"""


def habilitado() -> bool:
    """Ligada por padrão; desligue com OLX_ENABLED=0."""
    return os.getenv("OLX_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "nao", "não",
    }


def _payload(html: str) -> str:
    """Remonta o payload do Next.js, desescapando cada pedaço.

    Os pedaços chegam como strings JSON escapadas dentro de chamadas de
    script, então `raw_decode` em cada uma devolve o texto original.
    """
    decodificador = json.JSONDecoder()
    partes = []
    posicao = 0

    while (inicio := html.find(_MARCA, posicao)) != -1:
        aspas = html.find('"', inicio)
        if aspas == -1:
            break
        try:
            texto, fim = decodificador.raw_decode(html[aspas:])
        except ValueError:
            posicao = inicio + len(_MARCA)
            continue
        partes.append(texto)
        posicao = aspas + fim

    return "".join(partes)


def _anuncios(html: str) -> list[dict]:
    payload = _payload(html)
    inicio = payload.find(_CHAVE_ANUNCIOS)
    if inicio == -1:
        return []

    # `raw_decode` não tolera espaço à frente, e a OLX hoje serializa sem
    # espaço — mas depender disso deixaria o parser refém da formatação.
    resto = payload[inicio + len(_CHAVE_ANUNCIOS):].lstrip()

    try:
        anuncios, _ = json.JSONDecoder().raw_decode(resto)
    except ValueError:
        return []

    # A lista traz entradas vazias (espaços de anúncio): sem url não há oferta.
    return [a for a in anuncios if isinstance(a, dict) and a.get("url")]


def _condicao(anuncio: dict) -> Condicao:
    """Lê a condição declarada: "Novo", "Usado - Bom", "Recondicionado"...

    Sem a propriedade, assume usado — é o padrão de um classificado.
    """
    for propriedade in anuncio.get("properties") or []:
        if propriedade.get("name") == _PROP_CONDICAO:
            valor = (propriedade.get("value") or "").strip().lower()
            return Condicao.NOVO if valor.startswith("novo") else Condicao.USADO
    return Condicao.USADO


def _imagem(anuncio: dict) -> str | None:
    for imagem in anuncio.get("images") or []:
        if url := imagem.get("original"):
            return url
    return None


def _limpar(anuncios: list[dict], condicoes: set[Condicao]) -> list[dict]:
    itens = []
    for anuncio in anuncios:
        nome = (anuncio.get("subject") or "").strip()
        preco = anuncio.get("priceValue")
        if not nome or not preco:
            continue

        condicao = _condicao(anuncio)
        if condicao not in condicoes:
            continue

        itens.append({
            "nome": nome,
            "preco": preco,
            # Classificado não tem nome de loja; identificar o marketplace é
            # mais útil ao usuário do que o apelido de quem anuncia.
            "loja": NOME,
            "condicao": condicao,
            "link": anuncio.get("url"),
            "imagem": _imagem(anuncio),
            "autor": None,
            "ano": None,
            "ofertas": None,
        })

    return itens


def buscar(query: str, condicoes: set[Condicao], limite: int = 20) -> list[dict]:
    if not ({Condicao.NOVO, Condicao.USADO} & condicoes):
        return []

    with navegador.pagina() as page:
        page.goto(
            f"{BUSCA}?{urlparse.urlencode({'q': query})}",
            timeout=navegador.TIMEOUT_MS,
            wait_until="domcontentloaded",
        )

        # Espera os anúncios existirem no DOM. Note o `attached`: a grade é
        # virtualizada e o primeiro card pode não estar visível, caso em que
        # esperar por visibilidade estouraria com a página já carregada.
        # Busca sem resultado é resposta vazia legítima, não erro.
        try:
            page.wait_for_function(_TEM_ANUNCIOS_JS, timeout=10_000)
        except Exception:
            return []

        html = page.content()

    return _limpar(_anuncios(html), condicoes)[:limite]
