from contextlib import asynccontextmanager
from importlib.resources import files

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from app.database.db import engine
from app.routers.tasks import router
from seed import seed_demo


def create_app(bind=engine):
    @asynccontextmanager
    async def lifespan(app):
        seed_demo(bind)
        yield

    api = FastAPI(title="Учебный планировщик", version="1.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None)
    api.include_router(router)
    api.mount("/swagger-assets", StaticFiles(directory=str(files("swagger_ui") / "static")), name="swagger")

    @api.get("/docs", include_in_schema=False)
    def swagger():
        return get_swagger_ui_html(
            openapi_url="/openapi.json", title="Планировщик · Swagger UI",
            swagger_js_url="/swagger-assets/swagger-ui-bundle.js",
            swagger_css_url="/swagger-assets/swagger-ui.css",
            swagger_favicon_url="/swagger-assets/favicon-32x32.png",
        )

    @api.get("/", tags=["Сервис"])
    def health():
        return {"status": "ok"}

    return api


app = create_app()
