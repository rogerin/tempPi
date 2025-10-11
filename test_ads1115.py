#!/usr/bin/env python3
"""
Script de teste para o sensor de pressão ADS1115.
Testa a detecção I2C e leitura do sensor de pressão.

USO:
    python3 test_ads1115.py
"""

import sys
import time

def test_i2c_detection():
    """Testa a detecção de dispositivos I2C"""
    print("🔍 Testando detecção I2C...")
    
    try:
        import board
        import busio
        
        i2c = busio.I2C(board.SCL, board.SDA)
        while not i2c.try_lock():
            pass
        devices = i2c.scan()
        i2c.unlock()
        
        if devices:
            print(f"✅ Dispositivos I2C encontrados: {[hex(device) for device in devices]}")
            return True
        else:
            print("⚠️  Nenhum dispositivo I2C detectado")
            return False
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("💡 Instale as dependências:")
        print("   pip install adafruit-circuitpython-ads1x15 adafruit-blinka")
        return False
    except Exception as e:
        print(f"❌ Erro ao escanear I2C: {e}")
        return False

def test_ads1115_pressure():
    """Testa a leitura do sensor de pressão via ADS1115"""
    print("\n🔍 Testando sensor de pressão ADS1115...")
    
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        # Configurar ADS1115
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=0x48)
        ads.gain = 1  # ±4.096V range
        
        # Canal A0
        channel = AnalogIn(ads, ADS.P0)
        
        print("📊 Fazendo 5 leituras do sensor...")
        readings = []
        
        for i in range(5):
            voltage = channel.voltage
            # Sensor: 0.5V=0PSI, 4.5V=30PSI
            if voltage < 0.4:
                psi = 0.0
            else:
                psi = (voltage - 0.5) * 7.5  # 30/4.0 = 7.5
                psi = max(0.0, psi)
            
            readings.append((voltage, psi))
            print(f"  Leitura {i+1}: {voltage:.3f}V = {psi:.2f} PSI")
            time.sleep(0.5)
        
        # Calcular média
        avg_voltage = sum(r[0] for r in readings) / len(readings)
        avg_psi = sum(r[1] for r in readings) / len(readings)
        
        print(f"\n📈 Resultados:")
        print(f"   Tensão média: {avg_voltage:.3f}V")
        print(f"   Pressão média: {avg_psi:.2f} PSI")
        
        # Validar se está dentro do range esperado
        if 0.4 <= avg_voltage <= 4.6:  # Margem de erro
            print("✅ Sensor funcionando corretamente!")
            return True
        else:
            print("⚠️  Tensão fora do range esperado (0.5-4.5V)")
            return False
            
    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        print("💡 Instale as dependências:")
        print("   pip install adafruit-circuitpython-ads1x15 adafruit-blinka")
        return False
    except Exception as e:
        print(f"❌ Erro ao ler sensor: {e}")
        return False

def main():
    print("="*60)
    print("🧪 TESTE DO SENSOR DE PRESSÃO ADS1115")
    print("="*60)
    print("📋 Configuração esperada:")
    print("   - ADS1115 no endereço I2C 0x48")
    print("   - Sensor conectado no canal A0")
    print("   - SDA: GPIO 2, SCL: GPIO 3")
    print("   - Sensor: 0-30 PSI, saída 0.5-4.5V")
    print("="*60)
    
    # Teste 1: Detecção I2C
    i2c_ok = test_i2c_detection()
    
    if not i2c_ok:
        print("\n❌ Falha na detecção I2C - verifique as conexões")
        return
    
    # Teste 2: Leitura do sensor
    sensor_ok = test_ads1115_pressure()
    
    print("\n" + "="*60)
    if sensor_ok:
        print("✅ TESTE CONCLUÍDO COM SUCESSO!")
        print("   O sensor de pressão está funcionando corretamente.")
    else:
        print("❌ TESTE FALHOU!")
        print("   Verifique as conexões e configurações.")
    print("="*60)

if __name__ == "__main__":
    main()
