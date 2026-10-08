from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.db import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="Agentic Software Engineering System",
    description="Agentic SDLC system for building and validating a URL shortener",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)