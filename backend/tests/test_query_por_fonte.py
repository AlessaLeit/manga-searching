"""Qual expressão cada fonte recebe: prefixada ou original."""
from backend.src.scraper import scraper
from backend.src.scraper.models import Condicao
from backend.src.scraper.sources import estante_virtual, mangadex


class _FonteFalsa:
    """Fonte mínima que só registra o termo recebido."""

    def __init__(self, nome, usa_query_limpa=False):
        self.NOME = nome
        self.recebido = None
        if usa_query_limpa:
            self.USA_QUERY_LIMPA = True

    def buscar(self, query, condicoes, limite):
        self.recebido = query
        return []


def test_mangadex_pede_query_limpa_e_lojas_nao():
    """O MangaDex casa por título: "livro manga X" não é obra nenhuma."""
    assert getattr(mangadex, "USA_QUERY_LIMPA", False)
    assert not getattr(estante_virtual, "USA_QUERY_LIMPA", False)


def test_cada_fonte_recebe_a_expressao_que_pediu(monkeypatch):
    """Regressão: o prefixo ia para todas as fontes e zerava o MangaDex."""
    loja = _FonteFalsa("Loja")
    catalogo = _FonteFalsa("Catalogo", usa_query_limpa=True)
    monkeypatch.setattr(scraper, "FONTES", [loja, catalogo])

    scraper.buscar("livro manga berserk", {Condicao.NOVO},
                   query_relevancia="berserk")

    assert loja.recebido == "livro manga berserk"
    assert catalogo.recebido == "berserk"


def test_sem_query_relevancia_todas_recebem_a_mesma(monkeypatch):
    loja = _FonteFalsa("Loja")
    catalogo = _FonteFalsa("Catalogo", usa_query_limpa=True)
    monkeypatch.setattr(scraper, "FONTES", [loja, catalogo])

    scraper.buscar("berserk", {Condicao.NOVO})

    assert loja.recebido == catalogo.recebido == "berserk"
