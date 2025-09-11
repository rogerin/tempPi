# Dashboard Overlay (Painel-Apenas) – README

Projeto em Python para simular e/ou ler dados (Raspberry Pi) e sobrepor valores em pontos de uma imagem (ex.: fluxograma da planta). Esta é uma versão simplificada que exibe apenas o painel principal, sem a janela de gráficos.

## 1) Requisitos

- **Python 3.9+** (recomendado 3.10/3.11)
- **Sistema**: macOS, Windows ou Linux (Raspberry Pi opcional)

### Dependências

#### Instalação Básica (Modo Simulação)
```bash
pip install opencv-python numpy
```

#### Instalação Completa (Raspberry Pi)
```bash
# Instalar dependências do sistema
sudo apt update
sudo apt install python3-dev python3-pip python3-venv

# Criar e ativar ambiente virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate

# Instalar todas as dependências
pip install -r requirements.txt

# Ou instalar manualmente:
pip install opencv-python numpy RPi.GPIO MAX6675-RPi
```

#### Resolução de Problemas Comuns

**Se `MAX6675-RPi` não funcionar, tente:**
```bash
pip install max6675
```

**Se houver erro de permissão GPIO:**
```bash
sudo usermod -a -G gpio $USER
# Depois faça logout/login ou reinicie
```

**Instalação sem ambiente virtual:**
```bash
pip install opencv-python numpy
# Para Raspberry Pi adicionar:
pip install RPi.GPIO MAX6675-RPi
```

## 2) Arquivo principal

O projeto é um único arquivo:

- `dashboard.py`

Coloque a sua imagem de fundo (jpg/png) na mesma pasta do projeto.

## 3) Como rodar

### Modo Simulação (padrão)
```bash
python3 dashboard.py --img assets/base.jpeg
```

### Modo Raspberry Pi
```bash
python3 dashboard.py --img assets/base.jpeg --use-rpi
```

### Modo Raspberry Pi com pinos customizados
```bash
python3 dashboard.py --img assets/base.jpeg --use-rpi \
  --thermo-torre1 25 24 18 \
  --thermo-torre2 7 8 23 \
  --thermo-torre3 21 20 16 \
  --thermo-tanque 4 3 2 \
  --thermo-gases 22 27 17 \
  --thermo-forno 11 9 10 \
  --pressao1-pin 2 \
  --pressao2-pin 3 \
  --ventilador-pin 14 \
  --resistencia-pin 26 \
  --motor-rosca-pin 12 \
  --tambor-dir-pin 13 \
  --tambor-pul-pin 19 \
  --scale 1.0
```

**Parâmetros básicos:**
- `--img`: caminho da imagem de fundo (obrigatório).
- `--scale`: escala da janela principal (opcional). Ex.: 0.8, 1.0, 1.2.
- `--use-rpi`: ativa o modo de leitura dos sensores no Raspberry Pi (opcional).

**Parâmetros de configuração GPIO:**

*Sensores de temperatura MAX6675 (3 pinos cada na ordem: SCK, CS, SO):*
- `--thermo-torre1`: Pinos SCK CS SO para sensor Torre Nível 1 (padrão: 25 24 18)
- `--thermo-torre2`: Pinos SCK CS SO para sensor Torre Nível 2 (padrão: 7 8 23)  
- `--thermo-torre3`: Pinos SCK CS SO para sensor Torre Nível 3 (padrão: 21 20 16)
- `--thermo-tanque`: Pinos SCK CS SO para sensor Tanque (padrão: 4 3 2)
- `--thermo-gases`: Pinos SCK CS SO para sensor Saída Gases (padrão: 22 27 17)
- `--thermo-forno`: Pinos SCK CS SO para sensor Forno (padrão: 11 9 10)

  **Nota:** SCK = Serial Clock, CS = Chip Select, SO = Serial Output

*Sensores de pressão:*
- `--pressao1-pin`: Pino para Transdutor de Pressão 1 (padrão: 2)
- `--pressao2-pin`: Pino para Transdutor de Pressão 2 (padrão: 3)

*Controles/Atuadores:*
- `--ventilador-pin`: Pino para controle do Ventilador (padrão: 14)
- `--resistencia-pin`: Pino para controle da Resistência (padrão: 26)
- `--motor-rosca-pin`: Pino para Motor Rosca Alimentação (padrão: 12)
- `--tambor-dir-pin`: Pino para DIR+ Driver Motor Tambor (padrão: 13)
- `--tambor-pul-pin`: Pino para PUL+ Driver Motor Tambor (padrão: 19)

Na janela **Painel**, você verá os valores sobrepostos nos campos da sua imagem.

### Exemplos de uso avançado

**Ver ajuda completa:**
```bash
python3 dashboard.py --help
```

**Customizar apenas alguns pinos específicos:**
```bash
python3 dashboard.py --img assets/base.jpeg --use-rpi \
  --thermo-forno 5 6 7 \
  --thermo-torre1 8 9 10 \
  --ventilador-pin 15 \
  --resistencia-pin 18
```

**Executar com escala diferente:**
```bash
python3 dashboard.py --img assets/base.jpeg --scale 0.8 --use-rpi
```

## 4) Modo Simulação

Por padrão, ou quando a flag `--use-rpi` não está presente, o script é executado em modo de simulação. Neste modo:

