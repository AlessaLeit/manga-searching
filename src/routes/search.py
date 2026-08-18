import asyncio

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from src.schemas.search import (
    SearchProduct,
    SearchResponse
)
from src.scraper import Condicao, TODAS_CONDICOES, buscar


router = APIRouter(prefix="/search", tags=["Search"])


@router.get('/', response_model=SearchResponse)
async def search(product: Annotated[SearchProduct, Depends()]):

    # sem filtro explícito, busca em todas as condições
    condicoes = {Condicao(f.value) for f in product.filters} or TODAS_CONDICOES

    # o scraper é síncrono (requests): roda fora do event loop
    resultado = await asyncio.to_thread(
        buscar, product.search_expression, condicoes
    )

    if not resultado.opcoes and resultado.fontes_com_falha:
        raise HTTPException(
            status_code=502,
            detail=f"Fontes indisponíveis: {', '.join(resultado.fontes_com_falha)}",
        )

    return SearchResponse(**resultado.model_dump())
