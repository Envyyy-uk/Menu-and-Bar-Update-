from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import menu as menu_api
from app.core.config import settings
from app.db import engine

app = FastAPI(
    title="Table ordering platform",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(menu_api.router)


@app.get("/health", tags=["ops"])
def health() -> JSONResponse:
    """Health-check із перевіркою бази: сервер, який відповідає «ok», поки
    Postgres лежить, гірший за сервер, який мовчить."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503, content={"status": "degraded", "db": exc.__class__.__name__}
        )
    return JSONResponse({"status": "ok", "db": "ok"})


# Статика без збірки, як у референсі. Монтується останньою, щоб не перехопити
# /api і /health.
_frontend = settings.frontend_dir
if _frontend.exists():
    for area in ("admin", "kitchen"):
        path = _frontend / area
        if path.exists():
            app.mount(f"/{area}", StaticFiles(directory=path, html=True), name=area)
    if (_frontend / "assets").exists():
        app.mount("/assets", StaticFiles(directory=_frontend / "assets"), name="assets")
    if (_frontend / "guest").exists():
        app.mount("/", StaticFiles(directory=_frontend / "guest", html=True), name="guest")
