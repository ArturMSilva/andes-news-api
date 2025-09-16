from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List

from ..core import settings, get_logger
from ..models import NoticiaResponse, ErrorResponse
from ..scraper import AndesScraper
from ..cache import news_cache
from ..filters import news_filter

logger = get_logger(__name__)

router = APIRouter(tags=["Notícias"])

scraper = AndesScraper()


@router.get("/noticias", 
           response_model=NoticiaResponse,
           summary="Obter últimas notícias com filtros automáticos",
           description="Retorna as últimas notícias do site da ANDES. Os filtros de palavras-chave definidos no arquivo de configuração são aplicados automaticamente - não é necessário chamar rotas específicas para filtragem.")
async def obter_noticias(
    max_noticias: Optional[int] = Query(
        default=settings.DEFAULT_NOTICIAS, 
        ge=1, 
        le=settings.MAX_NOTICIAS_LIMIT, 
        description=f"Número máximo de notícias para retornar (1-{settings.MAX_NOTICIAS_LIMIT})"
    ),
    apenas_titulo: bool = Query(
        default=False,
        description="Se True, busca palavras-chave apenas no título; se False, busca no título e resumo"
    ),
    case_sensitive: bool = Query(
        default=False,
        description="Se a busca por palavras-chave deve ser case sensitive"
    )
):
    try:
        logger.info(f"Requisição recebida para {max_noticias} notícias com filtros automáticos")
        
        keywords_include = None
        keywords_exclude = None
        
        filter_summary = news_filter.get_filter_summary(
            keywords_include=keywords_include,
            keywords_exclude=keywords_exclude,
            titulo_apenas=apenas_titulo,
            caso_sensitivo=case_sensitive,
            use_defaults=True
        )
        
        cache_filters = filter_summary
        cached_response = news_cache.get(max_noticias, cache_filters)
        
        if cached_response is not None:
            logger.info(f"Retornando {cached_response['total_noticias']} notícias do cache (filtradas)")
            return NoticiaResponse(**cached_response)
        
        logger.info("Cache miss - realizando scraping com filtros automáticos")
        
        noticias = scraper.obter_noticias(
            max_noticias=max_noticias,
            apply_filters=True,
            keywords_include=keywords_include,
            keywords_exclude=keywords_exclude,
            titulo_apenas=apenas_titulo,
            caso_sensitivo=case_sensitive
        )
        
        response_data = {
            "total_noticias": len(noticias),
            "dados_extraidos": ["Título ✓", "Resumo ✓", "Imagem ✓", "Link ✓", "Categoria ✓", "Data ✓"],
            "noticias": noticias,
            "timestamp": datetime.now().isoformat()
        }
        
        news_cache.set(max_noticias, response_data, cache_filters)
        
        response = NoticiaResponse(**response_data)
        logger.info(f"Retornando {len(noticias)} notícias com filtros automáticos aplicados")
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
            detail=error_response.model_dump()
        )
