"""Testes da rota /search — sem rede: o scraper é substituído por um espião."""
import pytest
from fastapi.testclient import TestClient

import backend.src.routes.search as rota
from backend.src.main import app
from backend.src.scraper.models import Condicao, ResultadoBusca

client = TestClient(app)


@pytest.fixture
def condicoes_recebidas(monkeypatch):
    """Captura as condições que a rota repassa ao scraper."""
    capturado = {}

    def espiao(query, condicoes, *args, **kwargs):
        capturado["condicoes"] = {c.value for c in condicoes}
        capturado["query"] = query
        return ResultadoBusca(manga=query, total_opcoes=0)

    monkeypatch.setattr(rota, "buscar", espiao)
    return capturado


def test_filtro_chega_ao_scraper(condicoes_recebidas):
    """Regressão: o filtro já foi ignorado em silêncio, buscando tudo sempre."""
    r = client.get("/search/", params={"search_expression": "berserk",
                                       "filters": ["usado"]})

    assert r.status_code == 200
    assert condicoes_recebidas["condicoes"] == {"usado"}


def test_multiplos_filtros(condicoes_recebidas):
    client.get("/search/", params={"search_expression": "berserk",
                                   "filters": ["usado", "online"]})

    assert condicoes_recebidas["condicoes"] == {"usado", "online"}


def test_sem_filtro_busca_todas_as_condicoes(condicoes_recebidas):
    client.get("/search/", params={"search_expression": "berserk"})

    assert condicoes_recebidas["condicoes"] == {c.value for c in Condicao}


def test_query_e_repassada_sem_espacos(condicoes_recebidas):
    client.get("/search/", params={"search_expression": "  berserk  "})

    assert condicoes_recebidas["query"] == "berserk"


@pytest.mark.parametrize("params", [
    {"search_expression": ""},
    {"search_expression": "berserk", "filters": ["xpto"]},
    {},
])
def test_entradas_invalidas_dao_422(params):
    assert client.get("/search/", params=params).status_code == 422
