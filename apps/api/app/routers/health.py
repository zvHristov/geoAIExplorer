from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "geoai-explorer-api",
        "score_type": "heuristic",  # NOT an AI/ML score
    }
