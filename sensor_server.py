#!/usr/bin/env python3
# sensor_server.py
# Servidor HTTP e WebSocket para visualização e controle de dados dos sensores

from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO
import os
import sqlite3
from datetime import datetime, timezone, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key-for-iot-project'
socketio = SocketIO(app)

DATABASE_PATH = "sensor_data.db"

def get_brazil_time():
    """Retorna timestamp atual em GMT-3 (Brasil)"""
    brazil_tz = timezone(timedelta(hours=-3))
    return datetime.now(brazil_tz)

def convert_to_brazil_time(timestamp_str):
    """Converte timestamp UTC para GMT-3 (Brasil)"""
    if not timestamp_str:
        return None
    try:
        # Se já está em formato string, assumir que é GMT-3
        if isinstance(timestamp_str, str):
            return timestamp_str
        # Se é datetime, converter para GMT-3
        brazil_tz = timezone(timedelta(hours=-3))
        if timestamp_str.tzinfo is None:
            # Se não tem timezone, assumir UTC
            timestamp_str = timestamp_str.replace(tzinfo=timezone.utc)
        return timestamp_str.astimezone(brazil_tz).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"Erro ao converter timestamp: {e}")
        return timestamp_str

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

        # Período de 24h com horário do Brasil
        now_br = get_brazil_time()
        start_24h = (now_br - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("SELECT COUNT(1) FROM sensor_readings WHERE timestamp >= ?", (start_24h,))
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

@app.route('/config')
def config():
    """Página de configurações do sistema."""
    return render_template('config.html')

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

        now_br = get_brazil_time()
        start_24h = (now_br - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("SELECT COUNT(1) FROM sensor_readings WHERE timestamp >= ?", (start_24h,))
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
        # Início baseado no horário de Brasília
        start_time = (get_brazil_time() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT timestamp, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            WHERE sensor_name = ? AND timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (sensor_name, start_time)
        )
        
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
    """API para dados consolidados de todos os sensores com filtros avançados."""
    try:
        # Parâmetros de filtro
        hours = request.args.get('hours', 24, type=int)
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        group_by = request.args.get('group_by', 'none')
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Construir query base
        if start_time and end_time:
            # Período customizado
            where_clause = "WHERE timestamp >= ? AND timestamp <= ?"
            params = [start_time, end_time]
        else:
            # Período por horas com horário do Brasil
            now_br = get_brazil_time()
            start_br = (now_br - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
            where_clause = "WHERE timestamp >= ?"
            params = [start_br]
        
        # Query base
        base_query = '''
            SELECT 
                timestamp,
                MAX(CASE WHEN sensor_name = 'Temp Forno' THEN temperature END) as temp_forno,
                MAX(CASE WHEN sensor_name = 'Torre Nível 1' THEN temperature END) as torre_nivel_1,
                MAX(CASE WHEN sensor_name = 'Torre Nível 2' THEN temperature END) as torre_nivel_2,
                MAX(CASE WHEN sensor_name = 'Torre Nível 3' THEN temperature END) as torre_nivel_3,
                MAX(CASE WHEN sensor_name = 'Temp Tanque' THEN temperature END) as temp_tanque,
                MAX(CASE WHEN sensor_name = 'Temp Saída Gases' THEN temperature END) as temp_gases,
                MAX(CASE WHEN sensor_name = 'Pressão Gases' THEN pressure END) as pressao_gases,
                MAX(CASE WHEN sensor_name = 'Velocidade' THEN velocity END) as velocity
            FROM sensor_readings
            {}
        '''.format(where_clause)
        
        # Aplicar agrupamento se necessário
        # Aplicar agrupamento se necessário
        if group_by != 'none':
            group_interval = get_group_interval(group_by)
            if group_interval:
                # Agrupar por intervalo de tempo usando unix epoch
                # datetime((strftime('%s', timestamp) / interval) * interval, 'unixepoch', 'localtime')
                
                group_query = '''
                    SELECT 
                        datetime((strftime('%s', timestamp) / {}) * {}, 'unixepoch', 'localtime') as timestamp,
                        AVG(CASE WHEN sensor_name = 'Temp Forno' THEN temperature END) as temp_forno,
                        AVG(CASE WHEN sensor_name = 'Torre Nível 1' THEN temperature END) as torre_nivel_1,
                        AVG(CASE WHEN sensor_name = 'Torre Nível 2' THEN temperature END) as torre_nivel_2,
                        AVG(CASE WHEN sensor_name = 'Torre Nível 3' THEN temperature END) as torre_nivel_3,
                        AVG(CASE WHEN sensor_name = 'Temp Tanque' THEN temperature END) as temp_tanque,
                        AVG(CASE WHEN sensor_name = 'Temp Saída Gases' THEN temperature END) as temp_gases,
                        AVG(CASE WHEN sensor_name = 'Pressão Gases' THEN pressure END) as pressao_gases,
                        AVG(CASE WHEN sensor_name = 'Velocidade' THEN velocity END) as velocity
                    FROM sensor_readings 
                    {}
                    GROUP BY 1
                    ORDER BY 1
                '''.format(group_interval, group_interval, where_clause)
                
                cursor.execute(group_query, params)
            else:
                 # Fallback
                 cursor.execute(base_query + ' GROUP BY timestamp ORDER BY timestamp', params)
        else:
            query = base_query + ' GROUP BY timestamp ORDER BY timestamp'
            cursor.execute(query, params)
            
        rows = cursor.fetchall()
        conn.close()

        
        # Converter para lista de dicionários
        data = []
        for row in rows:
            data.append({
                'timestamp': row[0],
                'temp_forno': round(row[1], 2) if row[1] is not None else None,
                'torre_nivel_1': round(row[2], 2) if row[2] is not None else None,
                'torre_nivel_2': round(row[3], 2) if row[3] is not None else None,
                'torre_nivel_3': round(row[4], 2) if row[4] is not None else None,
                'temp_tanque': round(row[5], 2) if row[5] is not None else None,
                'temp_gases': round(row[6], 2) if row[6] is not None else None,
                'pressao_gases': round(row[7], 2) if row[7] is not None else None,
                'velocity': round(row[8], 2) if row[8] is not None else None
            })
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/all-sensors/latest')
def api_all_sensors_latest():
    """Retorna o último registro consolidado de todos os sensores."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Buscar o último timestamp com dados
        cursor.execute('''
            SELECT 
                timestamp,
                MAX(CASE WHEN sensor_name = 'Temp Forno' THEN temperature END) as temp_forno,
                MAX(CASE WHEN sensor_name = 'Torre Nível 1' THEN temperature END) as torre_nivel_1,
                MAX(CASE WHEN sensor_name = 'Torre Nível 2' THEN temperature END) as torre_nivel_2,
                MAX(CASE WHEN sensor_name = 'Torre Nível 3' THEN temperature END) as torre_nivel_3,
                MAX(CASE WHEN sensor_name = 'Temp Tanque' THEN temperature END) as temp_tanque,
                MAX(CASE WHEN sensor_name = 'Temp Saída Gases' THEN temperature END) as temp_gases,
                MAX(CASE WHEN sensor_name = 'Pressão Gases' THEN pressure END) as pressao_gases,
                MAX(CASE WHEN sensor_name = 'Velocidade' THEN velocity END) as velocity,
                MAX(mode) as mode
            FROM sensor_readings
            WHERE timestamp = (SELECT MAX(timestamp) FROM sensor_readings)
            GROUP BY timestamp
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'timestamp': None,
                    'temp_forno': None,
                    'torre_nivel_1': None,
                    'torre_nivel_2': None,
                    'torre_nivel_3': None,
                    'temp_tanque': None,
                    'temp_gases': None,
                    'pressao_gases': None,
                    'velocity': None,
                'mode': None
            })
        
        return jsonify({
            'timestamp': row[0],
            'temp_forno': round(row[1], 2) if row[1] is not None else None,
            'torre_nivel_1': round(row[2], 2) if row[2] is not None else None,
            'torre_nivel_2': round(row[3], 2) if row[3] is not None else None,
            'torre_nivel_3': round(row[4], 2) if row[4] is not None else None,
            'temp_tanque': round(row[5], 2) if row[5] is not None else None,
            'temp_gases': round(row[6], 2) if row[6] is not None else None,
            'pressao_gases': round(row[7], 2) if row[7] is not None else None,
            'velocity': round(row[8], 2) if row[8] is not None else None,
            'mode': row[9]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/all-sensors/recent')
def api_all_sensors_recent():
    """Retorna os últimos N registros consolidados de todos os sensores."""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Buscar últimos N timestamps únicos
        cursor.execute('''
            SELECT DISTINCT timestamp
            FROM sensor_readings
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        timestamps = [row[0] for row in cursor.fetchall()]
        
        if not timestamps:
            conn.close()
            return jsonify([])
        
        # Buscar dados consolidados para esses timestamps
        placeholders = ','.join(['?'] * len(timestamps))
        cursor.execute(f'''
            SELECT 
                timestamp,
                MAX(CASE WHEN sensor_name = 'Temp Forno' THEN temperature END) as temp_forno,
                MAX(CASE WHEN sensor_name = 'Torre Nível 1' THEN temperature END) as torre_nivel_1,
                MAX(CASE WHEN sensor_name = 'Torre Nível 2' THEN temperature END) as torre_nivel_2,
                MAX(CASE WHEN sensor_name = 'Torre Nível 3' THEN temperature END) as torre_nivel_3,
                MAX(CASE WHEN sensor_name = 'Temp Tanque' THEN temperature END) as temp_tanque,
                MAX(CASE WHEN sensor_name = 'Temp Saída Gases' THEN temperature END) as temp_gases,
                MAX(CASE WHEN sensor_name = 'Pressão Gases' THEN pressure END) as pressao_gases,
                MAX(CASE WHEN sensor_name = 'Velocidade' THEN velocity END) as velocity,
                MAX(mode) as mode
            FROM sensor_readings
            WHERE timestamp IN ({placeholders})
            GROUP BY timestamp
            ORDER BY timestamp DESC
        ''', timestamps)
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                'timestamp': row[0],
                'temp_forno': round(row[1], 2) if row[1] is not None else None,
                'torre_nivel_1': round(row[2], 2) if row[2] is not None else None,
                'torre_nivel_2': round(row[3], 2) if row[3] is not None else None,
                'torre_nivel_3': round(row[4], 2) if row[4] is not None else None,
                'temp_tanque': round(row[5], 2) if row[5] is not None else None,
                'temp_gases': round(row[6], 2) if row[6] is not None else None,
                'pressao_gases': round(row[7], 2) if row[7] is not None else None,
                'velocity': round(row[8], 2) if row[8] is not None else None,
                'mode': row[9]
            })
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_group_interval(group_by):
    """Converte string de agrupamento para segundos."""
    intervals = {
        '2s': 2,
        '4s': 4,
        '6s': 6,
        '10s': 10,
        '30s': 30,
        '1min': 60,
        '5min': 300,
        '15min': 900,
        '1hour': 3600,
        '1day': 86400
    }
    return intervals.get(group_by, None)

@app.route('/api/config/smtp', methods=['GET', 'POST'])
def api_config_smtp():
    """API para configurações SMTP."""
    try:
        if request.method == 'GET':
            # Carregar configurações existentes
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Criar tabela se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smtp_config (
                    id INTEGER PRIMARY KEY,
                    smtp_host TEXT,
                    smtp_port INTEGER,
                    smtp_user TEXT,
                    smtp_password TEXT,
                    sender_email TEXT,
                    sender_name TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('SELECT * FROM smtp_config ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return jsonify({
                    'smtp_host': row[1],
                    'smtp_port': row[2],
                    'smtp_user': row[3],
                    'smtp_password': row[4],
                    'sender_email': row[5],
                    'sender_name': row[6]
                })
            else:
                return jsonify({})
                
        elif request.method == 'POST':
            # Salvar configurações
            data = request.get_json()
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Criar tabela se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS smtp_config (
                    id INTEGER PRIMARY KEY,
                    smtp_host TEXT,
                    smtp_port INTEGER,
                    smtp_user TEXT,
                    smtp_password TEXT,
                    sender_email TEXT,
                    sender_name TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Inserir nova configuração
            cursor.execute('''
                INSERT INTO smtp_config 
                (smtp_host, smtp_port, smtp_user, smtp_password, sender_email, sender_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('smtp_host'),
                data.get('smtp_port', 587),
                data.get('smtp_user'),
                data.get('smtp_password'),
                data.get('sender_email'),
                data.get('sender_name')
            ))
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'message': 'Configurações salvas com sucesso'})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/pressure-calibration', methods=['GET', 'POST'])
def api_pressure_calibration():
    """Lê/salva calibração de pressão (gain/offset) no banco."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calibration (
                key TEXT PRIMARY KEY,
                value REAL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        if request.method == 'GET':
            cursor.execute("SELECT value FROM calibration WHERE key='pressure_gain'")
            row_gain = cursor.fetchone()
            cursor.execute("SELECT value FROM calibration WHERE key='pressure_offset'")
            row_offset = cursor.fetchone()
            conn.close()
            return jsonify({
                'gain': float(row_gain[0]) if row_gain else 1.0,
                'offset': float(row_offset[0]) if row_offset else 0.0
            })
        else:
            data = request.get_json()
            gain = float(data.get('gain', 1.0))
            offset = float(data.get('offset', 0.0))
            cursor.execute("INSERT INTO calibration(key, value) VALUES('pressure_gain', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP", (gain,))
            cursor.execute("INSERT INTO calibration(key, value) VALUES('pressure_offset', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP", (offset,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/test-smtp', methods=['POST'])
def api_test_smtp():
    """Testa conexão SMTP."""
    server = None
    try:
        data = request.get_json()
        
        # Importar bibliotecas de email
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import socket
        
        # Configurar conexão
        smtp_host = data.get('smtp_host')
        smtp_port = data.get('smtp_port', 587)
        smtp_user = data.get('smtp_user')
        smtp_password = data.get('smtp_password')
        sender_email = data.get('sender_email', smtp_user)
        sender_name = data.get('sender_name', 'Sistema TempPi')
        
        # Criar email de teste
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = sender_email  # Enviar para si mesmo
        msg['Subject'] = "Teste de Configuração SMTP - TempPi"
        
        body = f"""
        Este é um email de teste do sistema TempPi.
        
        Configurações testadas:
        - Servidor: {smtp_host}:{smtp_port}
        - Usuário: {smtp_user}
        - Remetente: {sender_name} <{sender_email}>
        
        Se você recebeu este email, a configuração SMTP está funcionando corretamente!
        
        Enviado em: {get_brazil_time().strftime('%d/%m/%Y %H:%M:%S')}
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Testar conexão com timeout
        # Porta 465 usa SSL direto, porta 587 usa STARTTLS
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()  # Habilitar TLS para porta 587
        
        server.set_debuglevel(0)  # Desabilitar logs verbosos
        server.login(smtp_user, smtp_password)
        
        # Enviar email de teste
        text = msg.as_string()
        server.sendmail(sender_email, sender_email, text)
        
        return jsonify({
            'success': True,
            'message': f'Email de teste enviado com sucesso para {sender_email}'
        })
        
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'success': False,
            'error': 'Falha na autenticação. Verifique usuário e senha.'
        }), 400
    except smtplib.SMTPConnectError:
        return jsonify({
            'success': False,
            'error': 'Falha na conexão. Verifique servidor e porta.'
        }), 400
    except smtplib.SMTPServerDisconnected:
        return jsonify({
            'success': False,
            'error': 'Servidor desconectou inesperadamente. Tente usar porta 465 (SSL) ou 587 (TLS).'
        }), 400
    except socket.timeout:
        return jsonify({
            'success': False,
            'error': 'Timeout na conexão. O servidor SMTP não respondeu a tempo.'
        }), 408
    except socket.gaierror:
        return jsonify({
            'success': False,
            'error': 'Servidor SMTP não encontrado. Verifique o endereço.'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro inesperado: {str(e)}'
        }), 500
    finally:
        # Garantir que a conexão seja fechada
        if server:
            try:
                server.quit()
            except:
                pass


def _generate_pdf_bytes(data):
    """Função auxiliar para gerar bytes do PDF com base nos dados do filtro."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from io import BytesIO
    import base64
    import sqlite3
    
    # Normalizar timestamps
    def _normalize_ts(ts):
        if not ts: return None
        ts = ts.replace('T', ' ')
        if len(ts) == 16: ts = ts + ':00'
        return ts
    
    # Parâmetros
    time_range = data.get('timeRange', '24')
    start_time = _normalize_ts(data.get('startTime'))
    end_time = _normalize_ts(data.get('endTime'))
    group_by = data.get('groupBy', 'none')
    selected_sensors = data.get('selectedSensors', [])
    pressure_unit = data.get('pressureUnit', 'psi')
    
    # Metadados
    operation_name = data.get('operation_name', '')
    comments = data.get('comments', '')
    
    # Buscar dados
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if start_time and end_time:
        where_clause = "WHERE timestamp >= ? AND timestamp <= ?"
        params = [start_time, end_time]
    else:
        now_br = get_brazil_time()
        start_br = (now_br - timedelta(hours=int(time_range))).strftime('%Y-%m-%d %H:%M:%S')
        where_clause = "WHERE timestamp >= ?"
        params = [start_br]
    
    base_query = '''
        SELECT 
            timestamp,
            MAX(CASE WHEN sensor_name = 'Temp Forno' THEN temperature END) as temp_forno,
            MAX(CASE WHEN sensor_name = 'Torre Nível 1' THEN temperature END) as torre_nivel_1,
            MAX(CASE WHEN sensor_name = 'Torre Nível 2' THEN temperature END) as torre_nivel_2,
            MAX(CASE WHEN sensor_name = 'Torre Nível 3' THEN temperature END) as torre_nivel_3,
            MAX(CASE WHEN sensor_name = 'Temp Tanque' THEN temperature END) as temp_tanque,
            MAX(CASE WHEN sensor_name = 'Temp Saída Gases' THEN temperature END) as temp_gases,
            MAX(CASE WHEN sensor_name = 'Pressão Gases' THEN pressure END) as pressao_gases,
            MAX(CASE WHEN sensor_name = 'Velocidade' THEN velocity END) as velocity
        FROM sensor_readings 
        {}
    '''.format(where_clause)
    
    # Aplicar agrupamento se necessário
    if group_by != 'none':
        group_interval = get_group_interval(group_by)
        if group_interval:
            query = '''
                SELECT 
                    datetime((strftime('%s', timestamp) / {}) * {}, 'unixepoch', 'localtime') as timestamp,
                    AVG(CASE WHEN sensor_name = 'Temp Forno' THEN temperature END) as temp_forno,
                    AVG(CASE WHEN sensor_name = 'Torre Nível 1' THEN temperature END) as torre_nivel_1,
                    AVG(CASE WHEN sensor_name = 'Torre Nível 2' THEN temperature END) as torre_nivel_2,
                    AVG(CASE WHEN sensor_name = 'Torre Nível 3' THEN temperature END) as torre_nivel_3,
                    AVG(CASE WHEN sensor_name = 'Temp Tanque' THEN temperature END) as temp_tanque,
                    AVG(CASE WHEN sensor_name = 'Temp Saída Gases' THEN temperature END) as temp_gases,
                    AVG(CASE WHEN sensor_name = 'Pressão Gases' THEN pressure END) as pressao_gases,
                    AVG(CASE WHEN sensor_name = 'Velocidade' THEN velocity END) as velocity
                FROM sensor_readings 
                {}
                GROUP BY 1
                ORDER BY 1
            '''.format(group_interval, group_interval, where_clause)
        else:
            query = base_query + ' GROUP BY timestamp ORDER BY timestamp'
    else:
        query = base_query + ' GROUP BY timestamp ORDER BY timestamp'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    chart_data = []
    for row in rows:
        chart_data.append({
            'timestamp': row[0],
            'temp_forno': row[1],
            'torre_nivel_1': row[2],
            'torre_nivel_2': row[3],
            'torre_nivel_3': row[4],
            'temp_tanque': row[5],
            'temp_gases': row[6],
            'pressao_gases': row[7],
            'velocity': row[8]
        })
    
    if not chart_data:
        raise ValueError("Nenhum dado encontrado para o período especificado")
    
    # Gerar Gráfico
    import matplotlib
    matplotlib.use('Agg')
    plt.figure(figsize=(10, 6))
    
    sensor_colors = {
        'temp_forno': '#e74c3c', 'torre_nivel_1': '#3498db', 'torre_nivel_2': '#2ecc71',
        'torre_nivel_3': '#f39c12', 'temp_tanque': '#9b59b6', 'temp_gases': '#1abc9c',
        'pressao_gases': '#e67e22', 'velocity': '#34495e'
    }
    sensor_names = {
        'temp_forno': 'Temp Forno', 'torre_nivel_1': 'Torre Nível 1',
        'torre_nivel_2': 'Torre Nível 2', 'torre_nivel_3': 'Torre Nível 3',
        'temp_tanque': 'Temp Tanque', 'temp_gases': 'Temp Gases',
        'pressao_gases': 'Pressão Gases', 'velocity': 'Velocidade'
    }
    
    timestamps = [datetime.strptime(d['timestamp'], '%Y-%m-%d %H:%M:%S') for d in chart_data]
    
    for sensor in selected_sensors:
        if sensor in sensor_colors:
            values = [d[sensor] for d in chart_data if d[sensor] is not None]
            if values:
                sensor_timestamps = [ts for i, ts in enumerate(timestamps) if chart_data[i][sensor] is not None]
                plt.plot(sensor_timestamps, values, label=sensor_names[sensor], color=sensor_colors[sensor], linewidth=2)
    
    plt.title('Relatório de Sensores - TempPi')
    plt.xlabel('Tempo')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    
    # Formatar eixos de data
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=max(1, len(timestamps)//10)))
    
    plt.tight_layout()
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
    img_buffer.seek(0)
    plt.close()
    
    # Gerar PDF
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Cabeçalho
    story.append(Paragraph("Relatório de Sensores - TempPi", styles['Title']))
    
    if operation_name:
         story.append(Paragraph(f"<b>Operação:</b> {operation_name}", styles['Normal']))
         story.append(Spacer(1, 5))
         
    filter_info = f"""
    <b>Período:</b> {time_range if not start_time else f'{start_time} a {end_time}'}<br/>
    <b>Sensores:</b> {', '.join([sensor_names.get(s, s) for s in selected_sensors])}
    """
    story.append(Paragraph(filter_info, styles['Normal']))
    story.append(Spacer(1, 10))
    
    if comments:
        story.append(Paragraph("<b>Comentários:</b>", styles['Heading3']))
        story.append(Paragraph(comments.replace('\n', '<br/>'), styles['Normal']))
        story.append(Spacer(1, 10))
    
    # Gráfico
    story.append(Image(img_buffer, width=7*inch, height=4*inch))
    story.append(Spacer(1, 20))
    
    # Estatísticas
    story.append(Paragraph("Estatísticas Resumidas", styles['Heading2']))
    stats_data = [['Sensor', 'Mín', 'Máx', 'Média']]
    for sensor in selected_sensors:
        if sensor in sensor_names:
            values = [d[sensor] for d in chart_data if d[sensor] is not None]
            if values:
                stats_data.append([
                    sensor_names[sensor],
                    f"{min(values):.2f}",
                    f"{max(values):.2f}",
                    f"{sum(values)/len(values):.2f}"
                ])
    
    if len(stats_data) > 1:
        t = Table(stats_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(t)
        story.append(Spacer(1, 20))

    # Tabela de Dados Completos
    story.append(Paragraph("Dados Detalhados", styles['Heading2']))
    
    # Cabeçalho da tabela completa
    full_table_header = ['Data/Hora'] + [sensor_names[s] for s in selected_sensors if s in sensor_names]
    full_table_data = [full_table_header]
    
    # Linhas de dados (limitado a 5000 para evitar crash por memória em ranges muito grandes, opcional)
    # Mas o usuário pediu "todos os dados". Vamos colocar todos.
    
    for d in chart_data:
        row_vals = [datetime.strptime(d['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%d/%m %H:%M')]
        has_val = False
        for sensor in selected_sensors:
             val = d.get(sensor)
             if val is not None:
                 if sensor == 'pressao_gases' and pressure_unit == 'bar':
                     val = val * 0.0689476
                     row_vals.append(f"{val:.2f}")
                 else:
                     row_vals.append(f"{val:.2f}")
                 has_val = True
             else:
                 row_vals.append("-")
        
        # Só adiciona se tiver algum valor relevante
        if has_val:
            full_table_data.append(row_vals)
            
    # Estilizar tabela grande
    # Se for muito grande, Table do reportlab pode ser lenta.
    # Mas para uso típico (alguns milhares) é ok.
    if len(full_table_data) > 1:
        # Quebra automática de páginas é gerenciada pelo SimpleDocTemplate
        t_full = Table(full_table_data, repeatRows=1)
        t_full.setStyle(TableStyle([
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(t_full)
        
    doc.build(story)
    return pdf_buffer.getvalue()

@app.route('/api/reports/generate-pdf', methods=['POST'])
def api_generate_pdf():
    """Gera relatório PDF com dados dos sensores."""
    try:
        data = request.get_json()
        
        try:
            pdf_bytes = _generate_pdf_bytes(data)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
            
        # Retornar PDF
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=relatorio_sensores_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            }
        )
        
    except Exception as e:
        return jsonify({"error": f"Erro ao gerar PDF: {str(e)}"}), 500

@app.route('/api/reports/send-consolidated-email', methods=['POST'])
def api_send_consolidated_email():
    """Gera PDF consolidado e envia por email."""
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        
        data = request.get_json()
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name', '')
        message = data.get('message', '')
        
        if not recipient_email:
            return jsonify({'success': False, 'error': 'Email de destinatário obrigatório'}), 400
            
        # Gerar PDF
        try:
            pdf_bytes = _generate_pdf_bytes(data)
        except ValueError as ve:
            return jsonify({'success': False, 'error': str(ve)}), 400
            
        # Configurar Email
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM smtp_config ORDER BY id DESC LIMIT 1')
        smtp_config = cursor.fetchone()
        conn.close()
        
        if not smtp_config:
            return jsonify({'success': False, 'error': 'SMTP não configurado'}), 400
            
        msg = MIMEMultipart()
        msg['From'] = f"{smtp_config[6]} <{smtp_config[5]}>"
        msg['To'] = recipient_email
        msg['Subject'] = "Relatório Consolidado - TempPi"
        
        body = f"""
        Olá {recipient_name},
        
        Segue em anexo o relatório consolidado dos sensores solicitados.
        
        {f'Mensagem: {message}' if message else ''}
        
        Atenciosamente,
        Sistema TempPi
        """
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # Anexar PDF
        part = MIMEApplication(pdf_bytes, Name="relatorio_consolidado.pdf")
        part['Content-Disposition'] = 'attachment; filename="relatorio_consolidado.pdf"'
        msg.attach(part)
        
        # Enviar
        smtp_host = smtp_config[1]
        smtp_port = smtp_config[2]
        smtp_user = smtp_config[3]
        smtp_password = smtp_config[4]
        
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()
            
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_config[5], recipient_email, msg.as_string())
        server.quit()
        
        return jsonify({'success': True, 'message': 'Email enviado com sucesso!'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reports/send-email', methods=['POST'])
def api_send_email():
    """Envia relatório por email."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email import encoders
        import csv
        from io import StringIO
        
        data = request.get_json()
        
        # Carregar configurações SMTP
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM smtp_config ORDER BY id DESC LIMIT 1')
        smtp_config = cursor.fetchone()
        conn.close()
        
        if not smtp_config:
            return jsonify({
                'success': False,
                'error': 'Configuração SMTP não encontrada. Configure primeiro em /config'
            }), 400
        
        # Dados do email
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name', '')
        subject = data.get('subject', f"Relatório de {data.get('sensor_name', 'Sensor')} - TempPi")
        period = data.get('period', 24)
        include_chart = data.get('include_chart', True)
        include_stats = data.get('include_stats', True)
        include_raw_data = data.get('include_raw_data', False)
        message = data.get('message', '')
        sensor_name = data.get('sensor_name', 'Sensor')
        
        # Buscar dados do sensor
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, temperature, pressure, velocity, sensor_type, mode
            FROM sensor_readings
            WHERE sensor_name = ? AND timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp ASC
        '''.format(period), (sensor_name,))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return jsonify({
                'success': False,
                'error': 'Nenhum dado encontrado para o período especificado'
            }), 400
        
        # Preparar dados
        chart_data = []
        for row in rows:
            chart_data.append({
                'timestamp': row[0],
                'temperature': row[1],
                'pressure': row[2],
                'velocity': row[3],
                'sensor_type': row[4],
                'mode': row[5]
            })
        
        # Criar email
        msg = MIMEMultipart()
        msg['From'] = f"{smtp_config[6]} <{smtp_config[5]}>"  # sender_name <sender_email>
        msg['To'] = f"{recipient_name} <{recipient_email}>" if recipient_name else recipient_email
        msg['Subject'] = subject
        
        # Corpo do email
        body = f"""
        <html>
        <body>
            <h2>Relatório de {sensor_name} - TempPi</h2>
            
            <p><strong>Período:</strong> Últimas {period} horas</p>
            <p><strong>Sensor:</strong> {sensor_name}</p>
            <p><strong>Total de leituras:</strong> {len(chart_data)}</p>
            <p><strong>Gerado em:</strong> {get_brazil_time().strftime('%d/%m/%Y %H:%M:%S')}</p>
            
            {f'<p><strong>Mensagem:</strong> {message}</p>' if message else ''}
            
            <hr>
        """
        
        # Adicionar estatísticas se solicitado
        if include_stats and chart_data:
            temp_values = [d['temperature'] for d in chart_data if d['temperature'] is not None]
            pressure_values = [d['pressure'] for d in chart_data if d['pressure'] is not None]
            velocity_values = [d['velocity'] for d in chart_data if d['velocity'] is not None]
            
            body += "<h3>Estatísticas Resumidas</h3><ul>"
            
            if temp_values:
                body += f"<li><strong>Temperatura:</strong> Min: {min(temp_values):.2f}°C, Max: {max(temp_values):.2f}°C, Média: {sum(temp_values)/len(temp_values):.2f}°C</li>"
            
            if pressure_values:
                body += f"<li><strong>Pressão:</strong> Min: {min(pressure_values):.2f} PSI, Max: {max(pressure_values):.2f} PSI, Média: {sum(pressure_values)/len(pressure_values):.2f} PSI</li>"
            
            if velocity_values:
                body += f"<li><strong>Velocidade:</strong> Min: {min(velocity_values):.2f}, Max: {max(velocity_values):.2f}, Média: {sum(velocity_values)/len(velocity_values):.2f}</li>"
            
            body += "</ul>"
        
        # Adicionar dados brutos se solicitado
        if include_raw_data and chart_data:
            body += "<h3>Dados Brutos (CSV)</h3>"
            body += "<p>Verifique o anexo CSV para os dados completos.</p>"
            
            # Criar CSV
            csv_buffer = StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(['Timestamp', 'Temperatura', 'Pressão', 'Velocidade', 'Tipo', 'Modo'])
            
            for d in chart_data:
                writer.writerow([
                    d['timestamp'],
                    d['temperature'] or '',
                    d['pressure'] or '',
                    d['velocity'] or '',
                    d['sensor_type'] or '',
                    d['mode'] or ''
                ])
            
            # Anexar CSV
            csv_attachment = MIMEBase('application', 'octet-stream')
            csv_attachment.set_payload(csv_buffer.getvalue().encode())
            encoders.encode_base64(csv_attachment)
            csv_attachment.add_header(
                'Content-Disposition',
                f'attachment; filename=relatorio_{sensor_name.replace(" ", "_")}_{period}h.csv'
            )
            msg.attach(csv_attachment)
        
        body += """
            <hr>
            <p><em>Este relatório foi gerado automaticamente pelo sistema TempPi.</em></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html', 'utf-8'))
        
        # Enviar email
        smtp_host = smtp_config[1]
        smtp_port = smtp_config[2]
        smtp_user = smtp_config[3]
        smtp_password = smtp_config[4]
        
        # Porta 465 usa SSL direto, porta 587 usa STARTTLS
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()  # Habilitar TLS para porta 587
        
        server.set_debuglevel(0)
        server.login(smtp_user, smtp_password)
        
        text = msg.as_string()
        server.sendmail(smtp_config[5], recipient_email, text)  # sender_email, recipient
        server.quit()
        
        return jsonify({
            'success': True,
            'message': f'Email enviado com sucesso para {recipient_email}'
        })
        
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'success': False,
            'error': 'Falha na autenticação SMTP. Verifique as configurações.'
        }), 400
    except smtplib.SMTPConnectError:
        return jsonify({
            'success': False,
            'error': 'Falha na conexão SMTP. Verifique servidor e porta.'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao enviar email: {str(e)}'
        }), 500

@app.route('/api/report/send', methods=['POST'])
def api_report_send():
    """Gera relatório PDF com gráficos e dados agregados por hora e envia por email."""
    server = None
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        target_email = data.get('target_email')  # Opcional, se não vier usa o do config
        operation_name = data.get('operation_name')
        comments = data.get('comments')
        if not start_date or not end_date:
            return jsonify({'success': False, 'error': 'Datas de início e fim são obrigatórias'}), 400

        # --- Imports Locais para economizar memória se não usado ---
        import matplotlib
        matplotlib.use('Agg') # Backend não interativo
        import matplotlib.pyplot as plt
        import io
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        import sqlite3
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication
        from collections import defaultdict
        from datetime import datetime

        # 1. Configurações SMTP
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT smtp_host, smtp_port, smtp_user, smtp_password, sender_email, sender_name FROM smtp_config ORDER BY id DESC LIMIT 1')
        smtp_row = cursor.fetchone()
        
        if not smtp_row:
             conn.close()
             return jsonify({'success': False, 'error': 'SMTP não configurado.'}), 400
             
        smtp_host, smtp_port, smtp_user, smtp_password, sender_email, sender_name = smtp_row
        recipient_email = target_email if target_email else sender_email

        # 2. Buscar Dados
        if len(start_date) == 10: start_date += " 00:00:00"
        if len(end_date) == 10: end_date += " 23:59:59"
        
        # Se vier com T (do datetime-local input), substituir por espaço
        start_date = start_date.replace('T', ' ')
        end_date = end_date.replace('T', ' ')

        cursor.execute(
            """
            SELECT timestamp, sensor_name, temperature, pressure
            FROM sensor_readings
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (start_date, end_date)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
             return jsonify({'success': False, 'error': 'Sem dados no período.'}), 404

        # 3. Processar Dados (Agregação por Hora)
        # dict[hour_str] -> dict[sensor_name] -> list[values]
        data_by_hour = defaultdict(lambda: defaultdict(list))
        
        # Para o gráfico: dict[sensor_name] -> {'timestamps': [], 'values': []}
        chart_data = defaultdict(lambda: {'timestamps': [], 'values': []})

        for row in rows:
            ts_str, sensor, temp, press = row
            # Converter timestamp string para objeto datetime
            try:
                dt = datetime.strptime(ts_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue # Pula formatos inválidos
            
            val = temp if temp is not None else press
            if val is None: continue

            # Agregação Horária
            hour_key = dt.strftime('%d/%m/%Y %H:00')
            data_by_hour[hour_key][sensor].append(val)

            # Dados Gráfico (Raw)
            chart_data[sensor]['timestamps'].append(dt)
            chart_data[sensor]['values'].append(val)

        # Calcular médias horárias
        # aggregated_rows: list de [Hora, SensorA_Avg, SensorB_Avg, ...]
        active_sensors = sorted(list(chart_data.keys()))
        aggregated_rows = []
        
        sorted_hours = sorted(data_by_hour.keys())
        for h in sorted_hours:
            row_vals = [h]
            for s in active_sensors:
                vals = data_by_hour[h].get(s, [])
                if vals:
                    avg = sum(vals) / len(vals)
                    row_vals.append(f"{avg:.2f}")
                else:
                    row_vals.append("-")
            aggregated_rows.append(row_vals)

        # 4. Gerar Gráfico
        plt.figure(figsize=(10, 5))
        for sensor in active_sensors:
            times = chart_data[sensor]['timestamps']
            vals = chart_data[sensor]['values']
            plt.plot(times, vals, label=sensor)
        
        plt.title(f"Tendências: {start_date} a {end_date}")
        plt.xlabel("Tempo")
        plt.ylabel("Valor")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100)
        img_buffer.seek(0)
        plt.close()

        # 5. Gerar PDF
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Título
        elements.append(Paragraph("Relatório do Sistema TempPi", styles['Title']))
        elements.append(Paragraph(f"Período: {start_date} até {end_date}", styles['Normal']))
        elements.append(Paragraph(f"Total de Registros Processados: {len(rows)}", styles['Normal']))

        if operation_name:
            elements.append(Paragraph(f"<b>Operação:</b> {operation_name}", styles['Normal']))

        elements.append(Spacer(1, 20))

        # Imagem do Gráfico
        rl_img = RLImage(img_buffer, width=450, height=250)
        elements.append(rl_img)
        elements.append(Spacer(1, 20))

        # Tabela de Dados Agregados
        # Header
        table_data = [['Data/Hora'] + active_sensors]
        # Rows
        table_data.extend(aggregated_rows)

        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        # Removido do rodapé para o topo elements.append(Paragraph(f"Total de Registros Processados: {len(rows)}", styles['Normal']))

        if comments:
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("<b>Comentários:</b>", styles['Heading3']))
            elements.append(Paragraph(comments.replace('\n', '<br/>'), styles['Normal']))

        doc.build(elements)
        pdf_bytes = pdf_buffer.getvalue()

        # 6. Enviar Email
        msg = MIMEMultipart()
        msg['From'] = f"{sender_name} <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = f"Relatório TempPi (PDF): {start_date}"

        msg.attach(MIMEText("Segue em anexo o relatório PDF com gráfico e dados agregados.", 'plain', 'utf-8'))

        part = MIMEApplication(pdf_bytes, Name="relatorio.pdf")
        part['Content-Disposition'] = f'attachment; filename="relatorio_{start_date[:10]}.pdf"'
        msg.attach(part)

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()
            
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        
        return jsonify({'success': True, 'message': f'PDF enviado para {recipient_email}'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if server:
            try: server.quit()
            except: pass

# ===== Admin: Reset de dados de sensores =====
@app.route('/api/admin/reset-sensor-data', methods=['POST'])
def api_admin_reset_sensor_data():
    """Apaga todos os registros da tabela sensor_readings. Não altera configurações."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(1) FROM sensor_readings')
        count = cursor.fetchone()[0] or 0
        cursor.execute('DELETE FROM sensor_readings')
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'deleted': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/network-info')
def api_network_info():
    """Retorna informações de rede do servidor."""
    import socket
    try:
        # Obter IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Porta do servidor
        port = 3333
        
        return jsonify({
            'local_ip': local_ip,
            'port': port,
            'url': f'http://{local_ip}:{port}',
            'hostname': socket.gethostname()
        })
    except Exception as e:
        return jsonify({
            'local_ip': 'N/A',
            'port': 3333,
            'url': 'N/A',
            'hostname': 'N/A',
            'error': str(e)
        }), 500

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
    
    socketio.run(app, host='0.0.0.0', port=3333)