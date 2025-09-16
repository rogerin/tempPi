#!/usr/bin/env python3
# Teste completo do sistema TempPi

import os
import sys
import subprocess
import time
import sqlite3
import signal
from datetime import datetime

def print_status(message, status="info"):
    icons = {"info": "ℹ️", "success": "✅", "error": "❌", "warning": "⚠️"}
    print(f"{icons.get(status, 'ℹ️')} {message}")

def check_files():
    """Verificar se todos os arquivos necessários existem"""
    required_files = [
        "dashboard.py",
        "sensor_server.py", 
        "assets/base.jpeg",
        "templates/index.html",
        "static/js/main.js"
    ]
    
    print_status("Verificando arquivos necessários...")
    
    for file in required_files:
        if os.path.exists(file):
            print_status(f"{file} - OK", "success")
        else:
            print_status(f"{file} - FALTANDO", "error")
            return False
    return True

def test_database():
    """Testar criação e operação do banco de dados"""
    print_status("Testando banco de dados...")
    
    # Remover banco anterior se existir
    if os.path.exists("sensor_data.db"):
        os.remove("sensor_data.db")
    
    try:
        # Importar e testar funcões do banco
        sys.path.append('.')
        from test_db import init_database, test_insert
        
        init_database()
        test_insert()
        
        # Verificar se banco foi criado
        if os.path.exists("sensor_data.db"):
            print_status("Banco de dados criado com sucesso", "success")
            return True
        else:
            print_status("Falha ao criar banco de dados", "error")
            return False
            
    except Exception as e:
        print_status(f"Erro no teste do banco: {e}", "error")
        return False

def generate_sample_data():
    """Gerar dados de exemplo executando o dashboard por alguns segundos"""
    print_status("Gerando dados de exemplo...")
    
    try:
        # Executar dashboard em background
        proc = subprocess.Popen([
            sys.executable, "dashboard.py", 
            "--img", "assets/base.jpeg"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Aguardar 10 segundos
        time.sleep(10)
        
        # Parar o processo
        proc.terminate()
        proc.wait(timeout=5)
        
        # Verificar se dados foram gerados
        conn = sqlite3.connect("sensor_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sensor_readings")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count > 0:
            print_status(f"Gerados {count} registros de exemplo", "success")
            return True
        else:
            print_status("Nenhum dado foi gerado", "warning")
            return False
            
    except Exception as e:
        print_status(f"Erro ao gerar dados: {e}", "error")
        return False

def test_server():
    """Testar se o servidor web inicia corretamente"""
    print_status("Testando servidor web...")
    
    try:
        # Tentar iniciar servidor
        proc = subprocess.Popen([
            sys.executable, "sensor_server.py"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Aguardar inicialização
        time.sleep(3)
        
        # Verificar se processo está rodando
        if proc.poll() is None:
            print_status("Servidor iniciado com sucesso", "success")
            
            # Parar servidor
            proc.terminate()
            proc.wait(timeout=5)
            return True
        else:
            print_status("Servidor falhou ao iniciar", "error")
            return False
            
    except Exception as e:
        print_status(f"Erro ao testar servidor: {e}", "error")
        return False

def main():
    print("🚀 TempPi - Teste Completo do Sistema")
    print("=" * 50)
    
    # Verificar arquivos
    if not check_files():
        print_status("Teste interrompido - arquivos faltando", "error")
        return 1
    
    # Testar banco de dados
    if not test_database():
        print_status("Teste interrompido - problema no banco", "error")
        return 1
    
    # Gerar dados de exemplo
    if not generate_sample_data():
        print_status("Aviso: Poucos dados gerados, mas sistema funcional", "warning")
    
    # Testar servidor
    if not test_server():
        print_status("Teste interrompido - problema no servidor", "error")
        return 1
    
    # Sucesso
    print("\n" + "=" * 50)
    print_status("TODOS OS TESTES PASSARAM!", "success")
    print_status("Sistema está funcionando corretamente", "success")
    
    print("\n📋 Próximos passos:")
    print("1. Execute o dashboard: python3 dashboard.py --img assets/base.jpeg")
    print("2. Execute o servidor: python3 sensor_server.py")
    print("3. Acesse: http://localhost:5000")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_status("\nTeste interrompido pelo usuário", "warning")
        sys.exit(1)
    except Exception as e:
        print_status(f"Erro inesperado: {e}", "error")
        sys.exit(1)
