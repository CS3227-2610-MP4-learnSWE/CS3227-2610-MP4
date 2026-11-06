"""GET /api/progress: the signed-in student's lesson, practice and topic progress."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.db import get_session
from auth.dependencies import AuthUser, current_user
from progress_schemas import ProgressOut
from progress_service import build_progress

router = APIRouter(prefix="/api")


@router.get("/progress", response_model=ProgressOut)
def read_progress(
    user: AuthUser = Depends(current_user(role="student")), db: Session = Depends(get_session)
) -> ProgressOut:
    return build_progress(db, user.id)
