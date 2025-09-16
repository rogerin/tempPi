#!/bin/bash
# setup_run.sh - Script para preparar e iniciar o projeto no Raspberry Pi

# Caminho base do projeto
PROJ_DIR="/home/admin/Documentos/tempPi"

cd "$PROJ_DIR" || { echo "Diretório $PROJ_DIR não encontrado"; exit 1; }

echo "=== Criando ambiente virtual (.venv) ==="
python3 -m venv .venv

echo "=== Ativando ambiente virtual ==="
source .venv/bin/activate

echo "=== Atualizando pip ==="
pip install --upgrade pip

echo "=== Instalando dependências ==="
pip install opencv-python numpy RPi.GPIO flask

echo "=== Rodando dashboard.py ==="
python3 dashboard.py --img assets/base.jpeg --use-rpi &

# espera alguns segundos para garantir que o dashboard está inicializado
sleep 5

echo "=== Rodando sensor_server.py ==="
python3 sensor_server.py