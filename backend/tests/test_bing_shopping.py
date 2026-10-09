"""Testes offline da fonte Bing — não sobem navegador nem acessam a rede."""
import base64

from backend.src.scraper.models import Condicao
from backend.src.scraper.sources import bing_shopping


def _aclick(destino: str) -> str:
    """Monta um redirecionamento do Bing como os que vêm nos cards."""
    codificado = base64.b64encode(destino.encode()).decode()
    return f"https://www.bing.com/aclick?ld=abc&u={codificado}&rlid=xyz"


def test_decodifica_link_da_loja():
    destino = "https://www.amazon.com.br/One-Piece-Vol-3/dp/8573518936"

    assert bing_shopping.link_real(_aclick(destino)) == destino


def test_link_direto_passa_intacto():
    direto = "https://www.amazon.com.br/produto"

    assert bing_shopping.link_real(direto) == direto


def test_link_indecifravel_nao_quebra():
    """Preferimos devolver o link do Bing a perder a oferta inteira."""
    quebrado = "https://www.bing.com/aclick?ld=abc&u=%%%naoehbase64%%%"

    assert bing_shopping.link_real(quebrado).startswith("https://www.bing.com/aclick")
    assert bing_shopping.link_real("") is None


def test_ligada_por_padrao_e_desligavel(monkeypatch):
    monkeypatch.delenv("BING_SHOPPING_ENABLED", raising=False)
    assert bing_shopping.habilitado()

    monkeypatch.setenv("BING_SHOPPING_ENABLED", "0")
    assert not bing_shopping.habilitado()


def test_limpar_monta_item_completo():
    brutos = [{
        "nome": "One Piece Vol. 3",
        "preco": "R$ 31,40",
        "loja": "Amazon BR",
        "href": _aclick("https://www.amazon.com.br/dp/8573518936"),
        "texto": "One Piece Vol. 3 R$ 31,40 Amazon BR",
    }]

    item = bing_shopping._limpar(brutos, {Condicao.NOVO})[0]

    assert item["condicao"] is Condicao.NOVO
    assert item["loja"] == "Amazon BR"
    assert item["link"] == "https://www.amazon.com.br/dp/8573518936"
    # A chave auxiliar de inferência não vaza para o normalizer.
    assert "texto" not in item


def test_limpar_infere_usado_e_respeita_filtro():
    brutos = [{"nome": "One Piece Vol. 3", "preco": "R$ 12,00", "loja": None,
               "href": "", "texto": "One Piece Vol. 3 - produto usado"}]

    assert bing_shopping._limpar(brutos, {Condicao.USADO})[0]["condicao"] is Condicao.USADO
    assert bing_shopping._limpar(brutos, {Condicao.NOVO}) == []


def test_sem_loja_cai_para_a_propria_fonte():
    brutos = [{"nome": "One Piece", "preco": "R$ 10,00", "loja": None,
               "href": "", "texto": "One Piece R$ 10,00"}]

    assert bing_shopping._limpar(brutos, {Condicao.NOVO})[0]["loja"] == bing_shopping.NOME


def test_espera_exige_todas_as_capas():
    """Regressão: a espera parava na primeira capa e extraía cedo demais.

    Com ~8 de 20 miniaturas prontas no instante zero, a condição antiga já
    era satisfeita e a maioria das capas se perdia.
    """
    assert bing_shopping.PROPORCAO_CAPAS == 1.0
    # A condição conta cards com capa e compara com o total: exigir "alguma"
    # (querySelector != null) é justamente o que causava o bug.
    assert "cards.length" in bing_shopping._CAPAS_PRONTAS_JS
    assert "filter" in bing_shopping._CAPAS_PRONTAS_JS


def test_imagem_e_repassada_ao_normalizer():
    brutos = [{"nome": "One Piece Vol. 3", "preco": "R$ 31,40", "loja": "Amazon BR",
               "href": "", "imagem": "https://th.bing.com/th?id=OPHS.abc",
               "texto": "One Piece Vol. 3"}]

    assert bing_shopping._limpar(brutos, {Condicao.NOVO})[0]["imagem"] == (
        "https://th.bing.com/th?id=OPHS.abc"
    )


def test_item_sem_capa_nao_quebra():
    """Capa é opcional: a oferta vale pelo preço, mesmo sem miniatura."""
    brutos = [{"nome": "One Piece Vol. 3", "preco": "R$ 31,40", "loja": "Amazon BR",
               "href": "", "imagem": None, "texto": "One Piece Vol. 3"}]

    assert bing_shopping._limpar(brutos, {Condicao.NOVO})[0]["imagem"] is None


def test_leitura_online_nao_aciona_a_fonte():
    """Bing não tem leitura online: pedir só ONLINE não sobe navegador."""
    assert bing_shopping.buscar("one piece", {Condicao.ONLINE}) == []
