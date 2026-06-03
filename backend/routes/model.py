from fastapi import APIRouter

from backend.data_loader import get_model_summary


router = APIRouter(prefix="/api/model", tags=["model"])


@router.get("/summary")
def read_model_summary():
    """Return model metrics, explanation, and limitations."""
    return get_model_summary()
