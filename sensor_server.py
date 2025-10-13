#!/usr/bin/env python3
# sensor_server.py
# Servidor HTTP e WebSocket para visualização e controle de dados dos sensores

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO
import os
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-for-iot-project'
socketio = SocketIO(app)

DATABASE_PATH = "sensor_data.db"

# ============= ROTAS HTTP =============

@app.route('/')
def index():
    """Página principal do dashboard: envia sensores e estatísticas iniciais para o template."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Sensores distintos
        cursor.execute("SELECT DISTINCT sensor_name FROM sensor_readings")
        sensors_rows = cursor.fetchall()
        sensors = [row[0] for row in sensors_rows]

        # Estatísticas
        cursor.execute("SELECT COUNT(1) FROM sensor_readings")
        total_readings = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(1) FROM sensor_readings WHERE timestamp >= datetime('now','-1 day')")
        readings_24h = cursor.fetchone()[0] or 0

        cursor.execute("""
            SELECT id, timestamp, sensor_name, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        last_row = cursor.fetchone()
        last_reading = None
        if last_row:
            last_reading = {
                'id': last_row[0],
                'timestamp': last_row[1],
                'sensor_name': last_row[2],
                'temperature': last_row[3],
                'pressure': last_row[4],
                'velocity': last_row[5],
                'sensor_type': last_row[6],
                'mode': last_row[7],
            }

        conn.close()

        stats = {
            'total_readings': total_readings,
            'readings_24h': readings_24h,
            'last_reading': last_reading
        }

        return render_template('index.html', sensors=sensors, stats=stats)
    except Exception:
        # Em caso de erro, ainda renderiza a página
        return render_template('index.html', sensors=[], stats={})

@app.route('/control')
def control():
    """Página de controle do sistema."""
    return render_template('control.html')

@app.route('/sensor/<sensor_name>')
def sensor_detail(sensor_name):
    """Página de detalhes de um sensor específico."""
    return render_template('sensor_detail.html', sensor_name=sensor_name)

@app.route('/sensor/all')
def all_sensors():
    """Página de visualização de todos os sensores em um gráfico único."""
    return render_template('all_sensors.html')

