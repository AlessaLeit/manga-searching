"""Orquestrador da busca: consulta as fontes pré-definidas e consolida."""
import logging
from statistics import mean

from .models import Condicao, Produto, ResultadoBusca
from .normalizer import normalizar
from .sources import FONTES

logger = logging.getLogger(__name__)

TODAS_CONDICOES = {Condicao.NOVO, Condicao.USADO, Condicao.ONLINE}


def buscar_bruto(query: str, condicoes: set[Condicao] | None = None,
                 limite: int = 40) -> list[dict]:
    """Coleta itens crus de todas as fontes. Uma fonte que falha é ignorada."""
    return _coletar(query, condicoes or TODAS_CONDICOES, limite)[0]


def _coletar(query: str, condicoes: set[Condicao], limite: int,
             query_limpa: str | None = None
             ) -> tuple[list[dict], list[str], list[str]]:
    itens: list[dict] = []
    consultadas: list[str] = []
    com_falha: list[str] = []

    for fonte in FONTES:
        # Fonte opcional desligada não é "consultada": omiti-la evita relatar
        # uma busca mais ampla do que a que realmente aconteceu.
        if not getattr(fonte, "habilitado", lambda: True)():
            continue

        # Lojas se beneficiam do contexto "livro manga" na busca; catálogos
        # que casam por título exato, não — para o MangaDex, "livro manga
        # berserk" não é nenhuma obra e a busca voltava vazia.
        usa_limpa = getattr(fonte, "USA_QUERY_LIMPA", False)
        termo = query_limpa if (usa_limpa and query_limpa) else query

        try:
            encontrados = fonte.buscar(termo, condicoes, limite)
        except Exception:
            # Uma loja fora do ar não pode derrubar a busca inteira. Mas o
            # motivo precisa ficar no log: sem isto, a fonte só aparece em
            # `fontes_com_falha` e não há como saber se foi timeout, bloqueio
            # do site ou erro nosso.
            logger.warning("fonte %s falhou", fonte.NOME, exc_info=True)
            com_falha.append(fonte.NOME)
            continue

        consultadas.append(fonte.NOME)
        itens.extend(encontrados)

    return itens, consultadas, com_falha


def buscar(query: str, condicoes: set[Condicao] | None = None,
           limite: int = 40, *,
           query_relevancia: str | None = None) -> ResultadoBusca:
    condicoes = condicoes or TODAS_CONDICOES
    expressao_relevancia = query if query_relevancia is None else query_relevancia
    itens, consultadas, com_falha = _coletar(
        query, condicoes, limite, expressao_relevancia
    )
    opcoes = normalizar(itens, expressao_relevancia)[:limite]

    return ResultadoBusca(
        manga=expressao_relevancia,
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
