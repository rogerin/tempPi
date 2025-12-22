import sqlite3
import datetime

DATABASE_PATH = "sensor_data.db"

def configure_smtp():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
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
        
        # Check if config exists
        cursor.execute('SELECT COUNT(*) FROM smtp_config')
        count = cursor.fetchone()[0]
        
        smtp_host = "smtp.hostinger.com"
        smtp_port = 587
        smtp_user = "keyla@keycore.com.br"
        smtp_password = "R0ger!n20100"
        sender_email = "keyla@keycore.com.br"
        sender_name = "TempPi System"
        
        if count == 0:
            print("Configurando SMTP pela primeira vez...")
            cursor.execute('''
                INSERT INTO smtp_config 
                (smtp_host, smtp_port, smtp_user, smtp_password, sender_email, sender_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (smtp_host, smtp_port, smtp_user, smtp_password, sender_email, sender_name))
        else:
            print("Atualizando configuração SMTP existente...")
            cursor.execute('''
                UPDATE smtp_config 
                SET smtp_host=?, smtp_port=?, smtp_user=?, smtp_password=?, sender_email=?, sender_name=?, updated_at=CURRENT_TIMESTAMP
                WHERE id = (SELECT id FROM smtp_config ORDER BY id DESC LIMIT 1)
            ''', (smtp_host, smtp_port, smtp_user, smtp_password, sender_email, sender_name))
            
        conn.commit()
        conn.close()
        print("✅ Configuração SMTP aplicada com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao configurar SMTP: {e}")

if __name__ == "__main__":
    configure_smtp()
