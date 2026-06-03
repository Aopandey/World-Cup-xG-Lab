from fastapi import APIRouter

from backend.data_loader import get_data_coverage


router = APIRouter(prefix="/api/coverage", tags=["coverage"])


@router.get("")
def read_data_coverage():
    """Return data coverage metadata."""
    return get_data_coverage()
