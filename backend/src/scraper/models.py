from enum import Enum

from pydantic import BaseModel


class Condicao(str, Enum):
    NOVO = "novo"
    USADO = "usado"
    ONLINE = "online"  # leitura online, sem preço


class Produto(BaseModel):
    nome: str
    condicao: Condicao
    # De onde a oferta veio (a fonte consultada) e quem está vendendo (a loja
    # ou o anunciante). São perguntas diferentes: "Amazon BR" vem do Bing, e
    # "panini" é um vendedor da Enjoei, apesar de parecer editora.
    fonte: str
    loja: str
    preco: float | None = None  # None quando a opção é leitura online
    link: str | None = None
    imagem: str | None = None  # URL da capa; None quando a fonte não traz
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
