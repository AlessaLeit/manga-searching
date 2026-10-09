from fastapi import Query
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import Annotated, Optional

from backend.src.core.masks import (
    TAMANHO_MAXIMO_EXPRESSAO,
    mascarar_expressao,
    mascarar_filtro,
    tem_conteudo_util,
)

TAMANHO_MINIMO_EXPRESSAO = 2


class FilterOptions(str, Enum):
    """Condições de aquisição aceitas como filtro. Espelha scraper.Condicao."""
    NOVO = "novo"
    USADO = "usado"
    ONLINE = "online"

    @classmethod
    def _missing_(cls, value):
        """Máscara do filtro: aceita "NOVO", " Usado " e afins."""
        normalizado = mascarar_filtro(value)
        return next((m for m in cls if m.value == normalizado), None)


class SearchProduct(BaseModel):
    search_expression: str = Field(
        ...,
        description="Nome do mangá procurado.",
        examples=["One Piece"],
    )
    # Query() explícito: sem ele o Depends() da rota não liga o parâmetro
    # repetido (?filters=novo&filters=usado) e o filtro era ignorado em
    # silêncio, buscando sempre todas as condições.
    # Default literal (não default_factory) porque o Depends() lê o default do
    # campo diretamente e não resolve a factory. O pydantic copia o valor.
    filters: Annotated[list[FilterOptions], Query()] = []

    @field_validator("search_expression", mode="before")
    @classmethod
    def aplicar_mascara(cls, valor):
        """Roda ANTES da validação: limpa o que dá para limpar."""
        return mascarar_expressao(valor)

    @field_validator("search_expression")
    @classmethod
    def validar_expressao(cls, valor: str) -> str:
        """Roda DEPOIS da máscara: rejeita o que sobrou inválido."""
        if len(valor) < TAMANHO_MINIMO_EXPRESSAO:
            raise ValueError(
                f"A pesquisa precisa ter pelo menos {TAMANHO_MINIMO_EXPRESSAO} "
                "caracteres válidos."
            )
        if len(valor) > TAMANHO_MAXIMO_EXPRESSAO:
            raise ValueError(
                f"A pesquisa deve ter no máximo {TAMANHO_MAXIMO_EXPRESSAO} "
                "caracteres."
            )
        if not tem_conteudo_util(valor):
            raise ValueError("A pesquisa precisa conter letras ou números.")

        return valor

    @field_validator("filters")
    @classmethod
    def remover_filtros_repetidos(cls, filtros: list[FilterOptions]):
        """?filters=novo&filters=novo não deve dobrar o trabalho da busca."""
        return list(dict.fromkeys(filtros))


class ProductOption(BaseModel):
    nome: str
    condicao: FilterOptions
    loja: str
    preco: Optional[float] = None  # ausente na leitura online
    link: Optional[str] = None
    imagem: Optional[str] = None  # URL da capa para exibir no card
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
