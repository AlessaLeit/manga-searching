"""Teste de fumaça: as fontes ainda estão trazendo resultado dos sites reais?

A suíte offline protege a lógica — preço, relevância, condição, contrato. Ela
não enxerga o que mais quebra um scraper: o site do outro lado mudar. Quando a
Estante Virtual troca o nome de uma classe ou a Enjoei muda a grade, os 62
testes continuam verdes e a busca volta vazia em produção.

Foi exatamente assim que a Enjoei ficou zerada sem ninguém notar: a fonte
devolvia lista vazia, sem erro, e aparecia em `fontes_consultadas` como se
tivesse respondido normalmente.

Estes testes acessam a internet de verdade. Por isso ficam fora da suíte padrão
(veja `pytest.ini`) e não rodam no CI. Rode sob demanda:

    pytest -m fumaca -v

Falha aqui quase nunca é bug nosso de lógica: é sinal de que uma fonte parou de
responder e precisa de conserto. A mensagem de cada teste diz qual.
"""
import pytest

from backend.src.scraper import buscar
from backend.src.scraper.models import Condicao
from backend.src.scraper.normalizer import _limpar_preco
from backend.src.scraper.sources import (
    bing_shopping,
    enjoei,
    estante_virtual,
    mangadex,
    olx,
)

pytestmark = pytest.mark.fumaca

# Expressão enriquecida que a rota monta, e a original que o MangaDex recebe.
BUSCA_LOJAS = "livro manga berserk"
BUSCA_LIMPA = "berserk"

COMPRA = {Condicao.NOVO, Condicao.USADO}

# Uma fonte saudável traz muito mais que isto; o piso é baixo de propósito,
# para acusar só o colapso de verdade e não a variação normal do catálogo.
MINIMO_DE_ITENS = 3

FONTES_DE_COMPRA = [
    pytest.param(estante_virtual, BUSCA_LOJAS, COMPRA, id="estante_virtual"),
    pytest.param(bing_shopping, BUSCA_LOJAS, COMPRA, id="bing_shopping"),
    pytest.param(enjoei, BUSCA_LOJAS, COMPRA, id="enjoei"),
    pytest.param(olx, BUSCA_LOJAS, COMPRA, id="olx"),
    pytest.param(mangadex, BUSCA_LIMPA, {Condicao.ONLINE}, id="mangadex"),
]


# Cada fonte é consultada UMA vez e o resultado é reaproveitado pelos quatro
# testes. Sem isto seriam 20 consultas e uma dúzia de navegadores — um teste de
# fumaça que demora não é rodado por ninguém.
_cache: dict[str, list[dict]] = {}


def _itens(fonte, query, condicoes) -> list[dict]:
    if fonte.NOME not in _cache:
        _cache[fonte.NOME] = fonte.buscar(query, condicoes, 10)
    return _cache[fonte.NOME]


@pytest.mark.parametrize("fonte, query, condicoes", FONTES_DE_COMPRA)
def test_fonte_ainda_traz_resultado(fonte, query, condicoes):
    """O essencial: a fonte continua devolvendo ofertas."""
    itens = _itens(fonte, query, condicoes)

    assert len(itens) >= MINIMO_DE_ITENS, (
        f"{fonte.NOME} devolveu {len(itens)} item(ns) para {query!r}. "
        "A fonte provavelmente parou de funcionar — confira se o site mudou "
        "de layout, de URL ou passou a bloquear o acesso."
    )


@pytest.mark.parametrize("fonte, query, condicoes", FONTES_DE_COMPRA)
def test_campos_essenciais_preenchidos(fonte, query, condicoes):
    """Trazer item não basta: sem nome e link a oferta é inútil ao usuário."""
    itens = _itens(fonte, query, condicoes)
    assert itens, f"{fonte.NOME} não devolveu nada — veja o teste anterior."

    sem_nome = [i for i in itens if not (i.get("nome") or "").strip()]
    sem_link = [i for i in itens if not i.get("link")]

    assert not sem_nome, f"{fonte.NOME}: {len(sem_nome)} item(ns) sem nome."
    assert not sem_link, (
        f"{fonte.NOME}: {len(sem_link)} de {len(itens)} item(ns) sem link. "
        "O usuário não tem para onde clicar."
    )


