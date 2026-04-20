from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.deps import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/db/ping")
def db_ping(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1 AS ok"))
    row = result.fetchone()

    return {
        "database": "connected",
        "result": row.ok
    }