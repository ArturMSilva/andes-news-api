from typing import List


class Settings:
    
    APP_NAME: str = "ANDES News API"
    VERSION: str = "1.1.0"
    DESCRIPTION: str = "API para extração de notícias do site da ANDES (Sindicato Nacional dos Docentes das Instituições de Ensino Superior) com cache inteligente"
    
    API_BASE_URL: str = "https://andes-news-api.onrender.com"
    ANDES_BASE_URL: str = "https://andes.org.br"
    
    CACHE_TTL_SECONDS: int = 900
    CACHE_MAX_SIZE: int = 50
    
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    MAX_NOTICIAS_LIMIT: int = 20
    DEFAULT_NOTICIAS: int = 5
    DEFAULT_RSS_NOTICIAS: int = 10


settings = Settings()
