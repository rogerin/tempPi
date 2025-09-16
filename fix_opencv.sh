#!/bin/bash
# Script para corrigir problemas do OpenCV no Raspberry Pi

echo "🔧 Correção Rápida - OpenCV para Raspberry Pi"
echo "============================================"
echo ""

# Verificar se estamos em ambiente virtual
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  AVISO: Recomenda-se usar ambiente virtual"
    echo "   Para criar e ativar:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo ""
    read -p "   Continuar mesmo assim? (s/N): " continue_anyway
    if [[ ! $continue_anyway =~ ^[Ss]$ ]]; then
        echo "❌ Instalação cancelada."
        echo "💡 Execute: source .venv/bin/activate"
        exit 1
    fi
fi

echo "📦 Atualizando sistema..."
sudo apt update

echo "🎥 Instalando OpenCV do sistema..."
sudo apt install -y python3-opencv libopencv-dev

echo "📊 Instalando NumPy..."
pip install numpy

echo "🔗 Criando link simbólico do OpenCV..."
# Encontrar a instalação do OpenCV do sistema
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
OPENCV_PATH="/usr/lib/python3/dist-packages/cv2"

if [ -d "$OPENCV_PATH" ]; then
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        VENV_SITE_PACKAGES="$VIRTUAL_ENV/lib/python$PYTHON_VERSION/site-packages"
        echo "   Linkando $OPENCV_PATH para $VENV_SITE_PACKAGES/"
        ln -sf $OPENCV_PATH "$VENV_SITE_PACKAGES/"
        echo "✅ Link criado com sucesso!"
    else
        echo "✅ OpenCV do sistema instalado!"
    fi
else
    echo "⚠️  OpenCV não encontrado no sistema, tentando pip..."
    pip install opencv-python
fi

echo ""
echo "🧪 Testando instalação..."
python3 -c "import cv2; print(f'✅ OpenCV {cv2.__version__} funcionando!')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "🎉 OpenCV instalado com sucesso!"
else
    echo "❌ Ainda há problemas com OpenCV"
    echo ""
    echo "🔧 Soluções alternativas:"
    echo "1. Tentar instalar opencv-python-headless:"
    echo "   pip install opencv-python-headless"
    echo ""
    echo "2. Usar apenas funcionalidades sem OpenCV:"
    echo "   python3 dashboard.py --use-rpi (sem --img)"
fi

echo ""
echo "✅ Agora tente executar:"
echo "   python3 dashboard.py --img assets/base.jpeg --use-rpi"

