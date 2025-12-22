#!/usr/bin/env python3
"""
Script para gerar dados de teste no banco de dados TempPi.
Cria registros simulados das últimas 24 horas para todos os sensores.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
import random
import math
import sys

# Configurações
DATABASE_PATH = 'sensor_data.db'
HOURS_TO_GENERATE = 24
READINGS_PER_HOUR = 12  # 1 leitura a cada 5 minutos

# Função para obter horário do Brasil (GMT-3)
def get_brazil_time():
    return datetime.now(timezone(timedelta(hours=-3)))

# Função para gerar variação senoidal com ruído
def generate_value(base, amplitude, phase, time_index, noise_level=0.1):
    """Gera valores com padrão senoidal + ruído aleatório."""
    sine_value = base + amplitude * math.sin(2 * math.pi * time_index / (READINGS_PER_HOUR * 4) + phase)
    noise = random.uniform(-noise_level, noise_level) * amplitude
    return round(sine_value + noise, 2)

def main():
    print("🔄 Gerando dados de teste para TempPi...")
    
    # Conectar ao banco
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Verificar se já existem dados
    cursor.execute("SELECT COUNT(*) FROM sensor_readings")
    existing_count = cursor.fetchone()[0]
    
    # Verificar se o modo forçado está ativado
    force = '-y' in sys.argv or '--yes' in sys.argv or '--force' in sys.argv
    
    if existing_count > 0 and not force:
        print(f"⚠️  Banco já contém {existing_count} registros.")
        print("💡 Use 'python3 generate_test_data.py -y' para adicionar sem confirmação")
        conn.close()
        return
    
    if existing_count > 0:
        print(f"⚠️  Banco já contém {existing_count} registros. Adicionando dados de teste...")
    
    # Calcular timestamps
    now = get_brazil_time()
    start_time = now - timedelta(hours=HOURS_TO_GENERATE)
    
    total_readings = HOURS_TO_GENERATE * READINGS_PER_HOUR
    print(f"📊 Gerando {total_readings} registros para cada sensor...")
    
    # Lista de sensores
    sensors = [
        {'name': 'Temp Forno', 'type': 'temperature', 'base': 200, 'amplitude': 30, 'phase': 0},
        {'name': 'Torre Nível 1', 'type': 'temperature', 'base': 100, 'amplitude': 15, 'phase': 0.5},
        {'name': 'Torre Nível 2', 'type': 'temperature', 'base': 95, 'amplitude': 12, 'phase': 0.7},
        {'name': 'Torre Nível 3', 'type': 'temperature', 'base': 90, 'amplitude': 10, 'phase': 0.9},
        {'name': 'Temp Tanque', 'type': 'temperature', 'base': 75, 'amplitude': 10, 'phase': 1.2},
        {'name': 'Temp Saída Gases', 'type': 'temperature', 'base': 250, 'amplitude': 40, 'phase': 0.3},
        {'name': 'Pressão Gases', 'type': 'pressure', 'base': 5, 'amplitude': 2, 'phase': 0.6},
        {'name': 'Velocidade', 'type': 'velocity', 'base': 2000, 'amplitude': 500, 'phase': 0.8}
    ]
    
    inserted = 0
    
    # Gerar dados
    for i in range(total_readings):
        # Calcular timestamp para este registro
        timestamp = start_time + timedelta(minutes=5 * i)
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        # Modo (alternar entre automático e manual ocasionalmente)
        mode = 0 if random.random() > 0.1 else 1
        
        # Inserir dados para cada sensor
        for sensor in sensors:
            temp_value = None
            pressure_value = None
            velocity_value = None
            
            # Gerar valor baseado no tipo
            value = generate_value(
                sensor['base'],
                sensor['amplitude'],
                sensor['phase'],
                i,
                noise_level=0.05
            )
            
            # Garantir valores positivos
            value = max(0, value)
            
            # Atribuir ao campo correto
            if sensor['type'] == 'temperature':
                temp_value = value
            elif sensor['type'] == 'pressure':
                pressure_value = value
            elif sensor['type'] == 'velocity':
                velocity_value = value
            
            # Inserir no banco
            cursor.execute('''
                INSERT INTO sensor_readings 
                (timestamp, sensor_name, sensor_type, temperature, pressure, velocity, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp_str,
                sensor['name'],
                sensor['type'],
                temp_value,
                pressure_value,
                velocity_value,
                mode
            ))
            
            inserted += 1
    
    # Commit e fechar
    conn.commit()
    conn.close()
    
    print(f"✅ {inserted} registros inseridos com sucesso!")
    print(f"📅 Período: {start_time.strftime('%d/%m/%Y %H:%M')} até {now.strftime('%d/%m/%Y %H:%M')}")
    print(f"🎯 Total de sensores: {len(sensors)}")
    print(f"📈 Leituras por sensor: {total_readings}")
    
    print("\n💡 Agora você pode:")
    print("   1. Executar 'python3 test_pdf_generation.py' para gerar o PDF")
    print("   2. Acessar http://localhost:3333/sensor/all para visualizar os dados")

if __name__ == '__main__':
    main()

