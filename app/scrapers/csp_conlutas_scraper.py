from .base_scraper import BaseScraper
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import List
import html
import logging

logger = logging.getLogger(__name__)


class CSPConlutasScraper(BaseScraper):
    
    def __init__(self):
        super().__init__(
            base_url='https://cspconlutas.org.br',
            noticias_url='https://cspconlutas.org.br/noticias'
        )
        self.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
        })
    
    def get_site_name(self) -> str:
        return "CSP-Conlutas"
    
    def _extrair_links_noticias(self, soup: BeautifulSoup) -> List:
        return soup.find_all('a', href=re.compile(r'/noticias/n/\d+/'))
    
    def _extrair_titulo(self, link) -> str:
        titulo = self._limpar_texto(link.get_text())
        
        if titulo and len(titulo) > 10:
            return titulo
        
        if link.get('title'):
            return self._limpar_texto(link.get('title'))
        
        href = link.get('href', '')
        if '/noticias/n/' in href:
            slug = href.split('/')[-1]
            return slug.replace('-', ' ').title()
        
        return "Título não disponível"
    
    def _extrair_categoria_e_data(self, link) -> tuple:
        categoria = 'CSP-Conlutas'
        data = 'Data não encontrada'
        
        container = link.parent
        if container:
            texto_container = container.get_text()
            
            padrao_br = r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})'
            match_br = re.search(padrao_br, texto_container, re.IGNORECASE)
            
            if match_br:
                data = match_br.group(1)
            else:
                padrao_num = r'(\d{1,2}/\d{1,2}/\d{4})'
                match_num = re.search(padrao_num, texto_container)
                
                if match_num:
                    data = self._converter_data_formato(match_num.group(1))
        
        if data == 'Data não encontrada':
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
    
    def _converter_data_formato(self, data_str: str) -> str:
        try:
            meses_pt = [
                'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
            ]
            
            partes = data_str.split('/')
            if len(partes) == 3:
                dia = int(partes[0])
                mes = int(partes[1]) - 1
                ano = partes[2]
                
                if 0 <= mes < 12:
                    return f"{dia} de {meses_pt[mes]} de {ano}"
        except:
            pass
        
        return data_str
    
    def _extrair_resumo(self, soup_noticia) -> str:
        resumo = ""
        
        content_selectors = [
            'div.content',
            'div.article-content',
            'main p',
            'article p',
            '.post-content p',
            '.news-content p'
        ]
        
        for selector in content_selectors:
            elements = soup_noticia.select(selector)
            for element in elements:
                if element.name == 'p':
                    texto = self._limpar_texto(element.get_text())
                else:
                    primeiro_p = element.find('p')
                    if primeiro_p:
                        texto = self._limpar_texto(primeiro_p.get_text())
                    else:
                        continue
                
                if (len(texto) > 50 and 
                    not texto.startswith('Rua Senador') and
                    not texto.startswith('Telefone:') and
                    not texto.startswith('©') and
                    not 'cookie' in texto.lower() and
                    not texto.startswith('Facebook') and
                    not texto.startswith('Twitter')):
                    resumo = texto
                    break
            
            if resumo:
                break
        
        if not resumo:
            paragrafos = soup_noticia.find_all('p')
            for p in paragrafos:
                texto = self._limpar_texto(p.get_text())
                if len(texto) > 50:
                    resumo = texto
                    break
        
        if resumo:
            if len(resumo) > 300:
                resumo = resumo[:300] + "..."
                
        return resumo if resumo else "Resumo não disponível"
    
    def _extrair_imagem(self, soup_noticia) -> str:
        imagem_url = ""
        
        img_elements = soup_noticia.find_all('img')
        for img in img_elements:
            img_src = img.get('src', '')
            if '/arquivo/thumb/noticias/' in img_src:
                candidate_url = self._normalizar_url_imagem(img_src)
                if self._verificar_imagem_acessivel(candidate_url):
                    return candidate_url
        content_selectors = [
            'main img',
            'article img',
            '.content img',
            '.post-content img',
            '.news-content img'
        ]
        
        for selector in content_selectors:
            images = soup_noticia.select(selector)
            for img in images:
                img_src = img.get('src', '')
                
                img_alt = img.get('alt', '').lower()
                img_parent_classes = ' '.join(img.parent.get('class', []) if img.parent else [])
                
                if any(skip_term in img_alt for skip_term in ['facebook', 'twitter', 'whatsapp', 'youtube']):
                    continue
                
                if any(skip_class in img_parent_classes.lower() for skip_class in 
                       ['navigation', 'nav', 'sidebar', 'footer', 'header']):
                    continue
                
                if img_src and self._is_imagem_valida(img_src):
                    candidate_url = self._normalizar_url_imagem(img_src)
                    if self._verificar_imagem_acessivel(candidate_url):
                        return candidate_url
        
        return "Imagem não disponível"
    
    def extrair_resumo_e_imagem_noticia(self, url_noticia: str) -> dict:
        try:
            logger.info(f"Extraindo dados da notícia CSP-Conlutas: {url_noticia}")
            response = requests.get(url_noticia, headers=self.headers, timeout=15)
            
            response.encoding = 'utf-8'
            soup_noticia = BeautifulSoup(response.text, 'html.parser')
            
            resumo = self._extrair_resumo(soup_noticia)
            imagem_url = self._extrair_imagem(soup_noticia)
            
            return {
                'resumo': resumo if resumo else "Resumo não disponível",
                'imagem': imagem_url if imagem_url else "Imagem não disponível"
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da notícia CSP-Conlutas {url_noticia}: {str(e)}")
            return {
                'resumo': f"Erro ao extrair resumo: {str(e)}",
                'imagem': "Imagem não disponível"
            }
    
    def _limpar_texto(self, texto):
        if not texto:
            return ""
        
        texto = html.unescape(texto)
        
        texto = re.sub(r'\s+', ' ', texto).strip()
        
        texto = texto.replace('\n', ' ').replace('\r', ' ')
        
        return texto