import json
from sensor_server import app
import sqlite3
import datetime

def test_specific_report():
    print("🚀 Testando envio de RELATÓRIO PDF...")
    print("📅 Período: 2025-11-05 a 2025-11-06")
    print("📧 Destino: geriofilho@gmail.com")

    client = app.test_client()
    
    # Inserir dados mais variados para o gráfico ficar bonito
    conn = sqlite3.connect("sensor_data.db")
    cursor = conn.cursor()
    
    # Verificar dados dia 6
    cursor.execute("SELECT count(*) FROM sensor_readings WHERE timestamp >= '2025-11-06' AND timestamp <= '2025-11-06 23:59:59'")
    count_06 = cursor.fetchone()[0]
    
    if count_06 < 50:
        print("⚠️  Inserindo dados de ALTA RESOLUÇÃO (10min) para 05/11 e 06/11...")
        import math
        
        # Dados dia 05 - Frequência 10 min
        ts_base = datetime.datetime(2025, 11, 5, 8, 0, 0)
        # Gerar 60 pontos (10 horas * 6 pontos/hora)
        for i in range(60):
             ts = ts_base + datetime.timedelta(minutes=i*10)
             # Criar uma curva senoidal para ficar bonito no gráfico
             temp = 25.0 + 5 * math.sin(i / 10.0)
             cursor.execute("INSERT INTO sensor_readings (sensor_name, temperature, timestamp, sensor_type, mode) VALUES (?, ?, ?, ?, ?)", ('Temp Forno', temp, ts, 'sim', 'auto'))
        
        # Dados dia 06 - Frequência 10 min
        ts_base_6 = datetime.datetime(2025, 11, 6, 8, 0, 0)
        for i in range(60):
             ts = ts_base_6 + datetime.timedelta(minutes=i*10)
             temp = 30.0 + 5 * math.cos(i / 10.0)
             cursor.execute("INSERT INTO sensor_readings (sensor_name, temperature, timestamp, sensor_type, mode) VALUES (?, ?, ?, ?, ?)", ('Temp Forno', temp, ts, 'sim', 'auto'))
        
        conn.commit()
    
    conn.close()

    print("🚀 Enviando relatórios solicitados (05/11 e 06/11)...")
    
    # Relatório 1: 05/11 Completo
    run_test_request(client, 1, '2025-11-05 00:00:00', '2025-11-05 23:59:59', 'Relatório Diário 05/11', 'Dados completos do dia 05.')
    
    # Relatório 2: 06/11 Completo
    run_test_request(client, 2, '2025-11-06 00:00:00', '2025-11-06 23:59:59', 'Relatório Diário 06/11', 'Dados completos do dia 06.')

def run_test_request(client, test_num, start, end, op_name, comments):
    print(f"\n📄 [Teste {test_num}] Enviando relatório de {start} a {end}...")
    try:
        resp = client.post('/api/report/send', json={
            'start_date': start,
            'end_date': end,
            'target_email': 'geriofilho@gmail.com',
            'operation_name': op_name,
            'comments': comments
        })
        print(f"   Status: {resp.status_code}")
        print(f"   Msg: {resp.json.get('message', resp.json)}")
    except Exception as e:
        print(f"   ❌ Erro: {e}")

if __name__ == "__main__":
    test_specific_report()
