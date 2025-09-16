from fastapi import APIRouter, Query, Response
from datetime import datetime
from typing import Optional

from ..core import settings, get_logger
from ..services import rss_service
from ..scraper import AndesScraper
from ..cache import news_cache
from ..filters import news_filter

logger = get_logger(__name__)

router = APIRouter(tags=["RSS"])

scraper = AndesScraper()


@router.get("/rss")
async def get_rss_feed(
    max_noticias: int = Query(
        default=settings.DEFAULT_RSS_NOTICIAS, 
        ge=1, 
        le=settings.MAX_NOTICIAS_LIMIT, 
        description=f"Número máximo de notícias no feed RSS (1-{settings.MAX_NOTICIAS_LIMIT}) - filtradas automaticamente"
    )
):
    try:
        # Remove parâmetros externos - usa apenas configuração do config.py
        keywords_include = None  # Será definido pelo filtro baseado no config.py
        keywords_exclude = None  # Será definido pelo filtro baseado no config.py
        
        filter_summary = news_filter.get_filter_summary(
            keywords_include=keywords_include,
            keywords_exclude=keywords_exclude,
            use_defaults=True  # SEMPRE aplica filtros do config.py
        )
        
        cached_data = news_cache.get(max_noticias, filter_summary)
        
        if cached_data:
            logger.info(f"Retornando feed RSS com {len(cached_data['noticias'])} notícias (cache hit, filtradas)")
            noticias = cached_data['noticias']
        else:
            logger.info(f"Cache miss - buscando {max_noticias} notícias para feed RSS com filtros automáticos")
            
            # SEMPRE aplica filtros (não permite desabilitar)
            noticias = scraper.obter_noticias(
                max_noticias=max_noticias,
                apply_filters=True,  
                keywords_include=keywords_include,  
                keywords_exclude=keywords_exclude  
            )
            
            if not noticias:
                logger.warning("Nenhuma notícia encontrada para o feed RSS (após filtragem)")
                empty_rss = rss_service.generate_empty_rss()
                return Response(
                    content=empty_rss,
                    media_type="application/rss+xml; charset=utf-8"
                )
            
            response_data = {
                "total_noticias": len(noticias),
                "dados_extraidos": ["Título ✓", "Resumo ✓", "Imagem ✓", "Link ✓", "Categoria ✓", "Data ✓"],
                "noticias": noticias,
                "timestamp": datetime.now().isoformat(),
                "filtros_aplicados": filter_summary  # SEMPRE inclui informações sobre filtros
            }
            
            news_cache.set(max_noticias, response_data, filter_summary)
            logger.info(f"Feed RSS gerado com {len(noticias)} notícias (dados frescos, filtrados automaticamente)")
        
        rss_xml = rss_service.generate_rss_xml(noticias)
        
        return Response(
            content=rss_xml,
            media_type="application/rss+xml; charset=utf-8",
            headers={
                "Cache-Control": f"public, max-age={settings.CACHE_TTL_SECONDS}",
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar feed RSS: {str(e)}")
        
        error_rss = rss_service.generate_error_rss(str(e))
        return Response(
            content=error_rss,
            media_type="application/rss+xml; charset=utf-8",
            status_code=500
        )
