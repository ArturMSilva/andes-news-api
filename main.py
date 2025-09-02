from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime

from app import (
    settings, 
    setup_logging, 
    keep_alive_service,
    info_router, 
    noticias_router, 
    cache_router, 
    rss_router
)
from app.models import ErrorResponse

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(info_router)
app.include_router(noticias_router)
app.include_router(cache_router)
app.include_router(rss_router)


@app.on_event("startup")
async def startup_event():
    """Evento executado na inicialização da aplicação"""
    await keep_alive_service.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Evento executado no encerramento da aplicação"""
    await keep_alive_service.stop()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    from app.core import get_logger
    logger = get_logger(__name__)
    
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
    import os
    
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,
        log_level="info"
    )
