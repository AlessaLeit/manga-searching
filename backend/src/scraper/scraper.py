"""Orquestrador da busca: consulta as fontes pré-definidas e consolida.

As fontes não custam a mesma coisa. Estante Virtual e MangaDex respondem por
HTTP em segundos; Bing, Enjoei e OLX precisam de um Chromium, que na VM de
produção (1 GB) é o recurso mais escasso que existe.

Daí as três regras deste módulo:

1. As leves vêm sempre primeiro, e o resultado delas nunca fica refém das
   pesadas — se o tempo acabar, devolvemos o que já temos em vez de falhar.
2. As pesadas rodam uma busca por vez, compartilhando um único navegador.
3. Tudo respeita um orçamento de tempo, verificado antes de cada fonte, para
   a busca terminar sozinha antes de a rota desistir dela.
"""
import logging
import threading
import time
from statistics import mean

from . import navegador
from .models import Condicao, Produto, ResultadoBusca
from .normalizer import normalizar
from .sources import FONTES

logger = logging.getLogger(__name__)

TODAS_CONDICOES = {Condicao.NOVO, Condicao.USADO, Condicao.ONLINE}

# Uma busca com navegador por vez. Duas instâncias simultâneas do Chromium não
# cabem em 1 GB — quem chega depois espera, e desiste se o tempo apertar.
_VEZ_DO_NAVEGADOR = threading.Semaphore(1)

# Abaixo disto não vale a pena nem tentar uma fonte pesada: o navegador leva
# alguns segundos só para subir e carregar a página.
MINIMO_PARA_FONTE_PESADA = 12.0


def _e_pesada(fonte) -> bool:
    return getattr(fonte, "USA_NAVEGADOR", False)


def _habilitada(fonte) -> bool:
    # Fonte opcional desligada não é "consultada": omiti-la evita relatar
    # uma busca mais ampla do que a que realmente aconteceu.
    return getattr(fonte, "habilitado", lambda: True)()


def _restante(prazo: float | None) -> float:
    return float("inf") if prazo is None else prazo - time.monotonic()


def buscar_bruto(query: str, condicoes: set[Condicao] | None = None,
                 limite: int = 40) -> list[dict]:
    """Coleta itens crus de todas as fontes. Uma fonte que falha é ignorada."""
    return _coletar(query, condicoes or TODAS_CONDICOES, limite)[0]


def _consultar(fonte, query: str, query_limpa: str | None,
               condicoes: set[Condicao], limite: int,
               itens: list[dict], consultadas: list[str],
               com_falha: list[str]) -> None:
    """Chama uma fonte e acumula o resultado. Falha não propaga."""
    # Lojas se beneficiam do contexto "livro manga" na busca; catálogos que
    # casam por título exato, não — para o MangaDex, "livro manga berserk"
    # não é nenhuma obra e a busca voltava vazia.
    usa_limpa = getattr(fonte, "USA_QUERY_LIMPA", False)
    termo = query_limpa if (usa_limpa and query_limpa) else query

    try:
        encontrados = fonte.buscar(termo, condicoes, limite)
    except Exception:
        # Uma loja fora do ar não pode derrubar a busca inteira. Mas o motivo
        # precisa ficar no log: sem isto, a fonte só aparece em
        # `fontes_com_falha` e não há como saber se foi timeout, bloqueio do
        # site ou erro nosso.
        logger.warning("fonte %s falhou", fonte.NOME, exc_info=True)
        com_falha.append(fonte.NOME)
        return

    consultadas.append(fonte.NOME)

    # Carimbar aqui, e não em cada fonte, mantém o campo garantido: fonte nova
    # nasce com ele preenchido sem precisar lembrar de nada.
    for item in encontrados:
        item["fonte"] = fonte.NOME

    itens.extend(encontrados)


def _coletar(query: str, condicoes: set[Condicao], limite: int,
             query_limpa: str | None = None,
             orcamento_segundos: float | None = None
             ) -> tuple[list[dict], list[str], list[str]]:
    itens: list[dict] = []
    consultadas: list[str] = []
    com_falha: list[str] = []

    prazo = (None if orcamento_segundos is None
             else time.monotonic() + orcamento_segundos)

    ativas = [f for f in FONTES if _habilitada(f)]
    leves = [f for f in ativas if not _e_pesada(f)]
    pesadas = [f for f in ativas if _e_pesada(f)]

    # 1. As leves, sempre e primeiro: é o resultado que o usuário recebe mesmo
    #    quando tudo o mais dá errado.
    for fonte in leves:
        _consultar(fonte, query, query_limpa, condicoes, limite,
                   itens, consultadas, com_falha)

    if not pesadas:
        return itens, consultadas, com_falha

    # 2. As pesadas, no tempo que sobrou e uma busca por vez.
    _coletar_pesadas(pesadas, query, query_limpa, condicoes, limite, prazo,
                     itens, consultadas, com_falha)

    return itens, consultadas, com_falha


def _coletar_pesadas(pesadas, query, query_limpa, condicoes, limite, prazo,
                     itens, consultadas, com_falha) -> None:
    espera = _restante(prazo)
    if espera < MINIMO_PARA_FONTE_PESADA:
        logger.info("sem tempo para as fontes com navegador (%.1fs)", espera)
        com_falha.extend(f.NOME for f in pesadas)
        return

    # Espera a vez só pelo tempo que ainda temos. Sob carga, em vez de
    # enfileirar e estourar o prazo, a busca desiste das pesadas e entrega as
    # leves — degradar é melhor que devolver 504.
    if not _VEZ_DO_NAVEGADOR.acquire(timeout=espera - MINIMO_PARA_FONTE_PESADA):
        logger.info("servidor ocupado: fontes com navegador puladas")
        com_falha.extend(f.NOME for f in pesadas)
        return

    try:
        with navegador.sessao():
            for fonte in pesadas:
                if _restante(prazo) < MINIMO_PARA_FONTE_PESADA:
                    logger.info("tempo esgotado antes de %s", fonte.NOME)
                    com_falha.append(fonte.NOME)
                    continue

                _consultar(fonte, query, query_limpa, condicoes, limite,
                           itens, consultadas, com_falha)
    except navegador.PlaywrightIndisponivel:
        # Sem Chromium instalado nenhuma delas roda; a busca segue com as
        # leves em vez de estourar.
        logger.warning("Chromium indisponível; fontes com navegador puladas",
                       exc_info=True)
        com_falha.extend(f.NOME for f in pesadas if f.NOME not in com_falha)
    finally:
        _VEZ_DO_NAVEGADOR.release()


def buscar(query: str, condicoes: set[Condicao] | None = None,
           limite: int = 40, *,
           query_relevancia: str | None = None,
           orcamento_segundos: float | None = None) -> ResultadoBusca:
    condicoes = condicoes or TODAS_CONDICOES
    expressao_relevancia = query if query_relevancia is None else query_relevancia
    itens, consultadas, com_falha = _coletar(
        query, condicoes, limite, expressao_relevancia, orcamento_segundos
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
