"""Fontes pré-definidas de busca.

Cada fonte expõe `NOME` e `buscar(query, condicoes, limite) -> list[dict]`,
devolvendo dicionários crus que o normalizer converte em `Produto`.
"""
from . import estante_virtual, google_shopping, mangadex

FONTES = [estante_virtual, mangadex, google_shopping]

__all__ = ["FONTES", "estante_virtual", "google_shopping", "mangadex"]
