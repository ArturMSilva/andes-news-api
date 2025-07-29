import requests
from bs4 import BeautifulSoup
import re
import time
from typing import Dict, List
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AndesScraper:
    """Classe para realizar scraping do site da ANDES"""
    
    def __init__(self):
        self.base_url = 'https://andes.org.br'
        self.noticias_url = 'https://andes.org.br/sites/noticias'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.categorias_conhecidas = ['Nacional', 'Internacional', 'Outras lutas', 'Eventos']
    
    def extrair_resumo_e_imagem_noticia(self, url_noticia: str) -> Dict[str, str]:
        """
        Acessa uma notícia individual e extrai o resumo/introdução e imagem
        
        Args:
            url_noticia: URL da notícia individual
            
        Returns:
            Dict com 'resumo' e 'imagem'
        """
        try:
            logger.info(f"Extraindo dados da notícia: {url_noticia}")
            response = requests.get(url_noticia, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            soup_noticia = BeautifulSoup(response.text, 'html.parser')
            
            resumo = ""
            imagem_url = ""
            
            # Extrair resumo
            resumo = self._extrair_resumo(soup_noticia)
            
            # Extrair imagem
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
        """Extrai o resumo da notícia"""
        resumo = ""
        
        # Primeiro: procurar por div de conteúdo específico
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
        
        # Se não encontrou, procurar por parágrafo introdutório geral
        if not resumo:
            paragrafos = soup_noticia.find_all('p')
            for p in paragrafos:
                texto = p.get_text().strip()
                # Filtrar textos irrelevantes
                if (len(texto) > 50 and 
                    not texto.startswith('O nosso site') and
                    not texto.startswith('Utilizamos cookies') and
                    not 'cookies' in texto.lower() and
                    not texto.startswith('Home') and
                    not texto.startswith('A Entidade')):
                    resumo = texto
                    break
        
        # Limitar o tamanho do resumo e limpar
        if resumo:
            resumo = re.sub(r'\s+', ' ', resumo)  # Normalizar espaços
            if len(resumo) > 300:
                resumo = resumo[:300] + "..."
                
        return resumo
    
    def _extrair_imagem(self, soup_noticia) -> str:
        """Extrai a URL da imagem principal da notícia"""
        imagem_url = ""
        
        # Estratégia 1: Buscar imagens no conteúdo principal da notícia
        # Excluir imagens da sidebar/relacionadas
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
                # Excluir imagens da sidebar (com classes específicas)
                img_parent_classes = ' '.join(img.parent.get('class', []) if img.parent else [])
                
                # Skip imagens de outras notícias (sidebar/relacionadas)
                if any(skip_class in img_parent_classes.lower() for skip_class in 
                       ['img-capa-interna', 'sidebar', 'related', 'thumb', 'miniatura']):
                    continue
                
                if img_src and self._is_imagem_valida(img_src):
                    candidate_url = self._normalizar_url_imagem(img_src)
                    if self._verificar_imagem_acessivel(candidate_url):
                        imagem_url = candidate_url
                        break
            
            if imagem_url:  # Se encontrou, parar de procurar
                break
        
        # Estratégia 2: Se não encontrou no conteúdo, buscar por seletores específicos
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
        
        # Estratégia 3: Como último recurso, buscar qualquer imagem válida (exceto sidebar)
        if not imagem_url:
            all_images = soup_noticia.find_all('img')
            for img in all_images:
                img_src = img.get('src', '')
                
                # Verificar se não está na sidebar/relacionadas
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
        """Converte URL relativa para absoluta e corrige protocolos"""
        img_src = img_src.strip()
        
        if img_src.startswith('//'):
            # URLs que começam com // (protocol-relative)
            return f"https:{img_src}"
        elif img_src.startswith('/'):
            # URLs relativas
            return f"{self.base_url}{img_src}"
        elif img_src.startswith('http://'):
            # Converter http para https para consistência
            return img_src.replace('http://', 'https://')
        elif img_src.startswith('https://'):
            # URLs absolutas com HTTPS já estão ok
            return img_src
        else:
            # URLs relativas sem barra inicial
            return f"{self.base_url}/{img_src}"
    
    def _is_imagem_valida(self, img_src: str) -> bool:
        """Verifica se é uma imagem válida (não é ícone ou logo) - versão melhorada"""
        # Termos que indicam imagens não relevantes para o conteúdo
        invalid_terms = ['icon', 'logo', 'avatar', 'sprite']
        # Removemos 'banner' da lista pois pode ser imagem legítima do conteúdo
        
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        
        # Verificar se tem extensão válida
        has_valid_extension = any(img_src.lower().endswith(ext) for ext in valid_extensions)
        
        # Verificar se não contém termos inválidos
        has_invalid_terms = any(term in img_src.lower() for term in invalid_terms)
        
        # Verificar se não é SVG
        is_svg = img_src.endswith('.svg')
        
        # Verificar se não é muito pequena (possível ícone)
        is_small_icon = any(size in img_src.lower() for size in ['16x16', '32x32', '24x24'])
        
        return has_valid_extension and not has_invalid_terms and not is_svg and not is_small_icon
    
    def _verificar_imagem_acessivel(self, img_url: str) -> bool:
        """Verifica se a imagem é realmente acessível"""
        try:
            response = requests.head(img_url, headers=self.headers, timeout=5)
            return response.status_code == 200 and 'image' in response.headers.get('content-type', '')
        except:
            return False
    
    def obter_noticias(self, max_noticias: int = 10) -> List[Dict]:
        """
        Obtém lista de notícias do site da ANDES ordenadas por data (mais recentes primeiro)
        
        Args:
            max_noticias: Número máximo de notícias para extrair
            
        Returns:
            Lista de dicionários com dados das notícias ordenadas por data
        """
        try:
            logger.info(f"Iniciando scraping de {max_noticias} notícias")
            
            # Coletar notícias de múltiplas páginas se necessário
            all_unique_links = {}
            page = 0
            
            while len(all_unique_links) < max_noticias and page < 10:  # Máximo 10 páginas
                url = f"{self.noticias_url}?page={page}" if page > 0 else self.noticias_url
                logger.info(f"Buscando notícias na página {page}: {url}")
                
                response = requests.get(url, headers=self.headers, timeout=15)
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Encontrar links de notícias
                noticias_links = soup.find_all('a', href=re.compile(r'/conteudos/noticia/'))
                
                new_links_found = 0
                for link in noticias_links:
                    href = link.get('href')
                    if href and href not in all_unique_links:
                        all_unique_links[href] = link
                        new_links_found += 1
                
                logger.info(f"Página {page}: {new_links_found} novos links encontrados")
                
                # Se não encontrou novos links, parar
                if new_links_found == 0:
                    break
                    
                page += 1
            
            # Converter de volta para lista
            noticias_links_filtrados = list(all_unique_links.values())
            
            # Se ainda não temos notícias suficientes, buscar na página principal
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
            
            # Primeiro, processar TODAS as notícias para extrair as datas
            noticias_com_metadata = []
            logger.info(f"Processando {len(noticias_links_filtrados)} links únicos encontrados")
            
            for i, link in enumerate(noticias_links_filtrados):
                try:
                    # Extrair metadados básicos (título, categoria, data) sem acessar a página individual
                    href = link.get('href')
                    if href.startswith('/'):
                        link_completo = f"{self.base_url}{href}"
                    else:
                        link_completo = href
                    
                    titulo = self._extrair_titulo(link)
                    # Aceitar títulos mais curtos - se conseguiu extrair algo
                    if not titulo or len(titulo) <= 2:
                        continue
                        
                    categoria, data = self._extrair_categoria_e_data(link)
                    
                    # Converter data para objeto datetime para ordenação
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
            
            # Ordenar por data (mais recente primeiro)
            noticias_com_metadata.sort(key=lambda x: x['data_obj'], reverse=True)
            
            # Ajustar o número de notícias para processar baseado no que conseguimos coletar
            max_a_processar = min(max_noticias, len(noticias_com_metadata))
            logger.info(f"Notícias ordenadas por data. Processando {max_a_processar} mais recentes de {len(noticias_com_metadata)} coletadas...")
            
            # Agora processar apenas as N mais recentes para extrair resumo e imagem
            noticias_processadas = []
            contador = 0
            
            for noticia_meta in noticias_com_metadata:
                if contador >= max_a_processar:
                    break
                    
                try:
                    # Extrair resumo e imagem
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
                    
                    # Pausa entre requisições
                    if contador < max_noticias:  # Não pausar na última
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
        """Processa um link individual de notícia"""
        # Link completo
        href = link.get('href')
        if href.startswith('/'):
            link_completo = f"{self.base_url}{href}"
        else:
            link_completo = href
        
        # Extrair título
        titulo = self._extrair_titulo(link)
        
        if len(titulo) <= 10:
            return None
            
        # Extrair categoria e data
        categoria, data = self._extrair_categoria_e_data(link)
        
        # Extrair resumo e imagem
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
        """Extrai e limpa o título da notícia - versão mais robusta"""
        titulo = link.get_text().strip()
        
        # Se título vazio ou muito curto, procurar em elementos próximos
        if not titulo or len(titulo) < 10:
            # Procurar no parent
            parent = link.parent
            if parent:
                titulo = parent.get_text().strip()
            
            # Se ainda estiver vazio, procurar no title do link
            if not titulo and link.get('title'):
                titulo = link.get('title').strip()
            
            # Se ainda estiver vazio, tentar extrair do href
            if not titulo:
                href = link.get('href', '')
                # Tentar extrair título do slug da URL
                if '/conteudos/noticia/' in href:
                    slug = href.split('/conteudos/noticia/')[-1]
                    slug = slug.replace('-', ' ').replace('1', '').strip()
                    titulo = slug.title()
        
        # Limpar título
        titulo = re.sub(r'\s+', ' ', titulo).strip()
        
        # Remover categoria do início se presente
        for cat in self.categorias_conhecidas:
            if titulo.startswith(cat):
                titulo = titulo[len(cat):].strip()
                break
        
        # Remover data do final (padrão: "DD de Mês de YYYY")
        titulo = re.sub(r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$', '', titulo).strip()
        
        # Se o título ainda estiver muito curto, tentar acessar a página da notícia
        if len(titulo) < 10:
            href = link.get('href')
            if href:
                url_completa = f"{self.base_url}{href}" if href.startswith('/') else href
                try:
                    response = requests.get(url_completa, headers=self.headers, timeout=10)
                    soup_noticia = BeautifulSoup(response.text, 'html.parser')
                    
                    # Procurar título na página da notícia
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
        """Extrai categoria e data do contexto do link - versão melhorada"""
        categoria = 'Sem categoria'
        data = 'Data não encontrada'
        
        # Se conseguir extrair data do href/URL
        href = link.get('href', '')
        
        # Primeiro tentar extrair data do contexto ao redor do link
        container = link.parent
        data_encontrada = None
        
        if container:
            # Buscar em diferentes níveis do container
            for level in range(5):  # Aumentei para 5 níveis
                current_container = container
                for _ in range(level):
                    if current_container and current_container.parent:
                        current_container = current_container.parent
                    else:
                        break
                
                if current_container:
                    texto_container = current_container.get_text()
                    
                    # Extrair categoria
                    for cat in self.categorias_conhecidas:
                        if cat.lower() in texto_container.lower():
                            categoria = cat
                            break
                    
                    # Extrair data com padrão mais robusto
                    padrao_data = r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})'
                    match_data = re.search(padrao_data, texto_container)
                    
                    if match_data:
                        data_encontrada = match_data.group(1)
                        break
            
            if data_encontrada:
                data = data_encontrada
        
        # Se não encontrou data no contexto, tentar extrair do título do link
        if data == 'Data não encontrada':
            titulo_link = link.get_text()
            match_data = re.search(r'(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})', titulo_link)
            if match_data:
                data = match_data.group(1)
        
        # Se ainda não encontrou, usar data atual como fallback
        if data == 'Data não encontrada':
            from datetime import datetime
            data = datetime.now().strftime('%d de %B de %Y')
            # Traduzir mês para português
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
        """Converte string de data em objeto datetime para ordenação"""
        try:
            meses = {
                'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
                'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
                'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
            }
            
            # Extrair dia, mês e ano
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
