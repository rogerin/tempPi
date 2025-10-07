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

## 2) Como Rodar (Método Simplificado)

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
- **Painel de Controle Web**: [http://localhost:8080/control](http://localhost:8080/control)
- **Visualização Web**: [http://localhost:8080](http://localhost:8080)

Para encerrar tudo, basta fechar a janela do dashboard ou pressionar `Ctrl+C` no terminal.

## 3) Execução Manual (para Desenvolvimento)

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

## 4) Funcionalidades do Painel de Controle Web

O painel de controle (`http://localhost:8080/control`) permite:

- **Alternar entre modo Automático e Manual.**
- **Ajustar setpoints** de temperatura para o controle automático.
- **Configurar timers** para os atuadores.
- **Acionar atuadores individualmente** no modo manual.

## 5) Argumentos de Linha de Comando

O script `dashboard.py` aceita vários argumentos para customização:

- `--img`: Caminho da imagem de fundo (obrigatório).
- `--scale`: Escala da janela (ex: `0.8`).
- `--use-rpi`: Ativa o modo de leitura dos sensores no Raspberry Pi.
- `--thermo-torre1`, `--ventilador-pin`, etc: Permitem customizar todos os pinos GPIO utilizados. Use `python3 dashboard.py --help` para ver todas as opções.