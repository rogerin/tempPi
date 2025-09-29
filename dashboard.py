# dashboard_overlay.py

import cv2, numpy as np, random, argparse, time, math, warnings, signal, sqlite3, os
from datetime import datetime
import socketio
import json

# ============= 1) ARGUMENTOS DE LINHA DE COMANDO =============
# ... (argumentos permanecem os mesmos)

# ============= 2) CONFIGURAÇÕES GLOBAIS =============
# ... (pinagens e UI permanecem os mesmos) ...

# Estado global do sistema
state = {
    'settings': {},
    'values': {},
    'actuators': {
        'ventilador': False, 'resistencia': False, 'motor_rosca': False,
        'tambor_dir': False, 'tambor_pul': False
    },
    'timers': {'resistencia_start_time': None, 'rosca_cycle_start': None}
}

# ============= 3) CLIENTE WEBSOCKET =============
sio = socketio.Client()

@sio.event(namespace='/dashboard')
def connect():
    print("Conectado ao servidor WebSocket.")
    sio.emit('request_full_update', namespace='/dashboard')

@sio.event(namespace='/dashboard')
def disconnect():
    print("Desconectado do servidor WebSocket.")

@sio.on('command_from_server', namespace='/dashboard')
def handle_command(data):
    global state
    print(f"Comando recebido: {data}")
    command = data.get('command')
    payload = data.get('payload')

    if command == 'SET_SETTING':
        state['settings'][payload['name']] = payload['value']
        # Opcional: salvar no banco de dados para persistência

    elif command == 'MANUAL_CONTROL':
        if state['settings'].get('system_mode', 0) == 1: # Modo Manual
            target = payload.get('target')
            if target in state['actuators']:
                state['actuators'][target] = bool(payload.get('state'))

@sio.on('request_full_update', namespace='/dashboard')
def send_full_update():
    """Envia o estado completo para o servidor."""
    sio.emit('dashboard_update', state, namespace='/dashboard')

# ============= 4) LÓGICA DE CONTROLE E SIMULAÇÃO =============

def handle_automatic_mode():
    """Gerencia a lógica de controle no modo automático."""
    global state
    # ... (lógica do modo automático como antes, mas usando o dict `state`)

def compute_values():
    """Computa valores dos sensores."""
    global state
    # ... (lógica de leitura de sensores como antes, atualizando `state['values']`)

def apply_actuator_state():
    """Aplica o estado dos atuadores aos GPIOs ou simulação."""
    if USE_RPI and _rpi_ready:
        # ... (lógica GPIO como antes, lendo de `state['actuators']`)
        pass
    else:
        print(f"SIMUL: {state['actuators']}")

# ============= 10) MAIN LOOP =============
def main():
    global state
    # ... (inicialização de CV2, etc.) ...

    # Carregar configurações iniciais do banco
    state['settings'] = load_settings()

    # Conectar ao servidor WebSocket
    try:
        sio.connect('http://localhost:8080', namespaces=['/dashboard'])
    except socketio.exceptions.ConnectionError as e:
        print(f"Falha ao conectar ao servidor: {e}")
        print("Por favor, inicie o sensor_server.py primeiro.")
        return

    while True:
        # ... (lógica do loop principal) ...

        compute_values()

        if state['settings'].get('system_mode', 0) == 0:
            handle_automatic_mode()
        
        apply_actuator_state()

        # Envia atualização para o servidor
        sio.emit('dashboard_update', state, namespace='/dashboard')

        # ... (lógica de exibição do OpenCV e saída) ...
        
        sio.sleep(1) # Usar o sleep do socketio para permitir o processamento de eventos

    sio.disconnect()
    # ... (cleanup) ...

if __name__ == "__main__":
    main()
