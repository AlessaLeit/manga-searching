import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.core.errors import registrar_tratadores_de_erro
from backend.src.routes import search

# O uvicorn não lê o .env sozinho; sem isto as variáveis de configuração
# (fontes, CORS, timeout) ficariam sempre no valor padrão.
load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

# Origens do front autorizadas a chamar esta API pelo navegador.
# Em fase de testes, CORS_ORIGINS=* no .env libera qualquer origem.
_ORIGENS_PADRAO = "http://localhost:5173,http://localhost:3000,http://localhost:8080"


def origens_permitidas() -> list[str]:
    bruto = os.getenv("CORS_ORIGINS", _ORIGENS_PADRAO)
    return [origem.strip() for origem in bruto.split(",") if origem.strip()]


app = FastAPI(
    title="MangaSearch API",
    description="Busca e comparação de preços de mangás físicos.",
    version="1.0.0",
)

# Controle de acesso do navegador (CORS). Sem este middleware o front em
# localhost:5173 recebe erro de rede ao chamar a API em localhost:8000 —
# o navegador bloqueia a resposta por ser de outra origem.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origens_permitidas(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],  # a API é somente leitura
    allow_headers=["*"],
)

registrar_tratadores_de_erro(app)

app.include_router(search.router)


@app.get("/health", tags=["Infra"])
async def health():
    """Usado para checar se a API está no ar antes de culpar a rede."""
    return {"status": "ok"}