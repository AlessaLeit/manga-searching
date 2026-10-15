"""Testes offline do scraper Enjoei: sem navegador e sem rede."""
from urllib.parse import parse_qs, urlsplit

from backend.src.scraper.models import Condicao
from backend.src.scraper.sources import enjoei


def test_url_busca_usa_slug_e_query_sem_filtros_de_paginacao():
    url = enjoei._url_busca("livro manga Demon Slayer 1")
    partes = urlsplit(url)

    assert partes.path == "/livro-manga-demon-slayer-1/s"
    assert parse_qs(partes.query) == {
        "ref": ["products_search"],
        "q": ["livro manga Demon Slayer 1"],
    }


def test_condicao_sem_marcador_fica_como_usado():
    assert enjoei._condicao("mangá demon slayer volume 1") is Condicao.USADO
    assert enjoei._condicao("produto novo com etiqueta") is Condicao.NOVO


def test_limpar_monta_anuncio_completo_e_remove_tracking_do_link():
    brutos = [{
        "nome": "Demon Slayer Vol. 1",
        "preco": "R$ 20",
        "loja": "brechó da ana",
        "href": "/p/demon-slayer-1-123?sid=tracking",
        "imagem": "https://photos.enjoei.com.br/capa.jpg",
        "texto": "Demon Slayer Vol. 1\nR$ 20\nnovo com etiqueta",
    }]

    item = enjoei._limpar(brutos, {Condicao.NOVO})[0]

    assert item["nome"] == "Demon Slayer Vol. 1"
    assert item["preco"] == "R$ 20"
    assert item["loja"] == "brechó da ana"
    assert item["condicao"] is Condicao.NOVO
    assert item["link"] == "https://www.enjoei.com.br/p/demon-slayer-1-123"
    assert item["imagem"] == "https://photos.enjoei.com.br/capa.jpg"


def test_limpar_assume_usado_e_respeita_filtro():
    brutos = [{
        "nome": "Mangá usado",
        "preco": "R$ 18",
        "href": "/p/manga-usado-456",
        "texto": "Mangá usado",
    }]

    item = enjoei._limpar(brutos, {Condicao.USADO})[0]

    assert item["condicao"] is Condicao.USADO
    assert enjoei._limpar(brutos, {Condicao.NOVO}) == []
    assert enjoei._limpar(brutos, {Condicao.ONLINE}) == []


def test_rejeita_links_que_nao_sao_anuncios_da_enjoei():
    brutos = [{
        "nome": "Mangá",
        "preco": "R$ 18",
        "href": "https://exemplo.com/p/manga-456",
        "texto": "Mangá",
    }]

    item = enjoei._limpar(brutos, {Condicao.USADO})[0]

    assert item["link"] is None


def test_desligada_por_padrao_e_ligavel(monkeypatch):
    """Fonte com navegador é opt-in: Chromium não cabe com folga em 1 GB."""
    monkeypatch.delenv("ENJOEI_ENABLED", raising=False)

    assert not enjoei.habilitado()
    # Desligada, não sobe navegador nem acessa a rede.
    assert enjoei.buscar("manga", {Condicao.USADO}) == []

    monkeypatch.setenv("ENJOEI_ENABLED", "1")
    assert enjoei.habilitado()
