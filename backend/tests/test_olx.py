"""Testes offline da fonte OLX — não sobem navegador nem acessam a rede."""
import json

from backend.src.scraper.models import Condicao
from backend.src.scraper.sources import olx


def _pagina(anuncios: list[dict]) -> str:
    """Monta uma página como a da OLX: payload do Next.js em pedaços escapados."""
    corpo = json.dumps({"ads": anuncios}, ensure_ascii=False)
    # O payload real chega partido; o parser precisa remontar os pedaços.
    metade = len(corpo) // 2
    pedacos = [corpo[:metade], corpo[metade:]]
    scripts = "".join(
        f"<script>self.__next_f.push([1,{json.dumps(p, ensure_ascii=False)}])</script>"
        for p in pedacos
    )
    return f"<html><body>{scripts}</body></html>"


ANUNCIO = {
    "subject": "Mangá Berserk Ed. Luxo - Vol. 1 ",
    "priceValue": "R$ 40",
    "listId": 1543540670,
    "url": "https://sp.olx.com.br/sao-paulo/livros-e-revistas/manga-berserk-123456",
    "categoryName": "Livros e revistas",
    "images": [{"original": "https://img.olx.com.br/images/54/capa.jpg"}],
    "properties": [
        {"name": "category", "value": "Livros e revistas"},
        {"name": "hobbies_condition", "value": "Usado - Excelente"},
    ],
}


def test_remonta_payload_partido_e_le_anuncios():
    anuncios = olx._anuncios(_pagina([ANUNCIO]))

    assert len(anuncios) == 1
    assert anuncios[0]["subject"].strip() == "Mangá Berserk Ed. Luxo - Vol. 1"


def test_descarta_espacos_de_anuncio_sem_url():
    """A lista vem com entradas vazias que não são ofertas."""
    anuncios = olx._anuncios(_pagina([ANUNCIO, {"subject": "vazio"}, {}]))

    assert len(anuncios) == 1


def test_pagina_sem_payload_nao_quebra():
    assert olx._anuncios("<html><body>nada aqui</body></html>") == []
    assert olx._anuncios("") == []


def test_limpar_monta_item_completo():
    item = olx._limpar([ANUNCIO], {Condicao.USADO})[0]

    assert item["nome"] == "Mangá Berserk Ed. Luxo - Vol. 1"
    assert item["preco"] == "R$ 40"
    assert item["condicao"] is Condicao.USADO
    assert item["loja"] == olx.NOME
    assert item["link"] == ANUNCIO["url"]
    assert item["imagem"] == "https://img.olx.com.br/images/54/capa.jpg"


def test_condicao_vem_do_anuncio_e_nao_do_titulo():
    """A OLX declara a condição; não precisamos adivinhar pelo nome."""
    novo = {**ANUNCIO, "properties": [{"name": "hobbies_condition", "value": "Novo"}]}
    recondicionado = {**ANUNCIO,
                      "properties": [{"name": "hobbies_condition",
                                      "value": "Recondicionado"}]}

    assert olx._condicao(novo) is Condicao.NOVO
    assert olx._condicao(recondicionado) is Condicao.USADO


def test_sem_condicao_declarada_assume_usado():
    assert olx._condicao({**ANUNCIO, "properties": []}) is Condicao.USADO
    assert olx._condicao({}) is Condicao.USADO


def test_respeita_filtro_de_condicao():
    assert olx._limpar([ANUNCIO], {Condicao.NOVO}) == []
    assert len(olx._limpar([ANUNCIO], {Condicao.USADO})) == 1


def test_anuncio_sem_preco_e_descartado():
    assert olx._limpar([{**ANUNCIO, "priceValue": None}], {Condicao.USADO}) == []


def test_leitura_online_nao_aciona_a_fonte():
    """OLX não tem leitura online: pedir só ONLINE não sobe navegador."""
    assert olx.buscar("berserk", {Condicao.ONLINE}) == []


def test_desligada_por_padrao_e_ligavel(monkeypatch):
    """Fonte com navegador é opt-in: Chromium não cabe com folga em 1 GB."""
    monkeypatch.delenv("OLX_ENABLED", raising=False)
    assert not olx.habilitado()

    monkeypatch.setenv("OLX_ENABLED", "1")
    assert olx.habilitado()
