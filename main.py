from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from datetime import datetime
from typing import Optional
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

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
            "rss": "/rss - Feed RSS das notícias (compatível com leitores RSS)",
            "health": "/health - Status da API",
            "docs": "/docs - Documentação interativa",
            "cache_stats": "/cache/stats - Estatísticas do cache",
            "cache_info": "/cache/info - Informações detalhadas do cache"
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


@app.get("/rss", tags=["RSS"])
async def get_rss_feed(
    max_noticias: int = Query(
        default=10, 
        ge=1, 
        le=20, 
        description="Número máximo de notícias no feed RSS (1-20)"
    )
):
    """
    Retorna as notícias em formato RSS 2.0 XML
    
    Este endpoint gera um feed RSS compatível com leitores de RSS padrão como:
    - Feedly
    - Inoreader  
    - RSS Guard
    - Thunderbird
    - E outros...
    
    **Formato**: RSS 2.0 XML
    **Content-Type**: application/rss+xml
    """
    try:
        # Verificar cache primeiro
        cached_data = news_cache.get(max_noticias)
        
        if cached_data:
            logger.info(f"Retornando feed RSS com {len(cached_data['noticias'])} notícias (cache hit)")
            noticias = cached_data['noticias']
        else:
            # Buscar dados frescos
            logger.info(f"Cache miss - buscando {max_noticias} notícias para feed RSS")
            noticias = scraper.obter_noticias(max_noticias=max_noticias)
            
            if not noticias:
                logger.warning("Nenhuma notícia encontrada para o feed RSS")
                # Retornar RSS vazio mas válido
                return _generate_empty_rss()
            
            # Armazenar no cache
            response_data = {
                "total_noticias": len(noticias),
                "dados_extraidos": ["Título ✓", "Resumo ✓", "Imagem ✓", "Link ✓", "Categoria ✓", "Data ✓"],
                "noticias": noticias,
                "timestamp": datetime.now().isoformat()
            }
            news_cache.set(max_noticias, response_data)
            logger.info(f"Feed RSS gerado com {len(noticias)} notícias (dados frescos)")
        
        # Gerar XML RSS
        rss_xml = _generate_rss_xml(noticias)
        
        return Response(
            content=rss_xml,
            media_type="application/rss+xml; charset=utf-8",
            headers={
                "Cache-Control": "public, max-age=900",  # Cache por 15 minutos
                "X-Content-Type-Options": "nosniff"
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar feed RSS: {str(e)}")
        
        # Retornar RSS de erro mas ainda válido
        error_rss = _generate_error_rss(str(e))
        return Response(
            content=error_rss,
            media_type="application/rss+xml; charset=utf-8",
            status_code=500
        )


def _generate_rss_xml(noticias: list) -> str:
    """Gera o XML RSS 2.0 a partir da lista de notícias"""
    # Criar elemento raiz RSS
    rss = Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    
    # Canal principal
    channel = SubElement(rss, "channel")
    
    # Metadados do canal
    title = SubElement(channel, "title")
    title.text = "ANDES News - Notícias do Sindicato Nacional dos Docentes"
    
    description = SubElement(channel, "description")
    description.text = "Feed RSS com as últimas notícias do Sindicato Nacional dos Docentes das Instituições de Ensino Superior (ANDES)"
    
    link = SubElement(channel, "link")
    link.text = "https://www.andes.org.br"
    
    language = SubElement(channel, "language")
    language.text = "pt-BR"
    
    last_build_date = SubElement(channel, "lastBuildDate")
    last_build_date.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
    
    generator = SubElement(channel, "generator")
    generator.text = "ANDES News API v1.1.0"
    
    # Link atom self-reference
    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", "https://seu-app.onrender.com/rss")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")
    
    # Adicionar itens (notícias)
    for noticia in noticias:
        item = SubElement(channel, "item")
        
        # Título
        item_title = SubElement(item, "title")
        item_title.text = noticia.get('titulo', 'Título não disponível')
        
        # Link
        item_link = SubElement(item, "link")
        item_link.text = noticia.get('link', '')
        
        # Descrição (resumo)
        item_description = SubElement(item, "description")
        resumo = noticia.get('resumo', 'Resumo não disponível')
        if resumo == 'Resumo não disponível':
            item_description.text = f"<![CDATA[{noticia.get('titulo', 'Título não disponível')}]]>"
        else:
            item_description.text = f"<![CDATA[{resumo}]]>"
        
        # GUID (identificador único)
        guid = SubElement(item, "guid")
        guid.text = noticia.get('link', f"noticia-{noticia.get('numero', 0)}")
        guid.set("isPermaLink", "true" if noticia.get('link') else "false")
        
        # Categoria
        if noticia.get('categoria'):
            category = SubElement(item, "category")
            category.text = noticia['categoria']
        
        # Data de publicação (se disponível)
        if noticia.get('data') and noticia['data'] != 'Data não informada':
            pub_date = SubElement(item, "pubDate")
            try:
                # Tentar converter a data para formato RFC 2822
                data_str = noticia['data']
                # Se não conseguir parsear, usar data atual
                pub_date.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
            except:
                pub_date.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        
        # Imagem (se disponível)
        if (noticia.get('imagem') and 
            noticia['imagem'] not in ['Imagem não disponível', 'Imagem não encontrada'] and
            noticia['imagem'].startswith('http')):
            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", noticia['imagem'])
            enclosure.set("type", "image/jpeg")  # Assumindo JPEG
            enclosure.set("length", "0")  # Tamanho desconhecido
    
    # Converter para string XML formatada
    xml_str = tostring(rss, encoding='unicode')
    
    # Formatar com minidom para melhor legibilidade
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding=None)
    
    # Remover linhas vazias extras
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    return '\n'.join(lines)


def _generate_empty_rss() -> Response:
    """Gera um feed RSS vazio mas válido"""
    rss = Element("rss")
    rss.set("version", "2.0")
    
    channel = SubElement(rss, "channel")
    
    title = SubElement(channel, "title")
    title.text = "ANDES News - Sem notícias disponíveis"
    
    description = SubElement(channel, "description")
    description.text = "Nenhuma notícia encontrada no momento"
    
    link = SubElement(channel, "link")
    link.text = "https://www.andes.org.br"
    
    xml_str = tostring(rss, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding=None)
    
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    return Response(
        content='\n'.join(lines),
        media_type="application/rss+xml; charset=utf-8"
    )


def _generate_error_rss(error_message: str) -> str:
    """Gera um feed RSS de erro mas ainda válido"""
    rss = Element("rss")
    rss.set("version", "2.0")
    
    channel = SubElement(rss, "channel")
    
    title = SubElement(channel, "title")
    title.text = "ANDES News - Erro"
    
    description = SubElement(channel, "description")
    description.text = f"Erro ao obter notícias: {error_message}"
    
    link = SubElement(channel, "link")
    link.text = "https://www.andes.org.br"
    
    xml_str = tostring(rss, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding=None)
    
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    return '\n'.join(lines)


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
