from .scrapers import multi_site_scraper
from typing import Dict, List
from datetime import datetime
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AndesScraper:
    
    def __init__(self):
        self.base_url = 'https://andes.org.br'
        self.noticias_url = 'https://andes.org.br/sites/noticias'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.categorias_conhecidas = ['Nacional', 'Internacional', 'Outras lutas', 'Eventos']
        
        self._multi_scraper = multi_site_scraper
    
    def extrair_resumo_e_imagem_noticia(self, url_noticia: str) -> Dict[str, str]:
        andes_scraper = self._multi_scraper.scrapers['andes']
        return andes_scraper.extrair_resumo_e_imagem_noticia(url_noticia)
    
    def obter_noticias(self, max_noticias: int = 10, apply_filters: bool = None, 
                      keywords_include: list = None, keywords_exclude: list = None,
                      titulo_apenas: bool = False, caso_sensitivo: bool = False) -> List[Dict]:
        try:
            logger.info(f"🔄 NOVO: Buscando notícias de MÚLTIPLOS SITES - {max_noticias} notícias")
            
            noticias = self._multi_scraper.obter_noticias(
                max_noticias=max_noticias,
                apply_filters=apply_filters,
                keywords_include=keywords_include,
                keywords_exclude=keywords_exclude,
                titulo_apenas=titulo_apenas,
                caso_sensitivo=caso_sensitivo,
                sites=['andes', 'csp-conlutas']
            )
            
            for noticia in noticias:
                if 'data_obj' in noticia:
                    del noticia['data_obj']
            
            logger.info(f"✅ Scraping concluído: {len(noticias)} notícias de múltiplos sites")
            return noticias
            
        except Exception as e:
            logger.error(f"❌ Erro no scraping multi-site: {str(e)}")
            logger.info("🔄 Tentando fallback apenas com ANDES...")
            try:
                noticias = self._multi_scraper.obter_noticias(
                    max_noticias=max_noticias,
                    apply_filters=apply_filters,
                    keywords_include=keywords_include,
                    keywords_exclude=keywords_exclude,
                    titulo_apenas=titulo_apenas,
                    caso_sensitivo=caso_sensitivo,
                    sites=['andes']
                )
                
                for noticia in noticias:
                    if 'data_obj' in noticia:
                        del noticia['data_obj']
                
                logger.info(f"✅ Fallback concluído: {len(noticias)} notícias apenas do ANDES")
                return noticias
            except Exception as fallback_error:
                logger.error(f"❌ Erro no fallback: {str(fallback_error)}")
                raise Exception(f"Erro ao obter notícias: {str(e)}")
    
    def _extrair_titulo(self, link) -> str:
        andes_scraper = self._multi_scraper.scrapers['andes']
        return andes_scraper._extrair_titulo(link)
    
    def _extrair_categoria_e_data(self, link) -> tuple:
        andes_scraper = self._multi_scraper.scrapers['andes']
        return andes_scraper._extrair_categoria_e_data(link)
    
    def _parse_date_string(self, data_str: str) -> datetime:
        andes_scraper = self._multi_scraper.scrapers['andes']
        return andes_scraper._parse_date_string(data_str)
