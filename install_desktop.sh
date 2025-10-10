#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Instalando atalho TempPi no desktop...${NC}"

# Detectar ambiente de desktop
if command -v gnome-terminal &> /dev/null; then
    DESKTOP_FILE="TempPi.desktop"
    echo -e "${GREEN}✅ Detectado GNOME - usando gnome-terminal${NC}"
elif command -v lxterminal &> /dev/null; then
    DESKTOP_FILE="TempPi-raspberry.desktop"
    echo -e "${GREEN}✅ Detectado LXDE - usando lxterminal${NC}"
elif command -v xfce4-terminal &> /dev/null; then
    DESKTOP_FILE="TempPi.desktop"
    # Modificar para usar xfce4-terminal
    sed 's/gnome-terminal/xfce4-terminal/g' TempPi.desktop > TempPi-xfce.desktop
    DESKTOP_FILE="TempPi-xfce.desktop"
    echo -e "${GREEN}✅ Detectado XFCE - usando xfce4-terminal${NC}"
else
    echo -e "${YELLOW}⚠️  Terminal não detectado - usando configuração padrão${NC}"
    DESKTOP_FILE="TempPi.desktop"
fi

# Copiar arquivo .desktop para o desktop
cp "$DESKTOP_FILE" ~/Desktop/TempPi.desktop
chmod +x ~/Desktop/TempPi.desktop

echo -e "${GREEN}✅ Atalho criado em ~/Desktop/TempPi.desktop${NC}"

# Tentar tornar confiável (Ubuntu/GNOME)
if command -v gio &> /dev/null; then
    gio set ~/Desktop/TempPi.desktop metadata::trusted true 2>/dev/null || true
fi

# Opcional: Adicionar ao menu de aplicações
read -p "Deseja adicionar ao menu de aplicações? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    mkdir -p ~/.local/share/applications/
    cp ~/Desktop/TempPi.desktop ~/.local/share/applications/
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database ~/.local/share/applications/
    fi
    echo -e "${GREEN}✅ Adicionado ao menu de aplicações${NC}"
fi

echo -e "${GREEN}🎉 Instalação concluída!${NC}"
echo -e "${BLUE}💡 Agora você pode clicar no ícone 'TempPi Dashboard' no desktop${NC}"
