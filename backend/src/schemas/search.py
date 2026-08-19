from fastapi import Query
from pydantic import BaseModel, Field, StringConstraints
from enum import Enum
from typing import Annotated, Optional

Expression = Annotated[
    str,
    StringConstraints(
        min_length=1,
        strip_whitespace=True,
    )
]


class FilterOptions(str, Enum):
    """Condições de aquisição aceitas como filtro. Espelha scraper.Condicao."""
    NOVO = "novo"
    USADO = "usado"
    ONLINE = "online"


class SearchProduct(BaseModel):
    search_expression: Expression
    # Query() explícito: sem ele o Depends() da rota não liga o parâmetro
    # repetido (?filters=novo&filters=usado) e o filtro era ignorado em
    # silêncio, buscando sempre todas as condições.
    # Default literal (não default_factory) porque o Depends() lê o default do
    # campo diretamente e não resolve a factory. O pydantic copia o valor.
    filters: Annotated[list[FilterOptions], Query()] = []


class ProductOption(BaseModel):
    nome: str
    condicao: FilterOptions
    loja: str
    preco: Optional[float] = None  # ausente na leitura online
    link: Optional[str] = None
    autor: Optional[str] = None
    ano: Optional[int] = None
    ofertas: Optional[int] = None


class SearchResponse(BaseModel):
    manga: str
    total_opcoes: int
    preco_minimo: Optional[float] = None
    preco_medio: Optional[float] = None
    fontes_consultadas: list[str] = Field(default_factory=list)
    fontes_com_falha: list[str] = Field(default_factory=list)
    opcoes: list[ProductOption] = Field(default_factory=list)
