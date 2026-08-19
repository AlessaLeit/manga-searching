from fastapi import FastAPI
from backend.src.routes import search


app = FastAPI()

app.include_router(search.router)
