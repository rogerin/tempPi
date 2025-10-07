#!/bin/bash
# setup_run.sh - Script para preparar e iniciar o projeto

# Encerra processos anteriores para evitar conflitos de porta
cleanup() {
    echo "Encerrando processos anteriores..."
    PORT_PID=$(lsof -t -i:3333)
    if [ -n "$PORT_PID" ]; then
        echo "Encerrando processo na porta 3333 (PID: $PORT_PID)..."
        kill -9 $PORT_PID
    fi
    sleep 2 # Espera um pouco para a porta ser liberada
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

# Força a reinstalação do numpy e opencv para a arquitetura correta
if [ "$(uname)" == "Darwin" ]; then
    echo "Forçando a reinstalação do numpy e opencv-python para arquitetura Apple Silicon..."
    pip uninstall -y numpy opencv-python
    pip install --no-cache-dir --force-reinstall --upgrade --only-binary=:all: --default-timeout=100 numpy opencv-python
fi

echo "=== Instalando/Atualizando dependências de requirements.txt ==="
pip install --upgrade pip

# Cria um requirements temporário sem RPi.GPIO se não for Linux
if [ "$(uname)" != "Linux" ]; then
    echo "Executando em ambiente não-Linux. Excluindo RPi.GPIO."
    grep -v "RPi.GPIO" requirements.txt > requirements_temp.txt
    pip install -r requirements_temp.txt
    rm requirements_temp.txt
else
    echo "Executando em ambiente Linux. Instalando todas as dependências."
    pip install -r requirements.txt
fi

# Verifica se o modo RPi deve ser ativado
USE_RPI_FLAG=""
if [ "$(uname)" == "Linux" ]; then
    echo "Modo Raspberry Pi ATIVADO."
    USE_RPI_FLAG="--use-rpi"
fi

echo "=== Iniciando Servidor Web (em background) ==="
python3 sensor_server.py &
SERVER_PID=$!
sleep 4 # Dá um tempo maior para o servidor iniciar

echo "=== Iniciando Dashboard (em foreground) ==="
# O dashboard tentará se conectar ao servidor
python3 dashboard.py --img assets/base.jpeg $USE_RPI_FLAG

# Ao fechar o dashboard (Ctrl+C), encerra o servidor também
kill $SERVER_PID
echo "Processos finalizados."