from typing import List


class Settings:
    
    APP_NAME: str = "ANDES News API"
    VERSION: str = "1.2.0"
    DESCRIPTION: str = "API para extração de notícias do site da ANDES (Sindicato Nacional dos Docentes das Instituições de Ensino Superior) com cache inteligente e filtragem por palavras-chave"
    
    API_BASE_URL: str = "https://andes-news-api.onrender.com"
    ANDES_BASE_URL: str = "https://andes.org.br"
    
    CACHE_TTL_SECONDS: int = 900
    CACHE_MAX_SIZE: int = 50
    
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    MAX_NOTICIAS_LIMIT: int = 20
    DEFAULT_NOTICIAS: int = 20
    DEFAULT_RSS_NOTICIAS: int = 10
    
    # Configurações de filtragem por palavras-chave
    ENABLE_KEYWORD_FILTER: bool = True
    DEFAULT_KEYWORDS_INCLUDE: List[str] = [
        "educação", "universidade", "ensino", "federal",
        "servidor público", "ifs", "if", "governo",
        "aposentadoria", "carreira", "ebtt", "paralisação", "greve",
    ]
    DEFAULT_KEYWORDS_EXCLUDE: List[str] = [
        "spam", "publicidade", "anúncio", "propaganda"
    ]
    # SEMPRE aplica os filtros definidos acima - não permite sobrescrita via URL
    APPLY_FILTER_BY_DEFAULT: bool = True
    ALLOW_EXTERNAL_KEYWORDS: bool = False  # Bloqueia palavras-chave externas


settings = Settings()
