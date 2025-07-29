#!/bin/bash
# Script de inicialização para o Render
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port $PORT
