from fastapi import APIRouter, HTTPException
from src.schemas.search import (
    SearchProduct,
    SearchResponse
)


router = APIRouter(prefix="/search", tags=["Search"])


@router.get('/', response_model=SearchResponse)
async def search(product: SearchProduct):

    # faz a pesquisa com o service

    return SearchResponse(
        # atributos da resposta
    )
