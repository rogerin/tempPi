#!/bin/bash
# setup_run.sh - Script para preparar e iniciar o projeto

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Criar diretório de logs
mkdir -p logs

# Encerra processos anteriores
cleanup() {
    echo -e "${YELLOW}Encerrando processos...${NC}"
    
    # Encerra servidor se PID existe
    if [ -n "$SERVER_PID" ] && kill -0 $SERVER_PID 2>/dev/null; then
        echo "Encerrando servidor (PID: $SERVER_PID)..."
        kill -TERM $SERVER_PID 2>/dev/null
        sleep 2
        kill -9 $SERVER_PID 2>/dev/null
    fi
    
    # Encerra processos na porta 3333
    PORT_PID=$(lsof -t -i:3333 2>/dev/null)
    if [ -n "$PORT_PID" ]; then
        echo "Encerrando processo na porta 3333 (PID: $PORT_PID)..."
        kill -9 $PORT_PID 2>/dev/null
    fi
    
    pkill -f sensor_server.py 2>/dev/null
    pkill -f dashboard.py 2>/dev/null
    
    echo -e "${GREEN}Processos finalizados.${NC}"
    exit
}

trap cleanup INT TERM

# Caminho base do projeto
PROJ_DIR=$(dirname "$0")
cd "$PROJ_DIR" || { echo -e "${RED}Erro ao acessar diretório do projeto${NC}"; exit 1; }

# Flag para forçar reinstalação
FORCE_INSTALL=false
if [ "$1" == "--force-install" ]; then
    FORCE_INSTALL=true
fi

# Função para verificar conexão com internet
check_internet() {
    if ping -c 1 8.8.8.8 >/dev/null 2>&1 || ping -c 1 1.1.1.1 >/dev/null 2>&1; then
        return 0  # Tem internet
    else
        return 1  # Sem internet
    fi
}

# Função para verificar dependências instaladas
check_dependencies() {
    echo "Verificando dependências instaladas..."
    
    # Pacotes essenciais
    REQUIRED_PACKAGES=("flask" "flask-socketio" "numpy" "opencv-python" "python-socketio")
    MISSING_PACKAGES=()
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! pip show "$package" >/dev/null 2>&1; then
            MISSING_PACKAGES+=("$package")
        fi
    done
    
    if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
        echo "✓ Todas as dependências já estão instaladas"
        return 0
    else
        echo "✗ Pacotes faltando: ${MISSING_PACKAGES[*]}"
        return 1
    fi
}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    TempPi Dashboard - Setup & Run     ${NC}"
echo -e "${BLUE}========================================${NC}"

# Mostrar opções disponíveis
if [ "$FORCE_INSTALL" = true ]; then
    echo -e "${YELLOW}🔧 Modo: Forçar reinstalação de dependências${NC}"
else
    echo -e "${GREEN}🚀 Modo: Verificação inteligente de dependências${NC}"
    echo -e "${BLUE}💡 Use './setup_run.sh --force-install' para forçar reinstalação${NC}"
fi

