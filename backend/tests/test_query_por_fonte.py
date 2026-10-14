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


class _FonteComOferta:
    """Fonte que devolve uma oferta, para checar o carimbo da origem."""

    def __init__(self, nome, loja, link):
        self.NOME = nome
        self._loja = loja
        self._link = link

    def buscar(self, query, condicoes, limite):
        return [{"nome": "Berserk Vol. 1", "preco": "R$ 30,00",
                 "loja": self._loja, "condicao": Condicao.USADO,
                 "link": self._link}]


def test_orquestrador_carimba_a_fonte_de_cada_oferta(monkeypatch):
    """`fonte` diz de onde veio; `loja` diz quem vende. São coisas diferentes.

    "panini" parece editora mas é vendedor da Enjoei, e "Amazon BR" chega pelo
    Bing — sem este campo não dava para distinguir a origem no front.
    """
    # Links distintos: mesmo título e condição com o mesmo link seriam
    # deduplicados, e sobraria uma oferta só.
    monkeypatch.setattr(scraper, "FONTES", [
        _FonteComOferta("Enjoei", "panini", "https://enjoei.com.br/p/1"),
        _FonteComOferta("Bing Shopping", "Amazon BR", "https://amazon.com.br/dp/1"),
    ])

    resultado = scraper.buscar("berserk", {Condicao.USADO})

    origens = {(o.fonte, o.loja) for o in resultado.opcoes}
    assert origens == {("Enjoei", "panini"), ("Bing Shopping", "Amazon BR")}


def test_sem_query_relevancia_todas_recebem_a_mesma(monkeypatch):
    loja = _FonteFalsa("Loja")
    catalogo = _FonteFalsa("Catalogo", usa_query_limpa=True)
    monkeypatch.setattr(scraper, "FONTES", [loja, catalogo])

    scraper.buscar("berserk", {Condicao.NOVO})

    assert loja.recebido == catalogo.recebido == "berserk"
