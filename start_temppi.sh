#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="/home/admin/Documentos/tempPi"

echo -e "${BLUE}🚀 Iniciando TempPi Dashboard...${NC}"

# Navegar para o diretório
cd "$PROJECT_DIR" || exit 1

# Executar setup_run.sh em segundo plano
./setup_run.sh &
SETUP_PID=$!

echo -e "${BLUE}⏳ Aguardando servidor iniciar na porta 3333...${NC}"

# Aguardar servidor iniciar (máximo 30 segundos)
for i in {1..30}; do
    if lsof -i:3333 -t >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Servidor iniciado!${NC}"
        sleep 2
        
        # Abrir navegador
        echo -e "${BLUE}🌐 Abrindo navegador...${NC}"
        xdg-open http://localhost:3333 2>/dev/null || \
        firefox http://localhost:3333 2>/dev/null || \
        chromium-browser http://localhost:3333 2>/dev/null || \
        google-chrome http://localhost:3333 2>/dev/null
        
        echo -e "${GREEN}✅ TempPi Dashboard iniciado!${NC}"
        echo -e "${BLUE}💡 Pressione Ctrl+C para encerrar${NC}"
        
        # Aguardar processo terminar
        wait $SETUP_PID
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo -e "\n${RED}❌ Timeout: Servidor não iniciou em 30 segundos${NC}"
exit 1
