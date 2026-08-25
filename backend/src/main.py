from fastapi import FastAPI
from backend.src.routes import search
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# APENAS PARA RODAR EM FASE DE TESTES --> LIBERA TUDO
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # libera qualquer origem
    allow_credentials=True,
    allow_methods=["*"],  # libera todos os métodos (GET, POST, etc)
    allow_headers=["*"],  # libera todos os headers
)

app.include_router(search.router)
