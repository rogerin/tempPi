# Projeto Dashboard IoT com Controle Remoto

Este projeto implementa um sistema de monitoramento e controle para um processo de destilação (ou similar), consistindo em um dashboard visual com sobreposição de dados em uma imagem e um painel de controle web completo para operação remota.

## Arquitetura

O sistema é dividido em dois componentes principais que se comunicam em tempo real via **WebSockets**:

1.  **`sensor_server.py`**: Um servidor web (Flask) que atua como um hub WebSocket. Ele serve a interface do usuário para o navegador e gerencia a comunicação entre o painel de controle web e o script do dashboard.

2.  **`dashboard.py`**: O cliente pesado que executa no Raspberry Pi (ou em modo de simulação). Ele é responsável por:
    - Ler os dados dos sensores (temperatura, pressão, etc.).
    - Exibir os dados em um dashboard visual (OpenCV).
    - Executar a lógica de controle (automático e manual).
    - Comunicar-se com o `sensor_server.py` para receber comandos e enviar atualizações.

## 1) Requisitos

- **Python 3.9+**
- **Sistema**: Linux (Raspberry Pi) ou qualquer sistema para modo de simulação.

## 2) Instalação Automática (Raspberry Pi)

Para Raspberry Pi, use o script de instalação automática que configura tudo:

```bash
chmod +x install_rpi.sh
./install_rpi.sh
```

O script irá:
- Instalar dependências do sistema (incluindo i2c-tools)
- Configurar ambiente virtual Python
- Instalar todas as bibliotecas necessárias
- Instalar bibliotecas para sensor de pressão (ADS1115)
- Verificar configuração do I2C

**Nota:** Após a instalação, certifique-se de que o I2C está habilitado:
```bash
sudo raspi-config
# Navegue até: Interface Options -> I2C -> Enable
```

## 3) Como Rodar (Método Simplificado)

Para facilitar a inicialização, use o script `setup_run.sh`. Ele cuida de tudo: prepara o ambiente, instala as dependências e inicia os dois componentes na ordem correta.

**Passo a passo:**

1.  **Dê permissão de execução ao script:**
    ```bash
    chmod +x setup_run.sh
    ```

2.  **Execute o script:**
    ```bash
    ./setup_run.sh
    ```

O script irá:
- Criar e ativar um ambiente virtual (`.venv`).
- Instalar todas as dependências do `requirements.txt`.
- Iniciar o `sensor_server.py` em background.
- Iniciar o `dashboard.py` em modo Raspberry Pi (`--use-rpi`).

### Acesso

