#!/bin/bash
# setup_run.sh - Script para preparar e iniciar o projeto

# Encerra processos anteriores para evitar conflitos de porta
cleanup() {
    echo "Encerrando processos anteriores..."
    pkill -f sensor_server.py
    pkill -f dashboard.py
    exit
}

trap cleanup INT

# Caminho base do projeto (detecta o diretório do script)
PROJ_DIR=$(dirname "$0")
cd "$PROJ_DIR" || { echo "Erro ao acessar o diretório do projeto"; exit 1; }

echo "=== Verificando e ativando ambiente virtual (.venv) ==="
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "=== Instalando/Atualizando dependências de requirements.txt ==="
pip install --upgrade pip
pip install -r requirements.txt

# Pergunta ao usuário se deseja usar o modo RPi
USE_RPI_FLAG=""
read -p "Deseja executar em modo Raspberry Pi (GPIO)? (s/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]
then
    USE_RPI_FLAG="--use-rpi"
    echo "Modo Raspberry Pi ATIVADO."
else
    echo "Modo de Simulação ATIVADO."
fi

echo "=== Iniciando Servidor Web (em background) ==="
python3 sensor_server.py &
SERVER_PID=$!
sleep 2 # Dá um tempo para o servidor iniciar

echo "=== Iniciando Dashboard (em foreground) ==="
# O dashboard tentará se conectar ao servidor
python3 dashboard.py --img assets/base.jpeg $USE_RPI_FLAG

# Ao fechar o dashboard (Ctrl+C), encerra o servidor também
kill $SERVER_PID
echo "Processos finalizados."
