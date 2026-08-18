"""Orquestrador da busca: consulta as fontes pré-definidas e consolida."""
from statistics import mean

from .models import Condicao, Produto, ResultadoBusca
from .normalizer import normalizar
from .sources import FONTES

TODAS_CONDICOES = {Condicao.NOVO, Condicao.USADO, Condicao.ONLINE}


def buscar_bruto(query: str, condicoes: set[Condicao] | None = None,
                 limite: int = 40) -> list[dict]:
    """Coleta itens crus de todas as fontes. Uma fonte que falha é ignorada."""
    return _coletar(query, condicoes or TODAS_CONDICOES, limite)[0]


def _coletar(query: str, condicoes: set[Condicao],
             limite: int) -> tuple[list[dict], list[str], list[str]]:
    itens: list[dict] = []
    consultadas: list[str] = []
    com_falha: list[str] = []

    for fonte in FONTES:
        try:
            encontrados = fonte.buscar(query, condicoes, limite)
        except Exception:
            # Uma loja fora do ar não pode derrubar a busca inteira.
            com_falha.append(fonte.NOME)
            continue

        consultadas.append(fonte.NOME)
        itens.extend(encontrados)

    return itens, consultadas, com_falha


def buscar(query: str, condicoes: set[Condicao] | None = None,
           limite: int = 40) -> ResultadoBusca:
    condicoes = condicoes or TODAS_CONDICOES
    itens, consultadas, com_falha = _coletar(query, condicoes, limite)
    opcoes = normalizar(itens, query)[:limite]

    return ResultadoBusca(
        manga=query,
        total_opcoes=len(opcoes),
        preco_minimo=_minimo(opcoes),
        preco_medio=_medio(opcoes),
        fontes_consultadas=consultadas,
        fontes_com_falha=com_falha,
        opcoes=opcoes,
    )


def _precos(opcoes: list[Produto]) -> list[float]:
    return [p.preco for p in opcoes if p.preco is not None]


def _minimo(opcoes: list[Produto]) -> float | None:
    precos = _precos(opcoes)
    return min(precos) if precos else None


def _medio(opcoes: list[Produto]) -> float | None:
    precos = _precos(opcoes)
    return round(mean(precos), 2) if precos else None
