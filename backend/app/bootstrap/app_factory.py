from fastapi import FastAPI

from app.bootstrap.cors import configure_cors
from app.bootstrap.routers import register_routers
from app.bootstrap.startup import run_startup_tasks
from app.core.config import settings
from app.services.backup_runtime import DailyBackupScheduler


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    configure_cors(app)
    scheduler = DailyBackupScheduler(config=settings)

    @app.on_event("startup")
    def on_startup() -> None:
        run_startup_tasks()
        scheduler.start()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        scheduler.stop()

    register_routers(app)
    return app
