from pydantic import BaseModel, Field, StringConstraints
from enum import Enum
<<<<<<< Updated upstream
from typing import Annotated
=======
from typing import Annotated, Optional
>>>>>>> Stashed changes

Expression = Annotated[
    str,
    StringConstraints(
        min_length=1,
        strip_whitespace=True,
    )
]


<<<<<<< Updated upstream
class FilterOptions(Enum):
    ...
=======
class FilterOptions(str, Enum):
    """Condições de aquisição aceitas como filtro. Espelha scraper.Condicao."""
    NOVO = "novo"
    USADO = "usado"
    ONLINE = "online"
>>>>>>> Stashed changes


class SearchProduct(BaseModel):
    search_expression: Expression
<<<<<<< Updated upstream
    filters: list[FilterOptions] = Field(default_factory=list)


class SearchResponse(BaseModel):
    ...
=======
    # default literal (não default_factory): o Depends() da rota lê o default
    # do campo diretamente e não resolve a factory. O pydantic copia o valor.
    filters: list[FilterOptions] = []


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
>>>>>>> Stashed changes
