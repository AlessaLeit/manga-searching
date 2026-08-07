from pydantic import BaseModel, Field, StringConstraints
from enum import Enum
from typing import Annotated

Expression = Annotated[
    str,
    StringConstraints(
        min_length=1,
        strip_whitespace=True,
    )
]


class FilterOptions(Enum):
    ...


class SearchProduct(BaseModel):
    search_expression: Expression
    filters: list[FilterOptions] = Field(default_factory=list)


class SearchResponse(BaseModel):
    ...
