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
pip install opencv-python numpy RPi.GPIO

echo "🌡️  Tentando instalar bibliotecas MAX6675..."

# Lista de bibliotecas para tentar
libraries=("MAX6675-RPi" "max6675" "MAX6675")
installed=false

for lib in "${libraries[@]}"; do
    echo "   Tentando instalar $lib..."
    if pip install "$lib" 2>/dev/null; then
        echo "   ✅ $lib instalado com sucesso!"
        installed=true
        break
    else
        echo "   ❌ Falha ao instalar $lib"
    fi
done

if [ "$installed" = true ]; then
    echo ""
    echo "🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!"
    echo ""
    echo "✅ Próximos passos:"
    echo "   1. Ativar o ambiente virtual:"
    echo "      source .venv/bin/activate"
    echo "   2. Executar o programa:"
    echo "      python dashboard.py --img assets/base.jpeg --use-rpi"
    echo ""
else
    echo ""
    echo "⚠️  INSTALAÇÃO PARCIALMENTE CONCLUÍDA"
    echo ""
    echo "❌ Nenhuma biblioteca MAX6675 foi instalada automaticamente."
    echo "🔧 Tente instalar manualmente:"
    echo "   source .venv/bin/activate"
    echo "   pip install MAX6675-RPi"
    echo "   # OU"
    echo "   pip install max6675"
    echo ""
    echo "📱 O programa ainda funcionará em modo simulação:"
    echo "   python dashboard.py --img assets/base.jpeg"
fi

echo "💡 Dica: Execute 'python dashboard.py --help' para ver todas as opções."
