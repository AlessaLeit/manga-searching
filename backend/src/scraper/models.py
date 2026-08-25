from enum import Enum

from pydantic import BaseModel


class Condicao(str, Enum):
    NOVO = "novo"
    USADO = "usado"
    ONLINE = "online"  # leitura online, sem preço


class Produto(BaseModel):
    nome: str
    condicao: Condicao
    loja: str
    preco: float | None = None  # None quando a opção é leitura online
    link: str | None = None
    autor: str | None = None
    ano: int | None = None
    ofertas: int | None = None  # quantos anúncios existem naquela condição


class ResultadoBusca(BaseModel):
    manga: str
    total_opcoes: int
    preco_minimo: float | None = None
    preco_medio: float | None = None
    fontes_consultadas: list[str] = []
    fontes_com_falha: list[str] = []
    opcoes: list[Produto] = []
