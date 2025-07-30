from fastapi import APIRouter
from datetime import datetime

from ..core import get_logger
from ..cache import news_cache

logger = get_logger(__name__)

router = APIRouter(tags=["Cache"])


@router.get("/cache/stats")
async def cache_stats():
    return news_cache.get_stats()


@router.get("/cache/info")
async def cache_info():
    return news_cache.get_cache_info()


@router.post("/cache/clear")
async def clear_cache():
    news_cache.clear()
    logger.info("Cache limpo manualmente")
    return {
        "message": "Cache limpo com sucesso",
        "timestamp": datetime.now().isoformat()
    }
