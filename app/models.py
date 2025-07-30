from typing import List, Dict, Optional
from pydantic import BaseModel, HttpUrl
from datetime import datetime


class NoticiaModel(BaseModel):
    numero: int
    titulo: str
    resumo: str
    imagem: str
    link: HttpUrl
    categoria: str
    data: str


class NoticiaResponse(BaseModel):
    total_noticias: int
    dados_extraidos: List[str]
    noticias: List[NoticiaModel]
    timestamp: str


class ErrorResponse(BaseModel):
    erro: str
    mensagem: str
    timestamp: str
