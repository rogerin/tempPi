#!/usr/bin/env python3
"""
Script para testar a geração de PDF do TempPi.
Faz requisição para a API e salva o PDF gerado.
"""

import requests
import json
from datetime import datetime
import os

# Configurações
API_URL = 'http://localhost:3333/api/reports/generate-pdf'
OUTPUT_FILE = 'test_report.pdf'

def main():
    print("📄 Gerando relatório PDF de teste...")
    
    # Verificar se o servidor está rodando
    try:
        response = requests.get('http://localhost:3333/api/health', timeout=2)
    except requests.exceptions.RequestException:
        print("❌ Erro: Servidor não está rodando!")
        print("💡 Inicie o servidor com: python3 sensor_server.py")
        return
    
    # Payload com todos os sensores e últimas 24h
    payload = {
        'timeRange': '24',
        'groupBy': 'none',
        'selectedSensors': [
            'temp_forno',
            'torre_nivel_1',
            'torre_nivel_2',
            'torre_nivel_3',
            'temp_tanque',
            'temp_gases',
            'pressao_gases',
            'velocity'
        ],
        'pressureUnit': 'psi'
    }
    
    print(f"📊 Parâmetros:")
    print(f"   - Período: Últimas 24 horas")
    print(f"   - Sensores: {len(payload['selectedSensors'])} sensores")
    print(f"   - Agrupamento: Sem agrupamento")
    
    try:
        # Fazer requisição
        print("\n🔄 Enviando requisição para API...")
        response = requests.post(
            API_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # Verificar resposta
        if response.status_code == 200:
            # Salvar PDF
            with open(OUTPUT_FILE, 'wb') as f:
                f.write(response.content)
            
            # Obter tamanho do arquivo
            file_size = os.path.getsize(OUTPUT_FILE)
            file_size_kb = file_size / 1024
            
            print(f"\n✅ PDF gerado com sucesso!")
            print(f"📁 Arquivo: {os.path.abspath(OUTPUT_FILE)}")
            print(f"📏 Tamanho: {file_size_kb:.2f} KB")
            print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            
            print("\n💡 Para abrir o PDF:")
            print(f"   macOS: open {OUTPUT_FILE}")
            print(f"   Linux: xdg-open {OUTPUT_FILE}")
            print(f"   Windows: start {OUTPUT_FILE}")
            
        elif response.status_code == 400:
            error_data = response.json()
            print(f"\n❌ Erro: {error_data.get('error', 'Requisição inválida')}")
            print("💡 Verifique se há dados no banco de dados.")
            print("   Execute: python3 generate_test_data.py")
            
        else:
            print(f"\n❌ Erro HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Mensagem: {error_data.get('error', 'Erro desconhecido')}")
            except:
                print(f"   Resposta: {response.text[:200]}")
    
    except requests.exceptions.Timeout:
        print("\n❌ Timeout: O servidor demorou muito para responder.")
        print("💡 O PDF pode estar sendo gerado. Aguarde alguns segundos e tente novamente.")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Erro de conexão com o servidor.")
        print("💡 Verifique se o servidor está rodando em http://localhost:3333")
    
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")

if __name__ == '__main__':
    main()

