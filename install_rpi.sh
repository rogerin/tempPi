#!/bin/bash
# Script de instalação automática para Raspberry Pi
# Este script tenta instalar as bibliotecas necessárias automaticamente

echo "🚀 Instalador Automático - Dashboard TempPi"
echo "==========================================="
echo ""

# Verificar se estamos em um Raspberry Pi
if ! grep -q "Raspberry Pi\|BCM" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  AVISO: Este script foi feito para Raspberry Pi"
    echo "   Você pode continuar, mas algumas bibliotecas podem não funcionar."
    read -p "   Deseja continuar mesmo assim? (s/N): " continue_anyway
    if [[ ! $continue_anyway =~ ^[Ss]$ ]]; then
        echo "❌ Instalação cancelada."
        exit 1
    fi
fi

echo "📦 Atualizando sistema..."
sudo apt update

echo "🔧 Instalando dependências do sistema..."
sudo apt install -y python3-dev python3-pip python3-venv python3-rpi.gpio

echo "🐍 Verificando ambiente virtual..."
if [ ! -d ".venv" ]; then
    echo "   Criando ambiente virtual..."
    python3 -m venv .venv
fi

echo "   Ativando ambiente virtual..."
source .venv/bin/activate

echo "📚 Instalando dependências básicas..."
pip install --upgrade pip
pip install opencv-python numpy RPi.GPIO flask werkzeug

echo "⚡ Implementação nativa MAX6675 - Não precisa de bibliotecas externas!"
echo "   O sistema agora usa protocolo SPI nativo com RPi.GPIO"

echo ""
echo "🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
echo ""
echo "✅ Próximos passos:"
echo "   1. Ativar o ambiente virtual:"
echo "      source .venv/bin/activate"
echo "   2. Executar o dashboard principal:"
echo "      python dashboard.py --img assets/base.jpeg --use-rpi"
echo "   3. Em outro terminal, executar o servidor web:"
echo "      python sensor_server.py"
echo "   4. Acessar o dashboard web:"
echo "      http://localhost:5000"
echo ""
echo "🌐 NOVA FUNCIONALIDADE: Servidor Web com Gráficos!"
echo "   • Visualização de dados em tempo real"
echo "   • Gráficos interativos"
echo "   • Filtros por sensor e data"
echo "   • Histórico completo no SQLite"

echo "💡 Dica: Execute 'python dashboard.py --help' para ver todas as opções."