@app.route('/api/sensors')
def api_sensors():
    """Retorna uma lista única de nomes de sensores."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT sensor_name FROM sensor_readings")
        rows = cursor.fetchall()
        conn.close()
        
        data = [row[0] for row in rows]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/readings')
def api_readings():
    """Lista leituras com filtros e paginação fixa de 50 por página."""
    try:
        sensor = request.args.get('sensor')
        start = request.args.get('start')  # ISO datetime
        end = request.args.get('end')      # ISO datetime
        page = max(int(request.args.get('page', 1)), 1)
        page_size = 50
        offset = (page - 1) * page_size

        where = []
        params = []
        if sensor:
            where.append("sensor_name = ?")
            params.append(sensor)
        if start:
            where.append("timestamp >= ?")
            params.append(start)
        if end:
            where.append("timestamp <= ?")
            params.append(end)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # total
        cursor.execute(f"SELECT COUNT(1) FROM sensor_readings {where_sql}", params)
        total = cursor.fetchone()[0] or 0

        # page items
        cursor.execute(
            f"""
            SELECT id, timestamp, sensor_name, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            {where_sql}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset]
        )
        rows = cursor.fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append({
                'id': r[0],
                'timestamp': r[1],
                'sensor_name': r[2],
                'temperature': r[3],
                'pressure': r[4],
                'velocity': r[5],
                'sensor_type': r[6],
                'mode': r[7],
            })

        total_pages = (total + page_size - 1) // page_size
        return jsonify({
            'items': items,
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/readings/export')
def api_readings_export():
    """Exporta leituras em CSV com os mesmos filtros da listagem."""
    try:
        sensor = request.args.get('sensor')
        start = request.args.get('start')
        end = request.args.get('end')

        where = []
        params = []
        if sensor:
            where.append("sensor_name = ?")
            params.append(sensor)
        if start:
            where.append("timestamp >= ?")
            params.append(start)
        if end:
            where.append("timestamp <= ?")
            params.append(end)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT timestamp, sensor_name, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            {where_sql}
            ORDER BY timestamp DESC
            """,
            params
        )
        rows = cursor.fetchall()
        conn.close()

        # Monta CSV
        lines = ["timestamp,sensor,temperature,pressure,velocity,type,mode"]
        for r in rows:
            line = ",".join([
                str(r[0] or ''), str(r[1] or ''),
                str(r[2] if r[2] is not None else ''),
                str(r[3] if r[3] is not None else ''),
                str(r[4] if r[4] is not None else ''),
                str(r[5] or ''), str(r[6] or ''),
            ])
            lines.append(line)
        csv_data = "\n".join(lines)

        return Response(
            csv_data,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename="readings.csv"'}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """Estatísticas para cards da home."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(1) FROM sensor_readings")
        total_readings = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(1) FROM sensor_readings WHERE timestamp >= datetime('now','-1 day')")
        readings_24h = cursor.fetchone()[0] or 0

        cursor.execute("SELECT DISTINCT sensor_name FROM sensor_readings")
        sensors = [r[0] for r in cursor.fetchall()]

        cursor.execute(
            """
            SELECT id, timestamp, sensor_name, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        last_row = cursor.fetchone()
        last_reading = None
        if last_row:
            last_reading = {
                'id': last_row[0],
                'timestamp': last_row[1],
                'sensor_name': last_row[2],
                'temperature': last_row[3],
                'pressure': last_row[4],
                'velocity': last_row[5],
                'sensor_type': last_row[6],
                'mode': last_row[7],
            }

        conn.close()

        return jsonify({
            'total_readings': total_readings,
            'readings_24h': readings_24h,
            'last_reading': last_reading,
            'sensors': sensors,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health/sensors')
def api_health_sensors():
    """Retorna status atual dos sensores (modo degradado incluído)."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS sensor_status (
                name TEXT PRIMARY KEY,
                ok INTEGER NOT NULL,
                last_error TEXT,
                pins TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        cursor.execute("SELECT name, ok, last_error, pins, updated_at FROM sensor_status ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append({
                'name': r[0],
                'ok': bool(r[1]),
                'last_error': r[2],
                'pins': r[3],
                'updated_at': r[4],
            })
        return jsonify(items)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sensor/<sensor_name>/data')
def api_sensor_data(sensor_name):
    """Retorna dados históricos de um sensor específico."""
    try:
        hours = int(request.args.get('hours', 24))
        start_time = f"datetime('now', '-{hours} hours')"
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT timestamp, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            WHERE sensor_name = ? AND timestamp >= {start_time}
            ORDER BY timestamp ASC
        """, (sensor_name,))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                'timestamp': row[0],
                'temperature': row[1],
                'pressure': row[2],
                'velocity': row[3],
                'sensor_type': row[4],
                'mode': row[5]
            })
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/all-sensors/data')
def api_all_sensors_data():
    """Retorna dados históricos de todos os sensores combinados."""
    try:
        hours = int(request.args.get('hours', 24))
        start_time = f"datetime('now', '-{hours} hours')"
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Buscar dados de todos os sensores no período
        cursor.execute(f"""
            SELECT timestamp, sensor_name, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            WHERE timestamp >= {start_time}
            ORDER BY timestamp ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Organizar dados por timestamp
        data_by_time = {}
        for row in rows:
            timestamp = row[0]
            sensor_name = row[1]
            temperature = row[2]
            pressure = row[3]
            velocity = row[4]
            sensor_type = row[5]
            mode = row[6]
            
            if timestamp not in data_by_time:
                data_by_time[timestamp] = {
                    'timestamp': timestamp,
                    'temp_forno': None,
                    'torre_nivel_1': None,
                    'torre_nivel_2': None,
                    'torre_nivel_3': None,
                    'temp_tanque': None,
                    'temp_gases': None,
                    'pressao_gases': None,
                    'velocity': None,
                    'mode': mode
                }
            
            # Mapear nomes dos sensores para campos padronizados
            if sensor_name == 'Temp Forno':
                data_by_time[timestamp]['temp_forno'] = temperature
            elif sensor_name == 'Torre Nível 1':
                data_by_time[timestamp]['torre_nivel_1'] = temperature
            elif sensor_name == 'Torre Nível 2':
                data_by_time[timestamp]['torre_nivel_2'] = temperature
            elif sensor_name == 'Torre Nível 3':
                data_by_time[timestamp]['torre_nivel_3'] = temperature
            elif sensor_name == 'Temp Tanque':
                data_by_time[timestamp]['temp_tanque'] = temperature
            elif sensor_name == 'Temp Saída Gases':
                data_by_time[timestamp]['temp_gases'] = temperature
            elif sensor_name == 'Pressão Gases':
                data_by_time[timestamp]['pressao_gases'] = pressure
            elif sensor_name == 'Velocidade':
                data_by_time[timestamp]['velocity'] = velocity
        
        # Converter para lista ordenada
        data = list(data_by_time.values())
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============= EVENTOS WEBSOCKET =============

@socketio.on('connect', namespace='/web')
def handle_web_connect():
    """Chamado quando um cliente web (navegador) se conecta."""
    print('Cliente web conectado')
    # Ao conectar um novo cliente, solicita ao dashboard um update com os dados mais recentes
    socketio.emit('request_full_update', namespace='/dashboard')

@socketio.on('request_initial_data', namespace='/web')
def handle_request_initial_data():
    """Solicitação explícita do cliente web para obter estado atual do dashboard."""
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
    print(f"📡 Retransmitindo update para web: actuators={data.get('actuators')}")
    socketio.emit('update_from_dashboard', data, namespace='/web')


# ============= INICIALIZAÇÃO =============

if __name__ == '__main__':
    print("🚀 Iniciando servidor Web e WebSocket...")
    print(f"🌐 Acesse o dashboard em http://localhost:3333")
    print(f"🕹️ Acesse o painel de controle em http://localhost:3333/control")
    
    socketio.run(app, host='127.0.0.1', port=3333)