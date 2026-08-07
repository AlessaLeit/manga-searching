from fastapi import FastAPI
from src.routes import search


app = FastAPI()

app.include_router(search.router)
