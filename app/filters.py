import re
from typing import List, Dict, Optional, Union

def get_logger(name):
    import logging
    return logging.getLogger(name)

logger = get_logger(__name__)


class NewsFilter:
    
    def __init__(self):
        from .core.config import settings
        self.default_include = settings.DEFAULT_KEYWORDS_INCLUDE
        self.default_exclude = settings.DEFAULT_KEYWORDS_EXCLUDE
        self.settings = settings
    
    def filter_news(
        self, 
        noticias: List[Dict], 
        keywords_include: Optional[Union[List[str], str]] = None,
        keywords_exclude: Optional[Union[List[str], str]] = None,
        titulo_apenas: bool = False,
        caso_sensitivo: bool = False,
        use_defaults: bool = None
    ) -> List[Dict]:
        if not noticias:
            return []
        
        if not self.settings.ALLOW_EXTERNAL_KEYWORDS:
            include_keywords = self.default_include
            exclude_keywords = self.default_exclude
            logger.info("Aplicando APENAS filtros do config.py - parâmetros externos ignorados")
        else:
            if use_defaults is None:
                use_defaults = self.settings.APPLY_FILTER_BY_DEFAULT and self.settings.ENABLE_KEYWORD_FILTER
            
            include_keywords = self._process_keywords(keywords_include)
            if use_defaults and not include_keywords:
                include_keywords = self.default_include
            
            exclude_keywords = self._process_keywords(keywords_exclude)
            if use_defaults and not exclude_keywords:
                exclude_keywords = self.default_exclude
        
        if not include_keywords and not exclude_keywords:
            logger.info("Nenhum filtro aplicado - retornando todas as notícias")
            return noticias
        
        filtered_news = []
        
        for noticia in noticias:
            if self._should_include_news(
                noticia, 
                include_keywords, 
                exclude_keywords, 
                titulo_apenas, 
                caso_sensitivo
            ):
                filtered_news.append(noticia)
        
        logger.info(
            f"Filtragem aplicada: {len(filtered_news)}/{len(noticias)} notícias mantidas. "
            f"Incluir: {include_keywords if include_keywords else 'Nenhuma'}, "
            f"Excluir: {exclude_keywords if exclude_keywords else 'Nenhuma'}"
        )
        
        return filtered_news
    
    def _process_keywords(self, keywords: Optional[Union[List[str], str]]) -> List[str]:
        if not keywords:
            return []
        
        if isinstance(keywords, str):
            keywords = re.split(r'[,\s]+', keywords.strip())
        
        return [kw.strip() for kw in keywords if kw.strip()]
    
    def _should_include_news(
        self, 
        noticia: Dict, 
        include_keywords: List[str], 
        exclude_keywords: List[str],
        titulo_apenas: bool, 
        caso_sensitivo: bool
    ) -> bool:
        
        titulo = noticia.get('titulo', '')
        resumo = noticia.get('resumo', '') if not titulo_apenas else ''
        search_text = f"{titulo} {resumo}".strip()
        
        if not caso_sensitivo:
            search_text = search_text.lower()
        
        if exclude_keywords:
            exclude_processed = [kw.lower() for kw in exclude_keywords] if not caso_sensitivo else exclude_keywords
            if any(self._keyword_matches(search_text, kw) for kw in exclude_processed):
                return False
        
        if include_keywords:
            include_processed = [kw.lower() for kw in include_keywords] if not caso_sensitivo else include_keywords
            return any(self._keyword_matches(search_text, kw) for kw in include_processed)
        
        return True
    
    def _keyword_matches(self, text: str, keyword: str) -> bool:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def get_filter_summary(
        self, 
        keywords_include: Optional[List[str]] = None,
        keywords_exclude: Optional[List[str]] = None,
        titulo_apenas: bool = False,
        caso_sensitivo: bool = False,
        use_defaults: bool = None
    ) -> Dict:
        
        if not self.settings.ALLOW_EXTERNAL_KEYWORDS:
            return {
                "palavras_incluir": self.default_include,
                "palavras_excluir": self.default_exclude,
                "apenas_titulo": titulo_apenas,
                "case_sensitive": caso_sensitivo,
                "fonte_filtros": "config.py (bloqueado para alterações externas)",
                "total_palavras_incluir": len(self.default_include),
                "total_palavras_excluir": len(self.default_exclude),
                "configuracao_segura": True
            }
        
        if use_defaults is None:
            use_defaults = self.settings.APPLY_FILTER_BY_DEFAULT and self.settings.ENABLE_KEYWORD_FILTER
        
        include_final = keywords_include or (self.default_include if use_defaults else [])
        exclude_final = keywords_exclude or (self.default_exclude if use_defaults else [])
        
        return {
            "palavras_incluir": include_final,
            "palavras_excluir": exclude_final,
            "apenas_titulo": titulo_apenas,
            "case_sensitive": caso_sensitivo,
            "filtros_padrao_aplicados": use_defaults and (not keywords_include and not keywords_exclude),
            "configuracao_segura": False
        }


news_filter = NewsFilter()
