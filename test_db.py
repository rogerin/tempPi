#!/usr/bin/env python3
# Teste do banco de dados SQLite

import sqlite3
import os
from datetime import datetime

DATABASE_PATH = "sensor_data.db"

def init_database():
    """Inicializa banco de dados SQLite para logging dos sensores"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Criar tabela de leituras dos sensores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sensor_name TEXT NOT NULL,
            temperature REAL,
            pressure REAL,
            velocity REAL,
            sensor_type TEXT NOT NULL,
            pins TEXT,
            mode TEXT DEFAULT 'simulation'
        )
    ''')
    
    # Índices para melhor performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_name ON sensor_readings(sensor_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_type ON sensor_readings(sensor_type)')
    
    conn.commit()
    conn.close()
    print(f"📊 Banco de dados inicializado: {DATABASE_PATH}")

def test_insert():
    """Testa inserção de dados"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Inserir dados de teste
    test_data = [
        ("Temp Forno", 350.5, None, None, "temperature", "(11, 9, 10)", "simulation"),
        ("Pressão Gases", None, 2.5, None, "pressure", "(2,)", "simulation"),
        ("Velocidade", None, None, 600, "velocity", None, "simulation"),
    ]
    
    for data in test_data:
        cursor.execute('''
            INSERT INTO sensor_readings 
            (sensor_name, temperature, pressure, velocity, sensor_type, pins, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', data)
    
    conn.commit()
    
    # Verificar dados inseridos
    cursor.execute("SELECT COUNT(*) FROM sensor_readings")
    count = cursor.fetchone()[0]
    print(f"📈 Registros inseridos: {count}")
    
    cursor.execute("SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT 3")
    rows = cursor.fetchall()
    print("📋 Últimos registros:")
    for row in rows:
        print(f"  - {row[2]}: {row[3] or row[4] or row[5]} ({row[6]})")
    
    conn.close()

if __name__ == "__main__":
    print("🧪 Testando banco de dados SQLite...")
    
    # Remover banco existente
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print("🗑️  Banco anterior removido")
    
    # Inicializar banco
    init_database()
    
    # Testar inserção
    test_insert()
    
    # Verificar arquivo
    if os.path.exists(DATABASE_PATH):
        size = os.path.getsize(DATABASE_PATH)
        print(f"✅ Banco criado com sucesso! Tamanho: {size} bytes")
    else:
        print("❌ Erro: banco não foi criado")
    
    print("🎉 Teste concluído!")
