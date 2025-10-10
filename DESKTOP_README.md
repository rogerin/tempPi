# 🖥️ Atalho Desktop - TempPi Dashboard

## 📋 O que foi criado

### Arquivos Criados:
- `start_temppi.sh` - Script principal de inicialização
- `TempPi.desktop` - Atalho para GNOME/Ubuntu
- `TempPi-raspberry.desktop` - Atalho para Raspberry Pi OS
- `install_desktop.sh` - Script de instalação automática

## 🚀 Como usar

### Opção 1: Instalação Automática
```bash
cd /home/admin/Documentos/tempPi
./install_desktop.sh
```

### Opção 2: Instalação Manual

#### Para Ubuntu/GNOME:
```bash
cp TempPi.desktop ~/Desktop/
chmod +x ~/Desktop/TempPi.desktop
```

#### Para Raspberry Pi OS:
```bash
cp TempPi-raspberry.desktop ~/Desktop/TempPi.desktop
chmod +x ~/Desktop/TempPi.desktop
```

## 🎯 Como funciona

1. **Clique no ícone** "TempPi Dashboard" no desktop
2. **Terminal abre** automaticamente
3. **Script executa** `./setup_run.sh`
4. **Aguarda** servidor iniciar na porta 3333
5. **Navegador abre** automaticamente em `http://localhost:3333`
6. **Terminal fica aberto** para ver logs

## 🔧 Solução de Problemas

### Se o atalho não funcionar:
```bash
# Verificar permissões
ls -la ~/Desktop/TempPi.desktop

# Dar permissão novamente
chmod +x ~/Desktop/TempPi.desktop

# Tornar confiável (Ubuntu)
gio set ~/Desktop/TempPi.desktop metadata::trusted true
```

### Se o terminal não abrir:
- Verifique se `gnome-terminal`, `lxterminal` ou `xfce4-terminal` está instalado
- Edite o arquivo `.desktop` e altere a linha `Exec=`

### Se o navegador não abrir:
- O script tenta: `xdg-open`, `firefox`, `chromium-browser`, `google-chrome`
- Verifique se algum desses está instalado

## 📁 Estrutura dos Arquivos

```
tempPi/
├── start_temppi.sh              # Script principal
├── TempPi.desktop              # Atalho GNOME/Ubuntu
├── TempPi-raspberry.desktop    # Atalho Raspberry Pi
├── install_desktop.sh          # Instalador automático
└── DESKTOP_README.md           # Este arquivo
```

## 🎨 Personalização

### Alterar ícone:
1. Substitua `static/images/keycore-logo.png`
2. Ou edite a linha `Icon=` no arquivo `.desktop`

### Alterar terminal:
Edite a linha `Exec=` no arquivo `.desktop`:
- GNOME: `gnome-terminal -- bash -c "..."`
- XFCE: `xfce4-terminal -e "..."`
- LXDE: `lxterminal -e "..."`
- KDE: `konsole -e "..."`

## ✅ Teste

```bash
# Testar script manualmente
./start_temppi.sh

# Verificar atalho
desktop-file-validate ~/Desktop/TempPi.desktop
```

## 🆘 Suporte

Se algo não funcionar:
1. Verifique os logs no terminal
2. Teste o script manualmente: `./start_temppi.sh`
3. Verifique se o `setup_run.sh` funciona: `./setup_run.sh`
4. Verifique se a porta 3333 está livre: `lsof -i:3333`
