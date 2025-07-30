import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List
from datetime import datetime
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
    
    def extrair_resumo_e_imagem_noticia(self, url_noticia: str) -> Dict[str, str]:
        try:
            logger.info(f"Extraindo dados da notícia: {url_noticia}")
            response = requests.get(url_noticia, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            soup_noticia = BeautifulSoup(response.text, 'html.parser')
            
            resumo = ""
            imagem_url = ""
            
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
                    resumo = primeiro_p.get_text().strip()
                    break
        
        if not resumo:
            paragrafos = soup_noticia.find_all('p')
            for p in paragrafos:
                texto = p.get_text().strip()
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
    
    def obter_noticias(self, max_noticias: int = 10) -> List[Dict]:
        try:
            logger.info(f"Iniciando scraping de {max_noticias} notícias")
            
            all_unique_links = {}
            page = 0
            
            while len(all_unique_links) < max_noticias and page < 10:
                url = f"{self.noticias_url}?page={page}" if page > 0 else self.noticias_url
                logger.info(f"Buscando notícias na página {page}: {url}")
                
                response = requests.get(url, headers=self.headers, timeout=15)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                noticias_links = soup.find_all('a', href=re.compile(r'/conteudos/noticia/'))
                
                new_links_found = 0
                for link in noticias_links:
                    href = link.get('href')
                    if href and href not in all_unique_links:
                        all_unique_links[href] = link
                        new_links_found += 1
                
                logger.info(f"Página {page}: {new_links_found} novos links encontrados")
                
                if new_links_found == 0:
                    break
                    
                page += 1
            
            noticias_links_filtrados = list(all_unique_links.values())
            
            if len(noticias_links_filtrados) < max_noticias:
                logger.info(f"Buscando notícias adicionais na página principal")
                try:
                    response_main = requests.get(self.base_url, headers=self.headers, timeout=15)
                    response_main.encoding = 'utf-8'
                    soup_main = BeautifulSoup(response_main.text, 'html.parser')
                    
                    main_links = soup_main.find_all('a', href=re.compile(r'/conteudos/noticia/'))
                    for link in main_links:
                        href = link.get('href')
                        if href and href not in all_unique_links:
                            all_unique_links[href] = link
                    
                    noticias_links_filtrados = list(all_unique_links.values())
                    logger.info(f"Total de links após busca na página principal: {len(noticias_links_filtrados)}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar na página principal: {e}")
            
            logger.info(f"Total de links únicos coletados: {len(noticias_links_filtrados)}")
            
            noticias_com_metadata = []
            logger.info(f"Processando {len(noticias_links_filtrados)} links únicos encontrados")
            
            for i, link in enumerate(noticias_links_filtrados):
                try:
                    href = link.get('href')
                    if href.startswith('/'):
                        link_completo = f"{self.base_url}{href}"
                    else:
                        link_completo = href
                    
                    titulo = self._extrair_titulo(link)
                    if not titulo or len(titulo) <= 2:
                        continue
                        
                    categoria, data = self._extrair_categoria_e_data(link)
                    
                    data_obj = self._parse_date_string(data)
                    
                    noticias_com_metadata.append({
                        'link': link,
                        'link_completo': link_completo,
                        'titulo': titulo,
                        'categoria': categoria,
                        'data': data,
                        'data_obj': data_obj,
                        'href': href
                    })
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar metadados do link {i+1}: {str(e)}")
                    continue
            
            noticias_com_metadata.sort(key=lambda x: x['data_obj'], reverse=True)
            
            max_a_processar = min(max_noticias, len(noticias_com_metadata))
            logger.info(f"Notícias ordenadas por data. Processando {max_a_processar} mais recentes de {len(noticias_com_metadata)} coletadas...")
            
            noticias_processadas = []
            contador = 0
            
            for noticia_meta in noticias_com_metadata:
                if contador >= max_a_processar:
                    break
                    
                try:
                    dados_noticia = self.extrair_resumo_e_imagem_noticia(noticia_meta['link_completo'])
                    
                    noticia_final = {
                        'numero': contador + 1,
                        'titulo': noticia_meta['titulo'],
                        'resumo': dados_noticia['resumo'],
                        'imagem': dados_noticia['imagem'],
                        'link': noticia_meta['link_completo'],
                        'categoria': noticia_meta['categoria'],
                        'data': noticia_meta['data']
                    }
                    
                    noticias_processadas.append(noticia_final)
                    contador += 1
                    
                    if contador < max_noticias:
                        time.sleep(2)
                        
                except Exception as e:
                    logger.warning(f"Erro ao processar notícia completa: {str(e)}")
                    continue
            
            logger.info(f"Scraping concluído. {len(noticias_processadas)} notícias processadas e ordenadas por data")
            return noticias_processadas
            
        except Exception as e:
            logger.error(f"Erro no scraping principal: {str(e)}")
            raise Exception(f"Erro ao obter notícias: {str(e)}")
    
    def _processar_link_noticia(self, link, numero: int) -> Dict:
        href = link.get('href')
        if href.startswith('/'):
            link_completo = f"{self.base_url}{href}"
        else:
            link_completo = href
        
        titulo = self._extrair_titulo(link)
        
        if len(titulo) <= 10:
            return None
            
        categoria, data = self._extrair_categoria_e_data(link)
        
        dados_noticia = self.extrair_resumo_e_imagem_noticia(link_completo)
        
        return {
            'numero': numero,
            'titulo': titulo,
            'resumo': dados_noticia['resumo'],
            'imagem': dados_noticia['imagem'],
            'link': link_completo,
            'categoria': categoria,
            'data': data
        }
    
    def _extrair_titulo(self, link) -> str:
        titulo = link.get_text().strip()
        
        if not titulo or len(titulo) < 10:
            parent = link.parent
            if parent:
                titulo = parent.get_text().strip()
            
            if not titulo and link.get('title'):
                titulo = link.get('title').strip()
            
            if not titulo:
                href = link.get('href', '')
                if '/conteudos/noticia/' in href:
                    slug = href.split('/conteudos/noticia/')[-1]
                    slug = slug.replace('-', ' ').replace('1', '').strip()
                    titulo = slug.title()
        
        titulo = re.sub(r'\s+', ' ', titulo).strip()
        
        for cat in self.categorias_conhecidas:
            if titulo.startswith(cat):
                titulo = titulo[len(cat):].strip()
                break
        
        titulo = re.sub(r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$', '', titulo).strip()
        
        if len(titulo) < 10:
            href = link.get('href')
            if href:
                url_completa = f"{self.base_url}{href}" if href.startswith('/') else href
                try:
                    response = requests.get(url_completa, headers=self.headers, timeout=10)
                    soup_noticia = BeautifulSoup(response.text, 'html.parser')
                    
                    title_selectors = ['h1', 'h2', '.title', '.headline', 'title']
                    for selector in title_selectors:
                        title_elem = soup_noticia.select_one(selector)
                        if title_elem:
                            titulo_pagina = title_elem.get_text().strip()
                            if len(titulo_pagina) > 10:
                                titulo = titulo_pagina
                                break
                except:
                    pass
        
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
