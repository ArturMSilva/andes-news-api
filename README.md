# ANDES News API

API modularizada para extração de notícias do site da ANDES (Sindicato Nacional dos Docentes das Instituições de Ensino Superior) com sistema de cache inteligente para máxima performance.

## 🚀 Funcionalidades

- **Extração automatizada** de notícias do site oficial da ANDES
- **Cache inteligente** com TTL de 15 minutos para performance otimizada
- **Dados estruturados** em JSON com título, resumo, imagem, link, categoria e data
- **Rate limiting** respeitoso com pausa entre requisições
- **API RESTful** com FastAPI
- **Documentação automática** com Swagger UI
- **Logs detalhados** para monitoramento
- **Monitoramento de cache** com estatísticas em tempo real

## 📋 Endpoints

### `GET /noticias`
Retorna as últimas notícias do site da ANDES com cache inteligente.

**Parâmetros:**
- `max_noticias` (opcional): Número de notícias para retornar (1-20, padrão: 5)

**Cache:** Primeira requisição demora 2-15s (scraping), próximas são instantâneas (cache hit).

### `GET /health`
Verificação de saúde da API.

### `GET /cache/stats`
Estatísticas do sistema de cache (hit rate, total de requisições, etc.).

### `GET /cache/info`
Informações detalhadas sobre entradas do cache.

### `POST /cache/clear`
Limpa todo o cache manualmente.

### `GET /docs`
Documentação interativa da API (Swagger UI).

## 🛠️ Tecnologias

- **Python 3.10+**
- **FastAPI** - Framework web moderno e rápido
- **BeautifulSoup4** - Parser HTML para web scraping
- **Requests** - Cliente HTTP
- **Pydantic** - Validação de dados
- **Uvicorn** - Servidor ASGI
- **CacheTools** - Sistema de cache em memória com TTL

## 📦 Instalação Local

### Pré-requisitos
- Python 3.10 ou superior
- pip (gerenciador de pacotes Python)

### Passos para instalação

1. **Clone o repositório**
```bash
git clone <url-do-repositorio>
cd andes-news-api
```

2. **Crie e ative um ambiente virtual**

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux/MacOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Execute a aplicação**
```bash
uvicorn main:app --reload
```

A API estará disponível em `http://localhost:8000`

> **⚠️ Importante:** Sempre ative o ambiente virtual antes de executar a API ou instalar dependências para evitar conflitos com outros projetos Python.

## 📁 Estrutura do Projeto

```
├── main.py           # Aplicação FastAPI principal com cache
├── cache.py          # Sistema de cache inteligente
├── scraper.py        # Classe para web scraping
├── models.py         # Modelos Pydantic
├── requirements.txt  # Dependências Python
├── .gitignore        # Arquivos ignorados pelo Git
├── start.sh         # Script de inicialização
└── README.md        # Documentação
```

## 🔍 Exemplo de Uso

### Obter 5 notícias (padrão)
```bash
curl "http://localhost:8000/noticias"
```

### Obter 10 notícias específicas
```bash
curl "http://localhost:8000/noticias?max_noticias=10"
```

### Verificar saúde da API
```bash
curl "http://localhost:8000/health"
```

### Acessar documentação interativa
Abra no navegador: `http://localhost:8000/docs`

### Verificar estatísticas do cache
```bash
curl "http://localhost:8000/cache/stats"
```

### Exemplo usando PowerShell (Windows)
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/noticias?max_noticias=5" -Method GET
```

### Exemplo usando Python
```python
import requests

# Obter notícias
response = requests.get("http://localhost:8000/noticias?max_noticias=10")
noticias = response.json()
print(f"Total de notícias: {noticias['total_noticias']}")

# Verificar estatísticas do cache
cache_stats = requests.get("http://localhost:8000/cache/stats")
print(f"Cache hit rate: {cache_stats.json()['hit_rate_percentage']}%")
```

## 📊 Exemplo de Resposta

```json
{
  "total_noticias": 5,
  "dados_extraidos": ["Título ✓", "Resumo ✓", "Imagem ✓", "Link ✓", "Categoria ✓", "Data ✓"],
  "noticias": [
    {
      "numero": 1,
      "titulo": "Título da notícia",
      "resumo": "Resumo da notícia...",
      "imagem": "https://andes.org.br/img/...",
      "link": "https://andes.org.br/conteudos/noticia/...",
      "categoria": "Nacional",
      "data": "28 de Julho de 2025"
    }
  ],
  "timestamp": "2025-07-29T10:30:00",
  "cache_info": {
    "cached_at": "2025-07-29T10:30:00",
    "from_cache": true
  }
}
```

## ⚡ Performance

- **Cache inteligente**: TTL de 15 minutos para máxima performance
- **Primeira requisição**: 2-15 segundos (scraping + armazenamento)
- **Próximas requisições**: <100ms (cache hit - 99% mais rápido!)
- **Rate limiting**: 2 segundos entre requisições para respeitar o servidor
- **Timeout**: 15 segundos por requisição
- **Limite**: Máximo 20 notícias por requisição

### 📈 Benefícios do Cache:
- ✅ **Performance drasticamente melhor** - Respostas quase instantâneas
- ✅ **Menor carga no servidor** da ANDES
- ✅ **Experiência do usuário superior**
- ✅ **Dados atualizados** a cada 15 minutos

## 🔒 Segurança

- **User-Agent** apropriado para requisições
- **CORS** configurado
- **Tratamento de erros** robusto
- **Logs** para auditoria

## 📝 Licença

Este projeto é para fins educacionais e de pesquisa. Respeite os termos de uso do site da ANDES.
