import asyncio
import os

from fastapi import APIRouter, Query
from typing import Annotated

from backend.src.core.errors import FonteIndisponivelError
from backend.src.schemas.search import (
    SearchProduct,
    SearchResponse
)
from backend.src.scraper import Condicao, TODAS_CONDICOES, buscar


router = APIRouter(prefix="/search", tags=["Search"])

# Teto para a busca inteira. As fontes já têm timeout próprio, mas uma delas
# travada não pode deixar o cliente esperando para sempre.
TEMPO_LIMITE_SEGUNDOS = float(os.getenv("SEARCH_TIMEOUT_SECONDS", "45"))


@router.get(
    '/',
    response_model=SearchResponse,
    responses={
        422: {"description": "Dados inválidos na requisição"},
        502: {"description": "As fontes consultadas estão indisponíveis"},
        504: {"description": "A busca excedeu o tempo limite"},
    },
)
async def search(product: Annotated[SearchProduct, Query()]):
    # sem filtro explícito, busca em todas as condições
    condicoes = {Condicao(f.value) for f in product.filters} or TODAS_CONDICOES

    # o scraper é síncrono (requests): roda fora do event loop.
    # Estourar o tempo levanta TimeoutError, que o tratador central vira 504.
    resultado = await asyncio.wait_for(
        asyncio.to_thread(buscar, product.search_expression, condicoes),
        timeout=TEMPO_LIMITE_SEGUNDOS,
    )

    # Sem nenhuma opção E com fonte que falhou: o problema é de conexão com as
    # lojas, não busca vazia. Busca vazia legítima devolve 200 com lista vazia.
    if not resultado.opcoes and resultado.fontes_com_falha:
        raise FonteIndisponivelError(resultado.fontes_com_falha)

    return SearchResponse(**resultado.model_dump())
