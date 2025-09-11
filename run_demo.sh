#!/bin/bash
# Script de demonstração do TempPi Dashboard

echo "🚀 TempPi Dashboard - Demonstração"
echo "=================================="
echo ""

# Verificar se os arquivos existem
if [ ! -f "dashboard.py" ]; then
    echo "❌ Arquivo dashboard.py não encontrado!"
    exit 1
fi

if [ ! -f "sensor_server.py" ]; then
    echo "❌ Arquivo sensor_server.py não encontrado!"
    exit 1
fi

if [ ! -f "assets/base.jpeg" ]; then
    echo "❌ Arquivo assets/base.jpeg não encontrado!"
    echo "   Coloque sua imagem de fundo em assets/base.jpeg"
    exit 1
fi

echo "📊 Iniciando dashboard em modo simulação para gerar dados..."
echo "   (O dashboard será executado por 30 segundos para criar dados de exemplo)"
echo ""

# Executar dashboard em background por 30 segundos
timeout 30 python3 dashboard.py --img assets/base.jpeg 2>/dev/null &
DASHBOARD_PID=$!

echo "⏳ Gerando dados de exemplo... (30 segundos)"
sleep 30

# Verificar se o banco foi criado
if [ -f "sensor_data.db" ]; then
    echo "✅ Banco de dados criado com sucesso!"
    
    # Contar registros
    RECORDS=$(sqlite3 sensor_data.db "SELECT COUNT(*) FROM sensor_readings;")
    echo "📈 Registros gerados: $RECORDS"
    
    echo ""
    echo "🌐 Iniciando servidor web..."
    echo "   Acesse: http://localhost:5000"
    echo "   Pressione Ctrl+C para parar"
    echo ""
    
    # Iniciar servidor web
    python3 sensor_server.py
else
    echo "❌ Erro: Banco de dados não foi criado"
    exit 1
fi
