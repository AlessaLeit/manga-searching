"""MangaDex — leitura online.

API pública JSON, sem chave. Atende o requisito de "link para leitura
online, quando houver". Não tem preço: essas opções entram com preco=None.
"""
from .. import http
from ..models import Condicao

NOME = "MangaDex"
API = "https://api.mangadex.org/manga"
SITE = "https://mangadex.org/title"

# A API pede um User-Agent identificável.
_HEADERS = {"User-Agent": "MangaSearch/1.0 (projeto academico)"}


def _titulo(atributos: dict) -> str | None:
    """Prefere pt-br, depois en, depois qualquer idioma disponível."""
    titulos = atributos.get("title") or {}
    alternativos = {k: v for alt in atributos.get("altTitles", [])
                    for k, v in alt.items()}

    for idioma in ("pt-br", "pt", "en"):
        if titulos.get(idioma):
            return titulos[idioma]
        if alternativos.get(idioma):
            return alternativos[idioma]

    return next(iter(titulos.values()), None)


def buscar(query: str, condicoes: set[Condicao], limite: int = 10) -> list[dict]:
    if Condicao.ONLINE not in condicoes:
        return []

    r = http.get(API, headers=_HEADERS, params={
        "title": query,
        "limit": min(limite, 20),
        "availableTranslatedLanguage[]": "pt-br",
        "contentRating[]": "safe",
    })
    if r is None:
        return []

    try:
        dados = r.json().get("data", [])
    except ValueError:
        return []

    itens = []
    for manga in dados:
        atributos = manga.get("attributes", {})
        nome = _titulo(atributos)
        if not nome:
            continue

        itens.append({
            "nome": nome,
            "preco": None,
            "loja": NOME,
            "condicao": Condicao.ONLINE,
            "link": f"{SITE}/{manga['id']}",
            "autor": None,
            "ano": atributos.get("year"),
            "ofertas": None,
        })

    return itens
