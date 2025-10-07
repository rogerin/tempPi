#!/usr/bin/env python3
# sensor_server.py
# Servidor HTTP e WebSocket para visualização e controle de dados dos sensores

from flask import Flask, render_template
from flask_socketio import SocketIO
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-for-iot-project'
socketio = SocketIO(app, async_mode='eventlet')

DATABASE_PATH = "sensor_data.db"

# ============= ROTAS HTTP =============

@app.route('/')
def index():
    """Página principal do dashboard."""
    return render_template('index.html')

@app.route('/control')
def control():
    """Página de controle do sistema."""
    return render_template('control.html')

# ============= EVENTOS WEBSOCKET =============

@socketio.on('connect', namespace='/web')
def handle_web_connect():
    """Chamado quando um cliente web (navegador) se conecta."""
    print('Cliente web conectado')
    # Ao conectar um novo cliente, solicita ao dashboard um update com os dados mais recentes
    socketio.emit('request_full_update', namespace='/dashboard')

@socketio.on('disconnect', namespace='/web')
def handle_web_disconnect():
    print('Cliente web desconectado')

@socketio.on('connect', namespace='/dashboard')
def handle_dashboard_connect():
    """Chamado quando o script dashboard.py se conecta."""
    print('Cliente dashboard.py conectado')

@socketio.on('disconnect', namespace='/dashboard')
def handle_dashboard_disconnect():
    print('Cliente dashboard.py desconectado')

@socketio.on('control_event', namespace='/web')
def handle_control_event(data):
    """Recebe um evento de controle da UI e o retransmite para o script do dashboard."""
    print(f"Comando da UI recebido: {data}")
    # Garante que o dashboard receba o comando
    socketio.emit('command_from_server', data, namespace='/dashboard')

@socketio.on('dashboard_update', namespace='/dashboard')
def handle_dashboard_update(data):
    """Recebe uma atualização de estado do dashboard e a retransmite para todos os clientes web."""
    # print(f"Update do dashboard recebido: {data}") # Descomente para debug
    socketio.emit('update_from_dashboard', data, namespace='/web')


# ============= INICIALIZAÇÃO =============

if __name__ == '__main__':
    print("🚀 Iniciando servidor Web e WebSocket...")
    print(f"🌐 Acesse o dashboard em http://localhost:8080")
    print(f"🕹️ Acesse o painel de controle em http://localhost:8080/control")
    
    # Usar eventlet é crucial para o bom funcionamento do SocketIO em produção
    import eventlet
    eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 8080)), app)