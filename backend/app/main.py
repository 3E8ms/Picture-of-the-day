"""Picture of the Day API entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import storage
from .config import get_settings
from .database import init_db
from .routers import auth, posts, users


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    init_db()
    if get_settings().seed_on_startup:
        from . import seed

        seed.run()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Picture of the Day API", lifespan=lifespan)
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    storage.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/uploads", StaticFiles(directory=storage.UPLOAD_DIR), name="uploads"
    )

    app.include_router(auth.router)
    app.include_router(posts.router)
    app.include_router(users.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