- Os valores são gerados aleatoriamente para simular a chegada de dados de sensores.
- As atualizações ocorrem a cada 2 segundos com pequenas variações para parecerem mais realistas.
- Não há controles de teclado para ajustar os valores; a simulação é automática.

## 5) Sistema de Validação de Sensores

### 🔍 Teste Automático de Sensores (Modo Raspberry Pi)

Quando executado com `--use-rpi`, o sistema agora inclui uma **validação robusta** de todos os sensores antes de iniciar:

**Características da validação:**
- ✅ **3 tentativas por sensor** - Cada sensor é testado até 3 vezes para garantir funcionamento
- 📊 **Relatório detalhado** - Mostra status individual de cada sensor
- ⏱️ **Timeout inteligente** - Pausa entre tentativas para estabilização
- 🎯 **Validação de dados** - Verifica se as leituras estão dentro de faixas válidas
- 🚫 **Bloqueio de execução** - O programa só inicia se todos os sensores estiverem funcionando

**Exemplo de saída da validação:**
```
🔍 Iniciando teste detalhado dos sensores de temperatura...
⏱️  Cada sensor será testado 3 vezes para garantir funcionamento correto.

[1/6] ==================================================
📡 Testando sensor 'Torre Nível 1' (Pinos SCK:25, CS:24, SO:18)...
  ✅ Tentativa 1/3: SUCESSO - Temperatura: 23.5°C
✨ Sensor 'Torre Nível 1' APROVADO!

[2/6] ==================================================
📡 Testando sensor 'Torre Nível 2' (Pinos SCK:7, CS:8, SO:23)...
  ❌ Tentativa 1/3: FALHA - No response from sensor
     🔄 Aguardando 1s antes da próxima tentativa...
  ❌ Tentativa 2/3: FALHA - Invalid reading: -999.0°C
     🔄 Aguardando 1s antes da próxima tentativa...
  ❌ Tentativa 3/3: FALHA - Connection timeout
     💥 Sensor 'Torre Nível 2' falhou em todas as tentativas!
💀 Sensor 'Torre Nível 2' REPROVADO!

======================================================================
📊 RELATÓRIO FINAL DE VALIDAÇÃO DOS SENSORES
======================================================================
✅ Sensores funcionando: 5/6
❌ Sensores com falha: 1/6

🎉 SENSORES APROVADOS:
  ✅ Torre Nível 1: 23.5°C (Pinos: (25, 24, 18))
  ✅ Temp Tanque: 25.2°C (Pinos: (4, 3, 2))
  ...

💥 SENSORES REPROVADOS:
  ❌ Torre Nível 2: Sem resposta (Pinos: (7, 8, 23))

⚠️  ATENÇÃO: 1 sensor(es) não está(ão) funcionando!
🔧 Verifique:
   • Conexões físicas dos pinos
   • Alimentação dos sensores (3.3V ou 5V)
   • Soldas dos conectores
   • Termopares conectados corretamente
```

### 🛡️ Proteção Contra Problemas Comuns

O sistema detecta e relata:
- **Conexões soltas** - Sensores que não respondem
- **Leituras inválidas** - Temperaturas fora da faixa (-50°C a 1000°C)
- **Problemas de alimentação** - Falhas na comunicação SPI
- **Configuração incorreta** - Pinos invertidos ou conflitantes

## 6) Troubleshooting Raspberry Pi

### 🔧 Problemas Comuns e Soluções

#### Erro: "No module named 'RPi'"
```bash
# Solução 1: Instalar RPi.GPIO
pip install RPi.GPIO

# Solução 2: Se estiver em ambiente virtual
source .venv/bin/activate
pip install RPi.GPIO

# Solução 3: Instalar via apt (sistema)
sudo apt install python3-rpi.gpio
```

#### Erro: "No module named 'MAX6675'"
```bash
# Solução 1: Biblioteca principal
pip install MAX6675-RPi

# Solução 2: Biblioteca alternativa
pip install max6675

# Solução 3: Instalar dependências do sistema primeiro
sudo apt install python3-dev python3-pip
pip install MAX6675-RPi
```

#### Erro: "Permission denied" nos GPIOs
```bash
# Adicionar usuário ao grupo gpio
sudo usermod -a -G gpio $USER

# Ou executar com sudo (não recomendado)
sudo python3 dashboard.py --img assets/base.jpeg --use-rpi
```

#### Sensores não respondem
1. **Verificar conexões físicas:**
   - VCC → 3.3V ou 5V
   - GND → Ground
   - SCK, CS, SO → Pinos GPIO corretos

2. **Verificar pinos no código:**
   ```bash
   # Ver ajuda com todos os pinos
   python3 dashboard.py --help
   
   # Testar com pinos diferentes
   python3 dashboard.py --img assets/base.jpeg --use-rpi \
     --thermo-forno 11 9 10
   ```

3. **Verificar termopar:**
   - Termopar tipo K conectado nos pinos T+ e T-
   - Polaridade correta

## 7) Controles

- **ESC** ou **Ctrl+C**: fecha o programa.

## 8) Posicionamento dos valores na imagem

As posições dos 8 campos são proporcionais à imagem (0.0–1.0) e podem ser ajustadas no dicionário `POSITIONS_NORM` dentro do arquivo `dashboard.py`.

Para encontrar as coordenadas, mova o cursor sobre a imagem; no canto superior esquerdo aparecem as coordenadas normalizadas (x, y) que você pode usar.