- **Dashboard Visual**: Uma janela do OpenCV irá abrir mostrando a imagem com os dados dos sensores.
- **Painel de Controle Web**: [http://localhost:3333/control](http://localhost:3333/control)
- **Visualização Web**: [http://localhost:3333](http://localhost:3333)

Para encerrar tudo, basta fechar a janela do dashboard ou pressionar `Ctrl+C` no terminal.

## 4) Execução Manual (para Desenvolvimento)

Se preferir iniciar os componentes separadamente:

**1. Instale as dependências:**
```bash
# Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instale os pacotes
pip install -r requirements.txt
```

**2. Inicie o Servidor Web (Terminal 1):**
```bash
python3 sensor_server.py
```

**3. Inicie o Dashboard (Terminal 2):**
```bash
# Para modo Raspberry Pi
python3 dashboard.py --img assets/base.jpeg --use-rpi

# Ou para modo de simulação
python3 dashboard.py --img assets/base.jpeg
```

## 5) Funcionalidades do Painel de Controle Web

O painel de controle (`http://localhost:3333/control`) permite:

- **Alternar entre modo Automático e Manual.**
- **Ajustar setpoints** de temperatura para o controle automático.
- **Configurar timers** para os atuadores.
- **Acionar atuadores individualmente** no modo manual.

## 6) Argumentos de Linha de Comando

O script `dashboard.py` aceita vários argumentos para customização:

- `--img`: Caminho da imagem de fundo (obrigatório).
- `--scale`: Escala da janela (ex: `0.8`).
- `--use-rpi`: Ativa o modo de leitura dos sensores no Raspberry Pi.
- `--thermo-torre1`, `--ventilador-pin`, etc: Permitem customizar todos os pinos GPIO utilizados. Use `python3 dashboard.py --help` para ver todas as opções.

## 7) Scripts de Teste

O projeto inclui scripts de teste para validar o hardware antes da execução completa:

### Teste do Motor de Passo (Tambor Rotativo)

```bash
# Teste básico com 200 passos
python3 test_motor.py --steps 200 --direction forward

# Teste com velocidade customizada
python3 test_motor.py --steps 400 --direction reverse --speed 1000

# Modo interativo
python3 test_motor.py --interactive

# Sequência automática de testes
python3 test_motor.py --sequence
```

**Opções:**
- `--steps`: Número de passos (padrão: 200)
- `--direction`: Direção - `forward` (horário) ou `reverse` (anti-horário)
- `--speed`: Velocidade em Hz - pulsos por segundo (padrão: 500)
- `--interactive`: Modo interativo para controle manual
- `--sequence`: Executa sequência de testes automática

### Teste do Sensor de Pressão (ADS1115)

```bash
# Teste completo do sensor de pressão
python3 test_ads1115.py
```

Este script irá:
- Detectar dispositivos I2C conectados
- Testar leitura do sensor no canal A0
- Fazer 5 leituras e calcular a média
- Validar se os valores estão no range esperado (0-30 PSI)

### Comandos de Diagnóstico I2C

```bash
# Listar dispositivos I2C conectados
sudo i2cdetect -y 1

# Informações sobre o barramento I2C
i2cdetect -l
```

**Endereços I2C esperados:**
- `0x48`: ADS1115 (conversor ADC para sensor de pressão)

## 8) Pinagem e Conexões

### Sensores de Temperatura (MAX6675 - SPI)

Cada sensor MAX6675 usa 3 pinos GPIO:

| Sensor | SCK | CS | SO |
|--------|-----|----|----|
| Torre Nível 1 | GPIO 25 | GPIO 24 | GPIO 18 |
| Torre Nível 2 | GPIO 7 | GPIO 8 | GPIO 23 |
| Torre Nível 3 | GPIO 21 | GPIO 20 | GPIO 16 |
| Tanque | GPIO 4 | GPIO 6 | GPIO 5 |
| Saída Gases | GPIO 22 | GPIO 27 | GPIO 17 |
| Forno | GPIO 11 | GPIO 9 | GPIO 10 |

### Sensor de Pressão (ADS1115 - I2C)

| Pino | GPIO | Função |
|------|------|--------|
| SDA | GPIO 2 | Dados I2C |
| SCL | GPIO 3 | Clock I2C |

**Conexão do sensor:**
- Sensor de pressão conectado no canal A0 do ADS1115
- Sensor: 0-30 PSI, saída 0.5-4.5V
- Level shifter 5V→3.3V entre sensor e ADS1115

### Atuadores

| Atuador | GPIO | Tipo |
|---------|------|------|
| Ventilador | GPIO 14 | Relé |
| Resistência | GPIO 26 | Relé |
| Motor Rosca | GPIO 12 | Relé |
| Tambor DIR | GPIO 13 | Driver motor |
| Tambor PUL | GPIO 19 | Driver motor |

**Nota:** Relés usam lógica invertida (HIGH=desligado, LOW=ligado)

## 9) Solução de Problemas

### Sensor de Pressão não detectado

1. Verifique se o I2C está habilitado:
```bash
sudo raspi-config
# Interface Options -> I2C -> Enable
```

2. Liste dispositivos I2C:
```bash
sudo i2cdetect -y 1
```

3. Execute o teste do sensor:
```bash
python3 test_ads1115.py
```

### Motor de Passo não funciona

1. Execute o teste do motor:
```bash
python3 test_motor.py --steps 10 --direction forward
```

2. Verifique se os pinos DIR (GPIO 13) e PUL (GPIO 19) estão corretamente conectados ao driver.

3. Certifique-se de que ENA+ e ENA- do driver estão conectados ao GND (motor sempre habilitado).

### Sensores de temperatura com erro

1. Verifique as conexões SPI de cada sensor (SCK, CS, SO).

2. Execute o dashboard com `--use-rpi` para ver o log de validação dos sensores.

3. O sistema mostrará quais sensores falharam durante a inicialização.