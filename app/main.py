from fastapi import FastAPI

from app.api.routes import router
from app.db.session import init_db


app = FastAPI(
    title="Persistent Sales Assistant Agent",
    description="A hosted conversational API with catalog tools, durable memory, and self-evaluation.",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(router)
