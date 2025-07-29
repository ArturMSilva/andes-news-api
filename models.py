from typing import List, Dict, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime


class NoticiaModel(BaseModel):
    """Modelo de dados para uma notícia"""
    numero: int
    titulo: str
    resumo: str
    imagem: str
    link: HttpUrl
    categoria: str
    data: str


class NoticiaResponse(BaseModel):
    """Resposta da API com lista de notícias"""
    total_noticias: int
    dados_extraidos: List[str]
    noticias: List[NoticiaModel]
    timestamp: str


class ErrorResponse(BaseModel):
    """Resposta de erro padrão"""
    erro: str
    mensagem: str
    timestamp: str
