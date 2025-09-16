#!/usr/bin/env python3
# sensor_server.py
# Servidor HTTP para visualização de dados dos sensores com gráficos

from flask import Flask, render_template, jsonify, request
import sqlite3
import json
from datetime import datetime, timedelta
import os

app = Flask(__name__)
DATABASE_PATH = "sensor_data.db"

# ============= FUNÇÕES DE BANCO DE DADOS =============

def get_db_connection():
    """Conecta ao banco de dados SQLite"""
    if not os.path.exists(DATABASE_PATH):
        return None
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
    return conn

def get_sensor_list():
    """Retorna lista de sensores disponíveis"""
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT sensor_name FROM sensor_readings ORDER BY sensor_name")
    sensors = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sensors

def get_sensor_data(sensor_name=None, start_date=None, end_date=None, limit=100, offset=0):
    """Busca dados dos sensores com filtros"""
    conn = get_db_connection()
    if not conn:
        return [], 0
    
    cursor = conn.cursor()
    
    # Construir query base
    where_clauses = []
    params = []
    
    if sensor_name:
        where_clauses.append("sensor_name = ?")
        params.append(sensor_name)
    
    if start_date:
        where_clauses.append("timestamp >= ?")
        params.append(start_date)
    
    if end_date:
        where_clauses.append("timestamp <= ?")
        params.append(end_date)
    
    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Query para contar total
    count_query = f"SELECT COUNT(*) FROM sensor_readings{where_sql}"
    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]
    
    # Query para buscar dados
    data_query = f"""
        SELECT * FROM sensor_readings{where_sql} 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
    """
    cursor.execute(data_query, params + [limit, offset])
    
    rows = cursor.fetchall()
    data = []
    for row in rows:
        data.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'sensor_name': row['sensor_name'],
            'temperature': row['temperature'],
            'pressure': row['pressure'],
            'velocity': row['velocity'],
            'sensor_type': row['sensor_type'],
            'pins': row['pins'],
            'mode': row['mode']
        })
    
    conn.close()
    return data, total

def get_chart_data(sensor_name, hours=24):
    """Busca dados para gráficos (últimas X horas)"""
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    start_time = datetime.now() - timedelta(hours=hours)
    
    cursor.execute("""
        SELECT timestamp, temperature, pressure, velocity 
        FROM sensor_readings 
        WHERE sensor_name = ? AND timestamp >= ?
        ORDER BY timestamp ASC
    """, (sensor_name, start_time.isoformat()))
    
    rows = cursor.fetchall()
    data = []
    for row in rows:
        data.append({
            'timestamp': row['timestamp'],
            'temperature': row['temperature'],
            'pressure': row['pressure'],
            'velocity': row['velocity']
        })
    
    conn.close()
    return data

def get_statistics():
    """Retorna estatísticas gerais do sistema"""
    conn = get_db_connection()
    if not conn:
        return {}
    
    cursor = conn.cursor()
    
    # Total de registros
    cursor.execute("SELECT COUNT(*) FROM sensor_readings")
    total_readings = cursor.fetchone()[0]
    
    # Registros por sensor
    cursor.execute("""
        SELECT sensor_name, COUNT(*) as count 
        FROM sensor_readings 
        GROUP BY sensor_name 
        ORDER BY count DESC
    """)
    sensor_counts = dict(cursor.fetchall())
    
    # Última leitura
    cursor.execute("""
        SELECT timestamp, sensor_name 
        FROM sensor_readings 
        ORDER BY timestamp DESC 
        LIMIT 1
    """)
    last_reading = cursor.fetchone()
    
    # Registros nas últimas 24h
    yesterday = datetime.now() - timedelta(days=1)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM sensor_readings 
        WHERE timestamp >= ?
    """, (yesterday.isoformat(),))
    readings_24h = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total_readings': total_readings,
        'sensor_counts': sensor_counts,
        'last_reading': dict(last_reading) if last_reading else None,
        'readings_24h': readings_24h
    }

# ============= ROTAS DO SERVIDOR =============

@app.route('/')
def index():
    """Página principal"""
    sensors = get_sensor_list()
    stats = get_statistics()
    return render_template('index.html', sensors=sensors, stats=stats)

@app.route('/api/sensors')
def api_sensors():
    """API: Lista de sensores"""
    return jsonify(get_sensor_list())

@app.route('/api/data')
def api_data():
    """API: Dados dos sensores com paginação e filtros"""
    sensor_name = request.args.get('sensor')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    offset = (page - 1) * per_page
    data, total = get_sensor_data(sensor_name, start_date, end_date, per_page, offset)
    
    return jsonify({
        'data': data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    })

@app.route('/api/chart/<sensor_name>')
def api_chart(sensor_name):
    """API: Dados para gráficos"""
    hours = int(request.args.get('hours', 24))
    data = get_chart_data(sensor_name, hours)
    return jsonify(data)

@app.route('/api/stats')
def api_stats():
    """API: Estatísticas gerais"""
    return jsonify(get_statistics())

@app.route('/sensor/<sensor_name>')
def sensor_detail(sensor_name):
    """Página de detalhes do sensor"""
    return render_template('sensor_detail.html', sensor_name=sensor_name)

# ============= INICIALIZAÇÃO =============

if __name__ == '__main__':
    # Verificar se banco existe
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Banco de dados não encontrado: {DATABASE_PATH}")
        print("🔧 Execute primeiro o dashboard para criar o banco de dados:")
        print("   python dashboard.py --img assets/base.jpeg")
        exit(1)
    
    print("🚀 Iniciando servidor de visualização de dados...")
    print(f"📊 Banco de dados: {DATABASE_PATH}")
    print("🌐 Acesse: http://localhost:8080")
    print("📱 Para acessar de outros dispositivos use: --host 0.0.0.0")
    print("💡 Se a porta 8080 estiver ocupada, o Flask tentará a próxima disponível")
    
    # Iniciar servidor (tentar porta 8080, se ocupada, o Flask tentará outras)
    try:
        app.run(host='127.0.0.1', port=3333, debug=True)
    except OSError as e:
        if "Address already in use" in str(e):
            print("⚠️  Porta 8080 ocupada, tentando porta 8081...")
            app.run(host='127.0.0.1', port=8081, debug=True)
        else:
            raise
