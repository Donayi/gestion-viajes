from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps_auth import require_admin
from app.crud.crud_dashboard import get_admin_dashboard
from app.db.deps import get_db
from app.models.models import Usuario
from app.schemas.dashboard import AdminDashboardResponse


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin", response_model=AdminDashboardResponse)
def get_dashboard_admin(
    db: Session = Depends(get_db),
    _current_user: Usuario = Depends(require_admin),
):
    return get_admin_dashboard(db)
