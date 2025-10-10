from .base_scraper import BaseScraper
import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AndesScraper(BaseScraper):
    
    def __init__(self):
        super().__init__(
            base_url='https://andes.org.br',
            noticias_url='https://andes.org.br/sites/noticias'
        )
        self.categorias_conhecidas = ['Nacional', 'Internacional', 'Outras lutas', 'Eventos']
    
    def get_site_name(self) -> str:
        return "ANDES"
    
    def _extrair_links_noticias(self, soup: BeautifulSoup) -> List:
        return soup.find_all('a', href=re.compile(r'/conteudos/noticia/'))
    
    def _extrair_titulo(self, link) -> str:
        # PRIORIDADE: Sempre tentar buscar o título na página da notícia primeiro
        titulo_da_pagina = None
        href = link.get('href')
        
        if href:
            url_completa = f"{self.base_url}{href}" if href.startswith('/') else href
            try:
                response = requests.get(url_completa, headers=self.headers, timeout=10)
                soup_noticia = self._processar_pagina_com_encoding_correto(response)
                
                # Buscar especificamente por H2 primeiro (onde está o título real no ANDES)
                title_selectors = ['h2', 'h1', '.title', '.headline', 'title']
                
                # Títulos genéricos para ignorar
                titulos_genericos = [
                    'SINDICATO NACIONAL DOS DOCENTES',
                    'ANDES',
                    'ASSOCIAÇÃO NACIONAL DOS DOCENTES'
                ]
                
                for selector in title_selectors:
                    title_elem = soup_noticia.select_one(selector)
                    if title_elem:
                        titulo_pagina = self._limpar_texto(title_elem.get_text())
                        titulo_pagina = re.sub(r'^\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s*', '', titulo_pagina).strip()
                        titulo_pagina = re.sub(r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$', '', titulo_pagina).strip()
                        
                        # Verificar se não é um título genérico
                        e_generico = any(gen.upper() in titulo_pagina.upper() for gen in titulos_genericos)
                        
                        if len(titulo_pagina) > 10 and not e_generico:
                            titulo_da_pagina = titulo_pagina
                            break
            except:
                pass
        
        # Se conseguiu extrair da página, usar esse título
        if titulo_da_pagina:
            return titulo_da_pagina
        
        # FALLBACK: Se não conseguiu da página, tentar extrair do link
        titulo = self._limpar_texto(link.get_text())
        
        if not titulo or len(titulo) < 10:
            parent = link.parent
            if parent:
                titulo = self._limpar_texto(parent.get_text())
            
            if not titulo and link.get('title'):
                titulo = self._limpar_texto(link.get('title'))
            
            # ÚLTIMO RECURSO: Gerar título da URL
            if not titulo:
                if href and '/conteudos/noticia/' in href:
                    slug = href.split('/conteudos/noticia/')[-1]
                    slug = slug.replace('-', ' ').replace('1', '').strip()
                    titulo = slug.title()
        
        titulo = re.sub(r'\s+', ' ', titulo).strip()
        titulo = re.sub(r'^\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s*', '', titulo).strip()
        
        for cat in self.categorias_conhecidas:
            if titulo.startswith(cat):
                titulo = titulo[len(cat):].strip()
                break
        
        titulo = re.sub(r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$', '', titulo).strip()
        
        return titulo
    
    def _extrair_categoria_e_data(self, link) -> tuple:
        categoria = 'Sem categoria'
        data = 'Data não encontrada'
        
        href = link.get('href', '')
        container = link.parent
        data_encontrada = None
        
        if container:
            for level in range(5):
                current_container = container
                for _ in range(level):
                    if current_container and current_container.parent:
                        current_container = current_container.parent
                    else:
                        break
                
                if current_container:
                    texto_container = current_container.get_text()
                    
                    for cat in self.categorias_conhecidas:
                        if cat.lower() in texto_container.lower():
                            categoria = cat
                            break
                    
                    padrao_data = r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})'
                    match_data = re.search(padrao_data, texto_container)
                    
                    if match_data:
                        data_encontrada = match_data.group(1)
                        break
            
            if data_encontrada:
                data = data_encontrada
        
        if data == 'Data não encontrada':
            titulo_link = link.get_text()
            match_data = re.search(r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', titulo_link)
            if match_data:
                data = match_data.group(1)
        
        if data == 'Data não encontrada':
            from datetime import datetime
            data = datetime.now().strftime('%d de %B de %Y')
            meses_pt = {
                'January': 'janeiro', 'February': 'fevereiro', 'March': 'março',
                'April': 'abril', 'May': 'maio', 'June': 'junho',
                'July': 'julho', 'August': 'agosto', 'September': 'setembro',
                'October': 'outubro', 'November': 'novembro', 'December': 'dezembro'
            }
            for en, pt in meses_pt.items():
                if en in data:
                    data = data.replace(en, pt)
                    break
        
        return categoria, data
    
    def _extrair_resumo(self, soup_noticia) -> str:
        resumo = ""
        
        content_selectors = [
            'div.field-type-text-with-summary',
            'div.content',
            'div.article-content',
            'div.news-content',
            'div.field-name-body',
            'div.field-item'
        ]
        
        for selector in content_selectors:
            content_div = soup_noticia.select_one(selector)
            if content_div:
                primeiro_p = content_div.find('p')
                if primeiro_p:
                    resumo = self._limpar_texto(primeiro_p.get_text())
                    break
        
        if not resumo:
            paragrafos = soup_noticia.find_all('p')
            for p in paragrafos:
                texto = self._limpar_texto(p.get_text())
                if (len(texto) > 50 and 
                    not texto.startswith('O nosso site') and
                    not texto.startswith('Utilizamos cookies') and
                    not 'cookies' in texto.lower() and
                    not texto.startswith('Home') and
                    not texto.startswith('A Entidade')):
                    resumo = texto
                    break
        
        if resumo:
            resumo = re.sub(r'\s+', ' ', resumo)
            if len(resumo) > 300:
                resumo = resumo[:300] + "..."
                
        return resumo
    
    def _extrair_imagem(self, soup_noticia) -> str:
        imagem_url = ""
        
        content_selectors = [
            'div.field-name-body img',
            'div.field-type-text-with-summary img', 
            'article.node-noticia img',
            'div.content img',
            'div.text-content img',
            'div.node-content img',
            'main img'
        ]
        
        for selector in content_selectors:
            content_images = soup_noticia.select(selector)
            for img in content_images:
                img_src = img.get('src', '')
                img_parent_classes = ' '.join(img.parent.get('class', []) if img.parent else [])
                
                if any(skip_class in img_parent_classes.lower() for skip_class in 
                       ['img-capa-interna', 'sidebar', 'related', 'thumb', 'miniatura']):
                    continue
                
                if img_src and self._is_imagem_valida(img_src):
                    candidate_url = self._normalizar_url_imagem(img_src)
                    if self._verificar_imagem_acessivel(candidate_url):
                        imagem_url = candidate_url
                        break
            
            if imagem_url:
                break
        
        if not imagem_url:
            specific_selectors = [
                'img.field-content',
                'div.field-name-field-imagem img',
                'div.field-type-image img',
                'div.image img'
            ]
            
            for selector in specific_selectors:
                img_element = soup_noticia.select_one(selector)
                if img_element:
                    img_src = img_element.get('src')
                    if img_src and self._is_imagem_valida(img_src):
                        candidate_url = self._normalizar_url_imagem(img_src)
                        if self._verificar_imagem_acessivel(candidate_url):
                            imagem_url = candidate_url
                            break
        
        if not imagem_url:
            all_images = soup_noticia.find_all('img')
            for img in all_images:
                img_src = img.get('src', '')
                
                img_parent_classes = ' '.join(img.parent.get('class', []) if img.parent else [])
                if any(skip_class in img_parent_classes.lower() for skip_class in 
                       ['img-capa-interna', 'sidebar', 'related', 'thumb', 'miniatura', 'navbar']):
                    continue
                
                if img_src and self._is_imagem_valida(img_src):
                    candidate_url = self._normalizar_url_imagem(img_src)
                    if self._verificar_imagem_acessivel(candidate_url):
                        imagem_url = candidate_url
                        break
                    break
                    
        return imagem_url