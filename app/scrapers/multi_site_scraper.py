from .andes_scraper import AndesScraper
from .csp_conlutas_scraper import CSPConlutasScraper
import requests
from bs4 import BeautifulSoup
import time
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MultiSiteScraper:
    
    def __init__(self):
        self.scrapers = {
            'andes': AndesScraper(),
            'csp-conlutas': CSPConlutasScraper()
        }
    
    def obter_noticias(self, max_noticias: int = 10, apply_filters: bool = None, 
                      keywords_include: list = None, keywords_exclude: list = None,
                      titulo_apenas: bool = False, caso_sensitivo: bool = False,
                      sites: List[str] = None) -> List[Dict]:
        try:
            logger.info(f"Iniciando scraping multi-site de {max_noticias} notícias")
            
            if apply_filters or keywords_include or keywords_exclude:
                from ..filters import news_filter
            
            if sites is None:
                sites_ativos = list(self.scrapers.keys())
            else:
                sites_ativos = [site for site in sites if site in self.scrapers]
            
            logger.info(f"Sites ativos: {sites_ativos}")
            
            noticias_por_site = max(max_noticias // len(sites_ativos), 5)
            logger.info(f"Buscando {noticias_por_site} notícias por site")
            
            todas_noticias = []
            
            for site_nome in sites_ativos:
                try:
                    logger.info(f"Buscando notícias do {site_nome.upper()}")
                    scraper = self.scrapers[site_nome]
                    
                    noticias_site = self._obter_noticias_site(
                        scraper, 
                        noticias_por_site,
                        site_nome
                    )
                    
                    logger.info(f"{site_nome.upper()}: {len(noticias_site)} notícias coletadas")
                    todas_noticias.extend(noticias_site)
                    
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Erro ao buscar notícias do {site_nome}: {str(e)}")
                    continue
            
            todas_noticias.sort(key=lambda x: x.get('data_obj', datetime.min), reverse=True)
            
            noticias_finais = todas_noticias[:max_noticias]
            for i, noticia in enumerate(noticias_finais):
                noticia['numero'] = i + 1
            
            logger.info(f"Total coletado: {len(noticias_finais)} notícias de {len(sites_ativos)} sites")
            
            if apply_filters or keywords_include or keywords_exclude:
                noticias_filtradas = news_filter.filter_news(
                    noticias_finais,
                    keywords_include=keywords_include,
                    keywords_exclude=keywords_exclude,
                    titulo_apenas=titulo_apenas,
                    caso_sensitivo=caso_sensitivo,
                    use_defaults=apply_filters
                )
                logger.info(f"Filtragem aplicada: {len(noticias_filtradas)}/{len(noticias_finais)} notícias mantidas")
                return noticias_filtradas
            
            return noticias_finais
            
        except Exception as e:
            logger.error(f"Erro no scraping multi-site: {str(e)}")
            raise Exception(f"Erro ao obter notícias: {str(e)}")
    
    def _obter_noticias_site(self, scraper, max_noticias: int, site_nome: str) -> List[Dict]:
        try:
            all_unique_links = {}
            page = 0
            max_pages = 10
            
            while len(all_unique_links) < max_noticias * 2 and page < max_pages:
                if page == 0:
                    url = scraper.noticias_url
                else:
                    if site_nome == 'andes':
                        url = f"{scraper.noticias_url}?page={page}"
                    else:
                        url = f"{scraper.noticias_url}?p={page}"
                
                logger.info(f"{site_nome.upper()} - Página {page}: {url}")
                
                response = requests.get(url, headers=scraper.headers, timeout=15)
                soup = scraper._processar_pagina_com_encoding_correto(response)
                
                links_noticias = scraper._extrair_links_noticias(soup)
                
                new_links_found = 0
                for link in links_noticias:
                    href = link.get('href')
                    if href and href not in all_unique_links:
                        all_unique_links[href] = link
                        new_links_found += 1
                
                logger.info(f"{site_nome.upper()} - Página {page}: {new_links_found} novos links")
                
                if new_links_found == 0:
                    break
                    
                page += 1
            
            noticias_com_metadata = []
            for i, (href, link) in enumerate(all_unique_links.items()):
                try:
                    if href.startswith('/'):
                        link_completo = f"{scraper.base_url}{href}"
                    else:
                        link_completo = href
                    
                    titulo = scraper._extrair_titulo(link)
                    if not titulo or len(titulo) <= 2:
                        continue
                        
                    categoria, data = scraper._extrair_categoria_e_data(link)
                    data_obj = scraper._parse_date_string(data)
                    
                    noticias_com_metadata.append({
                        'link': link,
                        'link_completo': link_completo,
                        'titulo': titulo,
                        'categoria': categoria,
                        'data': data,
                        'data_obj': data_obj,
                        'href': href,
                        'site': scraper.get_site_name()
                    })
                    
                except Exception as e:
                    logger.warning(f"{site_nome.upper()} - Erro ao processar link {i+1}: {str(e)}")
                    continue
            
            noticias_com_metadata.sort(key=lambda x: x['data_obj'], reverse=True)
            max_a_processar = min(max_noticias, len(noticias_com_metadata))
            
            noticias_processadas = []
            for i, noticia_meta in enumerate(noticias_com_metadata[:max_a_processar]):
                try:
                    dados_noticia = scraper.extrair_resumo_e_imagem_noticia(noticia_meta['link_completo'])
                    
                    noticia_final = {
                        'numero': i + 1,
                        'titulo': noticia_meta['titulo'],
                        'resumo': dados_noticia['resumo'],
                        'imagem': dados_noticia['imagem'],
                        'link': noticia_meta['link_completo'],
                        'categoria': noticia_meta['categoria'],
                        'data': noticia_meta['data'],
                        'data_obj': noticia_meta['data_obj'],
                        'site': noticia_meta['site']
                    }
                    
                    noticias_processadas.append(noticia_final)
                    
                    if i < max_a_processar - 1:
                        time.sleep(1)
                        
                except Exception as e:
                    logger.warning(f"{site_nome.upper()} - Erro ao processar notícia completa: {str(e)}")
                    continue
            
            return noticias_processadas
            
        except Exception as e:
            logger.error(f"Erro ao obter notícias do {site_nome}: {str(e)}")
            return []


multi_site_scraper = MultiSiteScraper()