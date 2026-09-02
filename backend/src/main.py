import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.src.core.errors import registrar_tratadores_de_erro
from backend.src.routes import search
from fastapi.middleware.cors import CORSMiddleware


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

# APENAS PARA RODAR EM FASE DE TESTES --> LIBERA TUDO
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # libera qualquer origem
    allow_credentials=True,
    allow_methods=["*"],  # libera todos os métodos (GET, POST, etc)
    allow_headers=["*"],  # libera todos os headers
)

app.include_router(search.router)


@app.get("/health", tags=["Infra"])
async def health():
    """Usado para checar se a API está no ar antes de culpar a rede."""
    return {"status": "ok"}