echo -e "${GREEN}=== Verificando ambiente virtual (.venv) ===${NC}"
if [ ! -d ".venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Reinstalação para macOS
if [ "$(uname)" == "Darwin" ]; then
    echo -e "${YELLOW}Forçando reinstalação numpy/opencv para Apple Silicon...${NC}"
    pip uninstall -y numpy opencv-python 2>/dev/null
    pip install --no-cache-dir --force-reinstall --upgrade --only-binary=:all: numpy opencv-python
fi

echo -e "${GREEN}=== Verificando dependências ===${NC}"

if [ "$FORCE_INSTALL" = true ]; then
    echo -e "${YELLOW}Flag --force-install detectada. Forçando reinstalação...${NC}"
    pip install --upgrade pip -q
    
    if [ "$(uname)" != "Linux" ]; then
        echo -e "${YELLOW}Ambiente não-Linux detectado. RPi.GPIO e bibliotecas Adafruit serão ignorados.${NC}"
        grep -v "RPi.GPIO" requirements.txt | grep -v "adafruit-" > requirements_temp.txt
        pip install -r requirements_temp.txt -q
        rm requirements_temp.txt
    else
        echo -e "${GREEN}Ambiente Linux detectado.${NC}"
        pip install -r requirements.txt -q
    fi
elif check_dependencies; then
    echo -e "${GREEN}✓ Dependências OK. Pulando instalação.${NC}"
else
    if check_internet; then
        echo -e "${YELLOW}Instalando dependências faltantes...${NC}"
        pip install --upgrade pip -q
        
        if [ "$(uname)" != "Linux" ]; then
            echo -e "${YELLOW}Ambiente não-Linux detectado. RPi.GPIO e bibliotecas Adafruit serão ignorados.${NC}"
            grep -v "RPi.GPIO" requirements.txt | grep -v "adafruit-" > requirements_temp.txt
            pip install -r requirements_temp.txt -q
            rm requirements_temp.txt
        else
            echo -e "${GREEN}Ambiente Linux detectado.${NC}"
            pip install -r requirements.txt -q
        fi
    else
        echo -e "${RED}⚠️  AVISO: Sem conexão com internet e dependências faltando!${NC}"
        echo -e "${YELLOW}Tentando continuar com pacotes disponíveis...${NC}"
        echo -e "${BLUE}💡 Dica: Execute './setup_run.sh --force-install' quando tiver internet${NC}"
    fi
fi

# Flag RPi
USE_RPI_FLAG=""
if [ "$(uname)" == "Linux" ]; then
    echo -e "${GREEN}Modo Raspberry Pi ATIVADO.${NC}"
    USE_RPI_FLAG="--use-rpi"
fi

echo -e "${GREEN}=== Iniciando Servidor Web ===${NC}"
nohup python3 sensor_server.py > logs/server.log 2>&1 &
SERVER_PID=$!
disown

# Verifica se servidor iniciou
echo "Aguardando servidor inicializar..."
for i in {1..10}; do
    sleep 1
    if curl -s http://localhost:3333/ > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Servidor iniciado com sucesso (PID: $SERVER_PID)${NC}"
        break
    fi
    if [ $i -eq 10 ]; then
        echo -e "${RED}✗ Falha ao iniciar servidor. Verifique logs/server.log${NC}"
        echo -e "${RED}Últimas linhas do log:${NC}"
        tail -10 logs/server.log
        kill $SERVER_PID 2>/dev/null
        exit 1
    fi
done

echo -e "${GREEN}=== Servidor disponível em http://localhost:3333 ===${NC}"

# Abrir navegador automaticamente em modo fullscreen (em background para não bloquear)
echo -e "${BLUE}🌐 Abrindo navegador em modo fullscreen na página de controle...${NC}"
echo -e "${YELLOW}⏳ Aguardando 5 segundos para garantir inicialização completa...${NC}"
(
    sleep 5  # Aguardar 5 segundos para garantir que servidor está completamente pronto
    if [ "$(uname)" == "Darwin" ]; then
        # macOS - tentar Chrome em modo app primeiro
        if [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --app=http://localhost:3333/control 2>/dev/null &
        else
            open http://localhost:3333/control 2>/dev/null
        fi
    elif [ "$(uname)" == "Linux" ]; then
        # Linux - priorizar modo kiosk
        chromium-browser --kiosk --app=http://localhost:3333/control 2>/dev/null || \
        google-chrome --kiosk --app=http://localhost:3333/control 2>/dev/null || \
        firefox --kiosk http://localhost:3333/control 2>/dev/null || \
        xdg-open http://localhost:3333/control 2>/dev/null
    fi
) &

echo -e "${YELLOW}=== Iniciando Dashboard ===${NC}"
echo -e "${BLUE}Pressione Ctrl+C para parar ambos os processos${NC}"
python3 dashboard.py --img assets/base.jpeg $USE_RPI_FLAG 2>&1 | tee logs/dashboard.log

# Cleanup ao sair
cleanup