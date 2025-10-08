from abc import ABC, abstractmethod
from typing import Dict, List
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import html
import logging

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    
    def __init__(self, base_url: str, noticias_url: str):
        self.base_url = base_url
        self.noticias_url = noticias_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def _normalizar_url_imagem(self, img_src: str) -> str:
        img_src = img_src.strip()
        
        if img_src.startswith('//'):
            return f"https:{img_src}"
        elif img_src.startswith('/'):
            return f"{self.base_url}{img_src}"
        elif img_src.startswith('http://'):
            return img_src.replace('http://', 'https://')
        elif img_src.startswith('https://'):
            return img_src
        else:
            return f"{self.base_url}/{img_src}"
    
    def _is_imagem_valida(self, img_src: str) -> bool:
        invalid_terms = ['icon', 'logo', 'avatar', 'sprite']
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        
        has_valid_extension = any(img_src.lower().endswith(ext) for ext in valid_extensions)
        has_invalid_terms = any(term in img_src.lower() for term in invalid_terms)
        is_svg = img_src.endswith('.svg')
        is_small_icon = any(size in img_src.lower() for size in ['16x16', '32x32', '24x24'])
        
        return has_valid_extension and not has_invalid_terms and not is_svg and not is_small_icon
    
    def _verificar_imagem_acessivel(self, img_url: str) -> bool:
        try:
            response = requests.head(img_url, headers=self.headers, timeout=5)
            return response.status_code == 200 and 'image' in response.headers.get('content-type', '')
        except:
            return False
    
    def _parse_date_string(self, data_str: str) -> datetime:
        try:
            meses = {
                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
            }
            
            partes = data_str.lower().split()
            if len(partes) >= 5:
                dia = partes[0].zfill(2)
                mes_nome = partes[2]
                ano = partes[4]
                mes_num = meses.get(mes_nome, '01')
                return datetime.strptime(f"{ano}-{mes_num}-{dia}", "%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Erro ao parsear data '{data_str}': {e}")
        
        return datetime.min
    
    def _limpar_texto(self, texto):
        if not texto:
            return ""
        
        texto = str(texto)
        texto = html.unescape(texto)
        texto = texto.replace('�', '')
        texto = re.sub(r'\s+', ' ', texto).strip()
        texto = texto.replace('\n', ' ').replace('\r', ' ')
        
        return texto
    
    @abstractmethod
    def _extrair_links_noticias(self, soup: BeautifulSoup) -> List:
        pass
    
    @abstractmethod
    def _extrair_titulo(self, link_element) -> str:
        pass
    
    @abstractmethod
    def _extrair_categoria_e_data(self, link_element) -> tuple:
        pass
    
    @abstractmethod
    def _extrair_resumo(self, soup_noticia: BeautifulSoup) -> str:
        pass
    
    @abstractmethod
    def _extrair_imagem(self, soup_noticia: BeautifulSoup) -> str:
        pass
    
    @abstractmethod
    def get_site_name(self) -> str:
        pass
    
    def _processar_pagina_com_encoding_correto(self, response):
        encodings = ['utf-8', 'cp1252', 'latin1', 'iso-8859-1']
        
        if response.encoding and response.encoding.lower() != 'iso-8859-1':
            encodings.insert(0, response.encoding)
        
        for encoding in encodings:
            try:
                content = response.content.decode(encoding)
                return BeautifulSoup(content, 'html.parser')
            except UnicodeDecodeError:
                continue
        
        return BeautifulSoup(response.text, 'html.parser')

    def extrair_resumo_e_imagem_noticia(self, url_noticia: str) -> Dict[str, str]:
        try:
            logger.info(f"Extraindo dados da notícia: {url_noticia}")
            response = requests.get(url_noticia, headers=self.headers, timeout=15)
            soup_noticia = self._processar_pagina_com_encoding_correto(response)
            
            resumo = self._extrair_resumo(soup_noticia)
            imagem_url = self._extrair_imagem(soup_noticia)
            
            return {
                'resumo': resumo if resumo else "Resumo não disponível",
                'imagem': imagem_url if imagem_url else "Imagem não disponível"
            }
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da notícia {url_noticia}: {str(e)}")
            return {
                'resumo': f"Erro ao extrair resumo: {str(e)}",
                'imagem': "Imagem não disponível"
            }