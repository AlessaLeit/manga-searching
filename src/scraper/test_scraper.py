"""Testes offline do parsing e da normalização (não fazem requisições)."""
from src.scraper.models import Condicao
from src.scraper.normalizer import _limpar_preco, e_relevante, normalizar
from src.scraper.sources import estante_virtual, google_shopping

HTML_CARD = """
<div class="product-list__items">
  <div class="product-item product-list__item">
    <a class="product-item__link" href="/livro/one-piece-vol-25-0BM"></a>
    <div class="product-item__info">
      <h2 class="product-item__title product-item__name">One Piece Vol. 25</h2>
      <p class="product-item__text product-item__author">Eiichiro Oda</p>
      <p class="product-item__text product-item__year">2024</p>
      <div class="product-item__buy-area">
        <div class="product-item__variations">
          <p class="product-item__variations__text product-item__variations__item">16 usados</p>
        </div>
        <p class="product-item__text">
          <span>A partir de</span>
          <span class="product-item__sale-price">R$&nbsp;21,25</span>
        </p>
      </div>
    </div>
  </div>
</div>
"""


def test_extrai_card_da_estante_virtual():
    itens = estante_virtual._extrair(HTML_CARD, Condicao.USADO, "usado")

    assert len(itens) == 1
    item = itens[0]
    assert item["nome"] == "One Piece Vol. 25"
    assert item["autor"] == "Eiichiro Oda"
    assert item["ano"] == 2024
    assert item["ofertas"] == 16
    assert item["condicao"] is Condicao.USADO
    assert item["link"] == (
        "https://www.estantevirtual.com.br/livro/one-piece-vol-25-0BM"
    )


def test_limpar_preco_formato_brasileiro():
    assert _limpar_preco("R$ 21,25") == 21.25
    assert _limpar_preco("R$ 1.234,56") == 1234.56
    assert _limpar_preco("R$ 90") == 90.0
    assert _limpar_preco(None) is None
    assert _limpar_preco("sob consulta") is None


def test_relevancia_descarta_resultado_aproximado():
    # A Estante Virtual devolve catálogo aleatório quando não acha nada.
    assert e_relevante("One Piece Vol. 25", "one piece")
    assert not e_relevante("Bzzz! O livro das onomatopeias", "one piece")


def test_normalizar_ordena_e_deixa_leitura_online_por_ultimo():
    brutos = [
        {"nome": "One Piece Vol. 2", "preco": "R$ 40,00", "loja": "EV",
         "condicao": Condicao.NOVO, "link": "a"},
        {"nome": "One Piece", "preco": None, "loja": "MangaDex",
         "condicao": Condicao.ONLINE, "link": "b"},
        {"nome": "One Piece Vol. 1", "preco": "R$ 20,00", "loja": "EV",
         "condicao": Condicao.USADO, "link": "c"},
    ]

    produtos = normalizar(brutos, "one piece")

    assert [p.preco for p in produtos] == [20.0, 40.0, None]
    assert produtos[-1].condicao is Condicao.ONLINE


def test_normalizar_descarta_compra_sem_preco_e_duplicatas():
    brutos = [
        {"nome": "One Piece Vol. 1", "preco": "R$ 20,00", "loja": "EV",
         "condicao": Condicao.USADO, "link": "c"},
        {"nome": "One Piece Vol. 1", "preco": "R$ 20,00", "loja": "EV",
         "condicao": Condicao.USADO, "link": "c"},
        {"nome": "One Piece Vol. 9", "preco": "indisponível", "loja": "EV",
         "condicao": Condicao.NOVO, "link": "d"},
    ]

    assert len(normalizar(brutos, "one piece")) == 1


def test_google_desligado_por_padrao(monkeypatch):
    """Sem a variável de ambiente a fonte não sobe navegador nenhum."""
    monkeypatch.delenv("GOOGLE_SHOPPING_ENABLED", raising=False)
    assert not google_shopping.habilitado()
    assert google_shopping.buscar("one piece", {Condicao.NOVO}) == []

    monkeypatch.setenv("GOOGLE_SHOPPING_ENABLED", "1")
    assert google_shopping.habilitado()


def test_google_infere_condicao_e_preenche_campos():
    brutos = [
        {"nome": "One Piece Vol. 1", "preco": "R$ 25,90", "loja": "Amazon",
         "link": "http://x", "texto": "One Piece Vol. 1 R$ 25,90 Amazon"},
        {"nome": "One Piece Vol. 2 - usado", "preco": "R$ 12,00", "loja": None,
         "link": "http://y", "texto": "One Piece Vol. 2 - usado R$ 12,00"},
    ]

    limpos = google_shopping._limpar(brutos, {Condicao.NOVO, Condicao.USADO})

    assert [i["condicao"] for i in limpos] == [Condicao.NOVO, Condicao.USADO]
    # Sem nome de loja no card, cai para a própria fonte.
    assert limpos[1]["loja"] == google_shopping.NOME
    # A chave auxiliar de inferência não vaza para o normalizer.
    assert "texto" not in limpos[0]


def test_google_respeita_filtro_de_condicao():
    brutos = [{"nome": "One Piece usado", "preco": "R$ 12,00", "loja": None,
               "link": "http://y", "texto": "One Piece usado"}]

    assert google_shopping._limpar(brutos, {Condicao.NOVO}) == []