@pytest.mark.parametrize("fonte, query, condicoes", FONTES_DE_COMPRA)
def test_precos_convertem_para_valor_plausivel(fonte, query, condicoes):
    """Pega o erro que os testes offline não pegam: formato novo de preço.

    Regressão: a OLX anuncia "R$ 1.300" e isso virava R$ 1,30, colocando um
    box de 33 volumes no topo da lista ordenada por preço.
    """
    itens = _itens(fonte, query, condicoes)
    assert itens, f"{fonte.NOME} não devolveu nada — veja o primeiro teste."

    if fonte is mangadex:
        pytest.skip("leitura online não tem preço")

    for item in itens:
        preco = _limpar_preco(item.get("preco"))
        assert preco is not None, (
            f"{fonte.NOME}: preço {item.get('preco')!r} não virou número. "
            "O site deve ter mudado o formato."
        )
        assert 1 <= preco <= 50_000, (
            f"{fonte.NOME}: {item['nome'][:40]!r} saiu por R$ {preco}. "
            "Valor implausível para mangá — suspeite da conversão de preço."
        )


@pytest.mark.parametrize("fonte, query, condicoes", FONTES_DE_COMPRA)
def test_imagens_sao_urls_utilizaveis(fonte, query, condicoes):
    """Capa é opcional, mas URL quebrada ou placeholder não serve ao card."""
    itens = _itens(fonte, query, condicoes)
    assert itens, f"{fonte.NOME} não devolveu nada — veja o primeiro teste."

    for item in itens:
        imagem = item.get("imagem")
        if not imagem:
            continue
        assert imagem.startswith(("http://", "https://")), (
            f"{fonte.NOME}: imagem {imagem[:60]!r} não é URL http."
        )
        assert "loading" not in imagem.lower(), (
            f"{fonte.NOME}: capa é o placeholder de carregamento, não a capa "
            "real. A espera pela imagem deve ter deixado de funcionar."
        )


def test_busca_completa_reune_as_fontes():
    """O caminho que o usuário percorre, ponta a ponta."""
    resultado = buscar(BUSCA_LOJAS, limite=40, query_relevancia=BUSCA_LIMPA)

    assert not resultado.fontes_com_falha, (
        f"Fontes falharam: {resultado.fontes_com_falha}. "
        "Veja o log do servidor para o motivo."
    )
    assert resultado.total_opcoes >= 10, (
        f"A busca completa trouxe só {resultado.total_opcoes} opções."
    )
    assert resultado.preco_minimo and resultado.preco_minimo >= 1, (
        f"Preço mínimo implausível: {resultado.preco_minimo}."
    )

    # Mais de uma fonte precisa estar contribuindo: se só uma responde, as
    # outras quebraram em silêncio e o total ainda assim parece saudável.
    lojas = {opcao.loja for opcao in resultado.opcoes}
    assert len(lojas) >= 2, f"Só uma origem contribuiu: {lojas}."


def test_busca_sem_sentido_nao_inventa_resultado():
    """A Estante Virtual e a Enjoei caem em busca aproximada quando não acham.

    Sem o filtro de relevância, o usuário recebia catálogo aleatório — uma vez
    apareceu "California Nevada Tourbook" numa busca por mangá.
    """
    resultado = buscar("livro manga xyzabc naoexiste 999", limite=20,
                       query_relevancia="xyzabc naoexiste 999")

    assert resultado.total_opcoes == 0, (
        f"Busca sem sentido devolveu {resultado.total_opcoes} opções: "
        f"{[o.nome for o in resultado.opcoes[:3]]}. "
        "O filtro de relevância deve ter afrouxado."
    )
