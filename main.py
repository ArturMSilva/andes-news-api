from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from typing import Optional
import logging

from scraper import AndesScraper
from models import NoticiaResponse, ErrorResponse
from cache import news_cache

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar instância da aplicação FastAPI
app = FastAPI(
    title="ANDES News API",
    description="API para extração de notícias do site da ANDES (Sindicato Nacional dos Docentes das Instituições de Ensino Superior) com cache inteligente",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios específicos
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Instância do scraper
scraper = AndesScraper()


@app.get("/", tags=["Info"])
async def root():
    """Endpoint raiz com informações da API"""
    cache_stats = news_cache.get_stats()
    return {
        "message": "ANDES News API",
        "version": "1.1.0",
        "description": "API para extração de notícias do site da ANDES com cache inteligente",
        "cache_enabled": True,
        "cache_ttl": "15 minutos",
        "cache_hit_rate": f"{cache_stats['hit_rate_percentage']}%",
        "endpoints": {
            "noticias": "/noticias - Obtém as últimas notícias (com cache)",
            "cache/stats": "/cache/stats - Estatísticas do cache",
            "cache/info": "/cache/info - Informações detalhadas do cache",
            "docs": "/docs - Documentação interativa",
            "health": "/health - Status da API"
        }
    }


@app.get("/health", tags=["Info"])
async def health_check():
    """Endpoint para verificação de saúde da API"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ANDES News API"
    }


@app.get("/noticias", 
         response_model=NoticiaResponse, 
         tags=["Notícias"],
         summary="Obter últimas notícias",
         description="Retorna as últimas notícias do site da ANDES com título, resumo, imagem, link, categoria e data")
async def obter_noticias(
    max_noticias: Optional[int] = Query(
        default=5, 
        ge=1, 
        le=20, 
        description="Número máximo de notícias para retornar (1-20)"
    )
):
    """
    Obtém as últimas notícias do site da ANDES
    
    - **max_noticias**: Número de notícias para retornar (1-20, padrão: 5)
    
    Retorna um JSON com:
    - Lista de notícias com título, resumo, imagem, link, categoria e data
    - Total de notícias processadas
    - Timestamp da requisição
    
    **Cache:** Esta API utiliza cache inteligente de 15 minutos para melhor performance.
    """
    try:
        logger.info(f"Requisição recebida para {max_noticias} notícias")
        
        # Tentar obter do cache primeiro
        cached_response = news_cache.get(max_noticias)
        if cached_response is not None:
            logger.info(f"Retornando {cached_response['total_noticias']} notícias do CACHE")
            return NoticiaResponse(**cached_response)
        
        # Cache miss - realizar scraping
        logger.info("Cache miss - realizando scraping")
        noticias = scraper.obter_noticias(max_noticias)
        
        # Preparar resposta
        response_data = {
            "total_noticias": len(noticias),
            "dados_extraidos": ["Título ✓", "Resumo ✓", "Imagem ✓", "Link ✓", "Categoria ✓", "Data ✓"],
            "noticias": noticias,
            "timestamp": datetime.now().isoformat()
        }
        
        # Armazenar no cache para próximas requisições
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


@app.get("/cache/stats", tags=["Cache"])
async def cache_stats():
    """Retorna estatísticas de uso do cache"""
    return news_cache.get_stats()


@app.get("/cache/info", tags=["Cache"])
async def cache_info():
    """Retorna informações detalhadas sobre entradas do cache"""
    return news_cache.get_cache_info()


@app.post("/cache/clear", tags=["Cache"])
async def clear_cache():
    """Limpa todo o cache (use com cuidado!)"""
    news_cache.clear()
    return {
        "message": "Cache limpo com sucesso",
        "timestamp": datetime.now().isoformat()
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler global para exceções não tratadas"""
    logger.error(f"Erro não tratado: {str(exc)}")
    
    error_response = ErrorResponse(
        erro="Erro interno do servidor",
        mensagem="Ocorreu um erro inesperado",
        timestamp=datetime.now().isoformat()
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
