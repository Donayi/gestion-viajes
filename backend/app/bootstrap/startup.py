from app.bootstrap.schema_bootstrap import run_schema_bootstrap
from app.bootstrap.seed_bootstrap import run_seed_bootstrap


def run_startup_tasks() -> None:
    run_schema_bootstrap()
    run_seed_bootstrap()

