# Instruções para Autostart no Raspberry Pi

## Problema Resolvido
O encerramento prematuro do servidor foi causado pelo bash wrapper do autostart que encerrava antes dos processos filhos estarem prontos.

## Solução Implementada
1. **setup_run.sh**: Adicionado `nohup` e `disown` para desacoplar o servidor do shell pai
2. **Arquivo .desktop**: Deve usar `exec` e remover redirecionamento externo

## Configuração do Autostart

### 1. Criar o arquivo .desktop
No Raspberry Pi, crie o arquivo:
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/temppi.desktop
```

### 2. Conteúdo do arquivo .desktop
```ini
[Desktop Entry]
Type=Application
Name=TempPi Dashboard
Exec=/bin/bash -c "cd /home/admin/Documentos/tempPi && exec ./setup_run.sh"
Terminal=false
X-GNOME-Autostart-enabled=true
```

### 3. Tornar executável
```bash
chmod +x ~/.config/autostart/temppi.desktop
```

## Diferenças da versão anterior
- **Antes**: `Exec=bash -c "sleep 15 && /home/admin/Documentos/tempPi/setup_run.sh > /home/admin/Documentos/log_inicio.txt 2>&1"`
- **Depois**: `Exec=/bin/bash -c "cd /home/admin/Documentos/tempPi && exec ./setup_run.sh"`

### Por que funciona agora:
1. **Remove redirecionamento externo**: `> log.txt` causava encerramento prematuro do bash wrapper
2. **Usa `exec`**: Substitui o bash pelo script, não cria processo intermediário
3. **`nohup` + `disown`**: Servidor sobrevive ao encerramento do wrapper
4. **Logs internos**: O script já salva logs em `logs/server.log` e `logs/dashboard.log`

## Verificação
Após reiniciar o Raspberry Pi:
1. Verificar se processos estão rodando:
   ```bash
   ps aux | grep -E "(sensor_server|dashboard)"
   ```
2. Verificar se servidor responde:
   ```bash
   curl http://localhost:3333
   ```
3. Verificar logs:
   ```bash
   tail -f /home/admin/Documentos/tempPi/logs/server.log
   tail -f /home/admin/Documentos/tempPi/logs/dashboard.log
   ```

## Troubleshooting
Se ainda houver problemas:
1. Verificar permissões do script:
   ```bash
   chmod +x /home/admin/Documentos/tempPi/setup_run.sh
   ```
2. Testar manualmente:
   ```bash
   cd /home/admin/Documentos/tempPi
   ./setup_run.sh
   ```
3. Verificar se ambiente virtual está ativo no autostart (pode precisar ajustar PATH)
