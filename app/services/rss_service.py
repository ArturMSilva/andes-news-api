from datetime import datetime
from typing import List, Dict
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import html

from ..core import settings, get_logger

logger = get_logger(__name__)


class RSSService:
    
    def generate_rss_xml(self, noticias: List[Dict]) -> str:
        try:
            rss = Element("rss")
            rss.set("version", "2.0")
            rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
            
            channel = SubElement(rss, "channel")
            
            self._add_channel_metadata(channel)
            
            for noticia in noticias:
                self._add_news_item(channel, noticia)
            
            return self._format_xml(rss)
            
        except Exception as e:
            logger.error(f"Erro ao gerar RSS XML: {str(e)}")
            return self.generate_error_rss(str(e))
    
    def generate_empty_rss(self) -> str:
        rss = Element("rss")
        rss.set("version", "2.0")
        
        channel = SubElement(rss, "channel")
        
        title = SubElement(channel, "title")
        title.text = "ANDES News - Sem notícias disponíveis"
        
        description = SubElement(channel, "description")
        description.text = "Nenhuma notícia encontrada no momento"
        
        link = SubElement(channel, "link")
        link.text = settings.ANDES_BASE_URL
        
        return self._format_xml(rss)
    
    def generate_error_rss(self, error_message: str) -> str:
        rss = Element("rss")
        rss.set("version", "2.0")
        
        channel = SubElement(rss, "channel")
        
        title = SubElement(channel, "title")
        title.text = "ANDES News - Erro"
        
        description = SubElement(channel, "description")
        description.text = f"Erro ao obter notícias: {error_message}"
        
        link = SubElement(channel, "link")
        link.text = settings.ANDES_BASE_URL
        
        return self._format_xml(rss)
    
    def _add_channel_metadata(self, channel: Element) -> None:
        title = SubElement(channel, "title")
        title.text = "ANDES News - Notícias do Sindicato Nacional dos Docentes"
        
        description = SubElement(channel, "description")
        description.text = "Feed RSS com as últimas notícias do Sindicato Nacional dos Docentes das Instituições de Ensino Superior (ANDES)"
        
        link = SubElement(channel, "link")
        link.text = settings.ANDES_BASE_URL
        
        language = SubElement(channel, "language")
        language.text = "pt-BR"
        
        last_build_date = SubElement(channel, "lastBuildDate")
        last_build_date.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
        
        generator = SubElement(channel, "generator")
        generator.text = f"{settings.APP_NAME} v{settings.VERSION}"
        
        atom_link = SubElement(channel, "atom:link")
        atom_link.set("href", f"{settings.API_BASE_URL}/rss")
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")
    
    def _add_news_item(self, channel: Element, noticia: Dict) -> None:
        item = SubElement(channel, "item")
        
        item_title = SubElement(item, "title")
        item_title.text = noticia.get('titulo', 'Título não disponível')
        
        item_link = SubElement(item, "link")
        item_link.text = noticia.get('link', settings.ANDES_BASE_URL + '/sites/noticias')
        
        item_description = SubElement(item, "description")
        resumo = noticia.get('resumo', 'Resumo não disponível')
        if resumo == 'Resumo não disponível':
            descricao_content = noticia.get('titulo', 'Título não disponível')
        else:
            descricao_content = resumo
        
        item_description.set('_cdata_content', descricao_content)
        
        guid = SubElement(item, "guid")
        guid.text = noticia.get('link', f"noticia-{noticia.get('numero', 0)}")
        guid.set("isPermaLink", "true" if noticia.get('link') else "false")
        
        if noticia.get('categoria'):
            category = SubElement(item, "category")
            category.text = noticia['categoria']
        
        self._add_publication_date(item, noticia)
        
        self._add_image_enclosure(item, noticia)
    
    def _add_publication_date(self, item: Element, noticia: Dict) -> None:
        if noticia.get('data') and noticia['data'] != 'Data não informada':
            pub_date = SubElement(item, "pubDate")
            try:
                data_noticia_str = noticia['data']
                data_formatada = self._converter_data_para_rfc2822(data_noticia_str)
                pub_date.text = data_formatada
            except Exception as e:
                logger.warning(f"Erro ao formatar data da notícia '{noticia.get('data')}': {e}")
                pub_date.text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
    
    def _add_image_enclosure(self, item: Element, noticia: Dict) -> None:
        if (noticia.get('imagem') and 
            noticia['imagem'] not in ['Imagem não disponível', 'Imagem não encontrada'] and
            noticia['imagem'].startswith('http')):
            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", noticia['imagem'])
            enclosure.set("type", "image/jpeg")
            enclosure.set("length", "0")
    
    def _format_xml(self, rss: Element) -> str:
        xml_str = tostring(rss, encoding='unicode')
        
        xml_str = self._process_cdata_sections(xml_str)
        
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ", encoding=None)
        
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _process_cdata_sections(self, xml_str: str) -> str:
        """Processa as seções CDATA para evitar escape de caracteres"""
        import re
        
        pattern = r'<description\s+_cdata_content="([^"]*)"(?:\s*/>|></description>)'
        
        def replace_cdata(match):
            content = match.group(1)
            content = html.unescape(content)
            return f'<description><![CDATA[{content}]]></description>'
        
        xml_str = re.sub(pattern, replace_cdata, xml_str)
        
        xml_str = re.sub(r'\s+_cdata_content="[^"]*"', '', xml_str)
        
        return xml_str
    
    def _converter_data_para_rfc2822(self, data_str: str) -> str:
     
        try:
            meses = {
                'janeiro': 'Jan', 'fevereiro': 'Feb', 'março': 'Mar', 'abril': 'Apr',
                'maio': 'May', 'junho': 'Jun', 'julho': 'Jul', 'agosto': 'Aug',
                'setembro': 'Sep', 'outubro': 'Oct', 'novembro': 'Nov', 'dezembro': 'Dec'
            }
            
            dias_semana = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            
            partes = data_str.lower().split()
            if len(partes) >= 5:
                dia = int(partes[0])
                mes_nome = partes[2]
                ano = int(partes[4])
                
                mes_abrev = meses.get(mes_nome, 'Jan')
                
                data_obj = datetime(ano, list(meses.keys()).index(mes_nome) + 1, dia)
                dia_semana = dias_semana[data_obj.weekday()]
                
                return f"{dia_semana}, {dia:02d} {mes_abrev} {ano} 12:00:00 +0000"
                
        except Exception as e:
            logger.warning(f"Erro ao converter data '{data_str}' para RFC 2822: {e}")
        
        return datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")


rss_service = RSSService()
