"""Fontes pré-definidas de busca.

Cada fonte expõe `NOME` e `buscar(query, condicoes, limite) -> list[dict]`,
devolvendo dicionários crus que o normalizer converte em `Produto`.
"""
from . import bing_shopping, estante_virtual, google_shopping, mangadex

# Ordem = ordem de consulta. As que respondem por HTTP simples vêm primeiro;
# as que sobem navegador (custam segundos) ficam no fim.
FONTES = [estante_virtual, mangadex, bing_shopping, google_shopping]

__all__ = [
    "FONTES",
    "bing_shopping",
    "estante_virtual",
    "google_shopping",
    "mangadex",
]
