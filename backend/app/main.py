import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api import admin_menu as admin_menu_api
from app.api import admin_schedules as admin_schedules_api
from app.api import admin_stripe as admin_stripe_api
from app.api import admin_tables as admin_tables_api
from app.api import admin_users as admin_users_api
from app.api import auth as auth_api
from app.api import menu as menu_api
from app.api import orders as orders_api
from app.api import kitchen as kitchen_api
from app.api import webhooks as webhooks_api
from app.core.config import settings
from app.db import engine
from app.services import realtime, reconcile

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Звірка `paid` → `accepted` крутиться поруч із застосунком: гість
    заплатив, кухня не побачила — і система має кричати, а не мовчати."""
    realtime.bind_loop(asyncio.get_running_loop())
    task = asyncio.create_task(reconcile.run_forever())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Table ordering platform",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.include_router(menu_api.router)
app.include_router(auth_api.router)
app.include_router(admin_users_api.router)
app.include_router(admin_menu_api.router)
app.include_router(admin_schedules_api.router)
app.include_router(admin_tables_api.router)
app.include_router(orders_api.router)
app.include_router(admin_stripe_api.router)
app.include_router(webhooks_api.router)
app.include_router(kitchen_api.router)


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


@app.get("/t/{token}", include_in_schema=False)
def table_entry(token: str) -> FileResponse:
    """QR веде на /t/{token}. Сторінка та сама, що й гостьове меню — стіл
    вона дізнається з адреси й перепитує в API."""
    page = settings.frontend_dir / "guest" / "index.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="guest page is not built")
    return FileResponse(page)


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
