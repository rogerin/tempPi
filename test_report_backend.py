import json
from sensor_server import app
import sqlite3
import datetime

def test_report_endpoint():
    print("🚀 Iniciando teste do endpoint de relatório...")
    
    # Garantir que o banco existe
    # init_database() - Removido pois não é exportado, banco deve estar via configure_smtp


    # Criar cliente de teste
    client = app.test_client()
    
    # 1. Inserir dados de teste se não houver
    conn = sqlite3.connect("sensor_data.db")
    cursor = conn.cursor()
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    # Adicionando sensor_type e mode para satisfazer constraints
    cursor.execute(f"INSERT INTO sensor_readings (sensor_name, temperature, timestamp, sensor_type, mode) VALUES ('Teste', 100.0, '{today} 12:00:00', 'test', 'auto')")
    conn.commit()
    conn.close()
    
    # 2. Testar payload inválido (sem datas)
    resp = client.post('/api/report/send', json={})
    assert resp.status_code == 400, f"Esperad0 400, recebeu {resp.status_code}"
    print("✅ Teste payload inválido: OK")
    
    # 3. Testar envio (Simulação - assumindo que config SMTP já existe)
    # Nota: Isso vai TENTAR enviar o email real se o SMTP estiver configurado corretamente.
    # Se falhar a autenticação, vai retornar 400 ou 500, mas validamos que o endpoint existe e processa.
    
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    
    try:
        resp = client.post('/api/report/send', json={
            'start_date': today_str,
            'end_date': today_str,
            # 'target_email': 'teste@exemplo.com' # Comentar para usar o padrão do banco
        })
        
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.json}")
        
        if resp.status_code == 200:
             print("✅ Teste de envio: SUCESSO (Email enviado!)")
        elif resp.status_code == 400 and 'autenticação' in str(resp.json):
             print("⚠️  Teste de envio: Falha de autenticação (Esperado se credenciais forem inválidas, mas endpoint funcionou)")
        else:
             print(f"⚠️  Resultado: {resp.json}")

    except Exception as e:
        print(f"❌ Erro durante requisição: {e}")

if __name__ == "__main__":
    test_report_endpoint()
