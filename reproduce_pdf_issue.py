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
    
    # Verificar se já tem dados
    cursor.execute("SELECT count(*) FROM sensor_readings WHERE timestamp >= '2025-11-05' AND timestamp <= '2025-11-06 23:59:59'")
    count = cursor.fetchone()[0]
    
    if count < 5:
        print("⚠️  Inserindo dados de teste extras para o período...")
        ts_base = datetime.datetime(2025, 11, 5, 10, 0, 0)
        for i in range(10):
             ts = ts_base + datetime.timedelta(hours=i)
             temp = 25.0 + i
             cursor.execute("INSERT INTO sensor_readings (sensor_name, temperature, timestamp, sensor_type, mode) VALUES (?, ?, ?, ?, ?)", ('Temp Forno', temp, ts, 'sim', 'auto'))
        conn.commit()
    
    conn.close()

    try:
        # Enviar requisição
        resp = client.post('/api/report/send', json={
            'start_date': '2025-11-05',
            'end_date': '2025-11-06',
            'target_email': 'geriofilho@gmail.com',
            'operation_name': 'Operacao Teste',
            'comments': 'Espaco para comentario aqui.'
        })
        
        print(f"🔄 Status Code: {resp.status_code}")
        print(f"📄 Response: {resp.json}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    test_specific_report()
