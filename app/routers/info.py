from fastapi import APIRouter
from datetime import datetime

from ..core import settings, get_logger
from ..cache import news_cache

logger = get_logger(__name__)

router = APIRouter(tags=["Info"])


@router.get("/")
async def root():
    cache_stats = news_cache.get_stats()
    return {
        "message": settings.APP_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "cache_enabled": True,
        "cache_ttl": "15 minutos",
        "cache_hit_rate": f"{cache_stats['hit_rate_percentage']}%",
        "endpoints": {
            "noticias": "/noticias - Obtém as últimas notícias (com cache)",
            "rss": "/rss - Feed RSS das notícias (compatível com leitores RSS)",
            "health": "/health - Status da API",
            "docs": "/docs - Documentação interativa",
            "cache_stats": "/cache/stats - Estatísticas do cache",
            "cache_info": "/cache/info - Informações detalhadas do cache"
        }
    }


@router.get("/health")
async def health_check():
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": settings.APP_NAME,
            "version": settings.VERSION
        }
    except Exception:
        return {"status": "ok"}
