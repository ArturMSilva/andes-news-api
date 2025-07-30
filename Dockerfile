# Use uma imagem oficial com Python 3.11
FROM python:3.11-slim

# Define diretório de trabalho dentro do container
WORKDIR /app

# Copia arquivos do projeto
COPY . .

# Instala dependências
RUN pip install --upgrade pip && pip install -r requirements.txt

# Expõe a porta que o Render vai acessar
EXPOSE 10000

# Comando de inicialização
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
