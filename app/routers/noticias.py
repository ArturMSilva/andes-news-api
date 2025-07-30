from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional

from ..core import settings, get_logger
from ..models import NoticiaResponse, ErrorResponse
from ..scraper import AndesScraper
from ..cache import news_cache

logger = get_logger(__name__)

router = APIRouter(tags=["Notícias"])

scraper = AndesScraper()


@router.get("/noticias", 
           response_model=NoticiaResponse,
           summary="Obter últimas notícias",
           description="Retorna as últimas notícias do site da ANDES com título, resumo, imagem, link, categoria e data")
async def obter_noticias(
    max_noticias: Optional[int] = Query(
        default=settings.DEFAULT_NOTICIAS, 
        ge=1, 
        le=settings.MAX_NOTICIAS_LIMIT, 
        description=f"Número máximo de notícias para retornar (1-{settings.MAX_NOTICIAS_LIMIT})"
    )
):
    try:
        logger.info(f"Requisição recebida para {max_noticias} notícias")
        
        cached_response = news_cache.get(max_noticias)
        if cached_response is not None:
            logger.info(f"Retornando {cached_response['total_noticias']} notícias do CACHE")
            return NoticiaResponse(**cached_response)
        
        logger.info("Cache miss - realizando scraping")
        noticias = scraper.obter_noticias(max_noticias)
        
        response_data = {
            "total_noticias": len(noticias),
            "dados_extraidos": ["Título ✓", "Resumo ✓", "Imagem ✓", "Link ✓", "Categoria ✓", "Data ✓"],
            "noticias": noticias,
            "timestamp": datetime.now().isoformat()
        }
        
        news_cache.set(max_noticias, response_data)
        
        response = NoticiaResponse(**response_data)
        logger.info(f"Retornando {len(noticias)} notícias (dados frescos armazenados no cache)")
        return response
        
    except Exception as e:
        logger.error(f"Erro ao obter notícias: {str(e)}")
        
        error_response = ErrorResponse(
            erro="Erro interno do servidor",
            mensagem=f"Não foi possível obter as notícias: {str(e)}",
            timestamp=datetime.now().isoformat()
        )
        raise HTTPException(
            status_code=500,
            detail=error_response.dict()
        )
