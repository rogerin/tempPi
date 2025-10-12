#!/usr/bin/env python3
"""
Script de teste para o sensor de pressão ADS1115.
Testa a detecção I2C e leitura do sensor de pressão.

USO:
    python3 test_ads1115.py
"""

import sys
import time

# Cores ANSI para output bonito
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Backgrounds
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'

def check_i2c_enabled():
    """Verifica se o I2C está habilitado no sistema"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}🔍 VERIFICANDO STATUS DO I2C{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    
    # Verificar /boot/config.txt ou /boot/firmware/config.txt
    config_files = ['/boot/firmware/config.txt', '/boot/config.txt']
    i2c_config = None
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                config = f.read()
                if 'dtparam=i2c_arm=on' in config and not config.find('dtparam=i2c_arm=on') > config.find('#dtparam=i2c_arm=on'):
                    print(f"{Colors.GREEN}✅ I2C habilitado em {config_file}{Colors.RESET}")
                    i2c_config = True
                    break
                else:
                    print(f"{Colors.RED}❌ I2C NÃO habilitado em {config_file}{Colors.RESET}")
                    i2c_config = False
        except FileNotFoundError:
            print(f"{Colors.YELLOW}⚠️  Arquivo {config_file} não encontrado{Colors.RESET}")
            continue
    
    if i2c_config is None:
        print(f"{Colors.YELLOW}⚠️  Nenhum arquivo de configuração encontrado{Colors.RESET}")
    
    # Verificar módulos carregados
    try:
        with open('/proc/modules', 'r') as f:
            modules = f.read()
            if 'i2c_dev' in modules:
                print(f"{Colors.GREEN}✅ Módulo i2c_dev carregado{Colors.RESET}")
                i2c_module = True
            else:
                print(f"{Colors.RED}❌ Módulo i2c_dev NÃO carregado{Colors.RESET}")
                i2c_module = False
    except FileNotFoundError:
        print(f"{Colors.YELLOW}⚠️  Não foi possível verificar módulos{Colors.RESET}")
        i2c_module = None
    
    # Verificar dispositivos I2C
    import os
    i2c_devices = []
    for i in range(10):
        if os.path.exists(f'/dev/i2c-{i}'):
            i2c_devices.append(i)
    
    if i2c_devices:
        print(f"{Colors.GREEN}✅ Dispositivos I2C encontrados: {', '.join([f'/dev/i2c-{i}' for i in i2c_devices])}{Colors.RESET}")
    else:
        print(f"{Colors.RED}❌ Nenhum dispositivo I2C em /dev/{Colors.RESET}")
    
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    return i2c_config and i2c_module and len(i2c_devices) > 0

def test_i2c_detection():
    """Testa a detecção de dispositivos I2C com output detalhado"""
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}📡 ESCANEANDO BARRAMENTO I2C{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    try:
        import board
        import busio
        
        # Tentar criar barramento I2C
        print(f"{Colors.BLUE}🔌 Inicializando barramento I2C...{Colors.RESET}")
        i2c = busio.I2C(board.SCL, board.SDA)
        print(f"{Colors.GREEN}✅ Barramento I2C inicializado com sucesso{Colors.RESET}")
        
        # Fazer scan
        print(f"\n{Colors.BLUE}🔍 Escaneando endereços 0x00 a 0x7F...{Colors.RESET}\n")
        
        while not i2c.try_lock():
            pass
        
        devices = i2c.scan()
        i2c.unlock()
        
        if devices:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ DISPOSITIVOS I2C ENCONTRADOS: {len(devices)}{Colors.RESET}\n")
            
            # Mapeamento de endereços conhecidos
            known_devices = {
                0x48: "ADS1115 (ADC 16-bit)",
                0x49: "ADS1115 (ADC 16-bit) - Endereço alternativo",
                0x4A: "ADS1115 (ADC 16-bit) - Endereço alternativo",
                0x4B: "ADS1115 (ADC 16-bit) - Endereço alternativo",
                0x68: "MPU6050/DS1307 (IMU/RTC)",
                0x76: "BMP280/BME280 (Pressão/Temp/Umidade)",
                0x77: "BMP280/BME280 (Pressão/Temp/Umidade) - Alt",
                0x3C: "SSD1306 (Display OLED 128x64)",
                0x27: "LCD I2C",
                0x20: "PCF8574 (Expansor I/O)",
            }
            
            print(f"{Colors.CYAN}╔{'═'*58}╗{Colors.RESET}")
            print(f"{Colors.CYAN}║{Colors.BOLD} Endereço │ Hex  │ Dispositivo Identificado{' '*17}║{Colors.RESET}")
            print(f"{Colors.CYAN}╠{'═'*58}╣{Colors.RESET}")
            
            for addr in devices:
                hex_addr = f"0x{addr:02X}"
                dec_addr = f"{addr:3d}"
                device_name = known_devices.get(addr, "Dispositivo desconhecido")
                
                if addr in [0x48, 0x49, 0x4A, 0x4B]:
                    color = Colors.GREEN
                    icon = "🎯"
                else:
                    color = Colors.YELLOW
                    icon = "📍"
                
                print(f"{Colors.CYAN}║{color} {icon} {dec_addr}   │ {hex_addr} │ {device_name:<35}{Colors.CYAN}║{Colors.RESET}")
            
            print(f"{Colors.CYAN}╚{'═'*58}╝{Colors.RESET}\n")
            
            # Verificar se ADS1115 foi encontrado
            ads_found = any(addr in [0x48, 0x49, 0x4A, 0x4B] for addr in devices)
            if ads_found:
                print(f"{Colors.GREEN}{Colors.BOLD}🎯 ADS1115 DETECTADO!{Colors.RESET}")
                print(f"{Colors.GREEN}   Pronto para leitura do sensor de pressão.{Colors.RESET}\n")
            else:
                print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  ADS1115 NÃO DETECTADO{Colors.RESET}")
                print(f"{Colors.YELLOW}   Endereço esperado: 0x48 (ou 0x49, 0x4A, 0x4B){Colors.RESET}\n")
            
            return True
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ NENHUM DISPOSITIVO I2C DETECTADO{Colors.RESET}")
            print(f"{Colors.RED}   Verifique as conexões SDA (GPIO 2) e SCL (GPIO 3){Colors.RESET}\n")
            return False
            
    except ImportError as e:
        print(f"{Colors.RED}❌ Erro de importação: {e}{Colors.RESET}")
        print(f"{Colors.YELLOW}💡 Instale as dependências:{Colors.RESET}")
        print(f"   pip install adafruit-circuitpython-ads1x15 adafruit-blinka\n")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Erro ao escanear I2C: {e}{Colors.RESET}\n")
        return False

def test_ads1115_pressure():
    """Testa a leitura do sensor de pressão via ADS1115"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}🔍 TESTANDO SENSOR DE PRESSÃO ADS1115{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        # Configurar ADS1115
        print(f"{Colors.BLUE}🔌 Configurando ADS1115...{Colors.RESET}")
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=0x48)
        ads.gain = 1  # ±4.096V range
        
        # Canal A0
        channel = AnalogIn(ads, 0)  # Canal A0
        print(f"{Colors.GREEN}✅ ADS1115 configurado no canal A0{Colors.RESET}")
        
        print(f"\n{Colors.BLUE}📊 Fazendo 5 leituras do sensor...{Colors.RESET}")
        readings = []
        
        for i in range(5):
            voltage = channel.voltage
            # Sensor: 0.5V=0PSI, 4.5V=30PSI
            if voltage < 0.4:
                psi = 0.0
            else:
                psi = (voltage - 0.5) * 7.5  # 30/4.0 = 7.5
                
                # CALIBRAÇÃO: Fator de correção
                CALIBRATION_FACTOR = 1.553
                psi = psi * CALIBRATION_FACTOR
                psi = max(0.0, psi)
            
            readings.append((voltage, psi))
            print(f"  {Colors.YELLOW}Leitura {i+1}:{Colors.RESET} {voltage:.3f}V = {Colors.GREEN}{psi:.2f} PSI{Colors.RESET}")
            time.sleep(0.5)
        
        # Calcular média
        avg_voltage = sum(r[0] for r in readings) / len(readings)
        avg_psi = sum(r[1] for r in readings) / len(readings)
        
        print(f"\n{Colors.CYAN}📈 RESULTADOS:{Colors.RESET}")
        print(f"   {Colors.BOLD}Tensão média:{Colors.RESET} {avg_voltage:.3f}V")
        print(f"   {Colors.BOLD}Pressão média:{Colors.RESET} {avg_psi:.2f} PSI")
        
        # Validar se está dentro do range esperado
        if 0.4 <= avg_voltage <= 4.6:  # Margem de erro
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ SENSOR FUNCIONANDO CORRETAMENTE!{Colors.RESET}")
            return True
        else:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  TENSÃO FORA DO RANGE ESPERADO{Colors.RESET}")
            print(f"{Colors.YELLOW}   Range esperado: 0.5-4.5V{Colors.RESET}")
            return False
            
    except ImportError as e:
        print(f"{Colors.RED}❌ Erro de importação: {e}{Colors.RESET}")
        print(f"{Colors.YELLOW}💡 Instale as dependências:{Colors.RESET}")
        print(f"   pip install adafruit-circuitpython-ads1x15 adafruit-blinka")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ Erro ao ler sensor: {e}{Colors.RESET}")
        return False

def scan_all_ads1115_channels(i2c_address=0x48):
    """Escaneia todos os 4 canais analógicos do ADS1115"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}📊 ESCANEANDO TODOS OS CANAIS ANALÓGICOS{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        # Configurar ADS1115
        print(f"{Colors.BLUE}🔌 Configurando ADS1115 (endereço 0x{i2c_address:02X})...{Colors.RESET}")
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=i2c_address)
        ads.gain = 1  # ±4.096V range
        print(f"{Colors.GREEN}✅ ADS1115 configurado{Colors.RESET}\n")
        
        # Mapear canais para pinos
        channels = {
            'A0': 0,
            'A1': 1,
            'A2': 2,
            'A3': 3,
        }
        
        print(f"{Colors.BLUE}🔍 Lendo todos os canais analógicos...{Colors.RESET}\n")
        
        active_channels = []
        
        # Criar tabela de resultados
        print(f"{Colors.CYAN}╔{'═'*58}╗{Colors.RESET}")
        print(f"{Colors.CYAN}║{Colors.BOLD} Canal │ Tensão   │ Pressão  │ Status{' '*20}║{Colors.RESET}")
        print(f"{Colors.CYAN}╠{'═'*58}╣{Colors.RESET}")
        
        for channel_name, channel_pin in channels.items():
            try:
                channel = AnalogIn(ads, channel_pin)
                voltage = channel.voltage
                
                # Calcular pressão (0.5V=0PSI, 4.5V=30PSI)
                if voltage < 0.4:
                    psi = 0.0
                    status = f"{Colors.YELLOW}Sem sensor / Desconectado{Colors.RESET}"
                    icon = "⚪"
                    color = Colors.YELLOW
                elif 0.4 <= voltage <= 4.6:
                    psi = (voltage - 0.5) * 7.5  # 30/4.0 = 7.5
                    psi = max(0.0, psi)
                    status = f"{Colors.GREEN}Sensor conectado{Colors.RESET}"
                    icon = "🟢"
                    color = Colors.GREEN
                    active_channels.append((channel_name, voltage, psi))
                else:
                    psi = 0.0
                    status = f"{Colors.RED}Fora do range{Colors.RESET}"
                    icon = "🔴"
                    color = Colors.RED
                
                # Formatar linha da tabela
                voltage_str = f"{voltage:.3f}V"
                psi_str = f"{psi:.2f} PSI" if psi > 0 else "  -  "
                
                print(f"{Colors.CYAN}║{color} {icon} {channel_name}  │ {voltage_str:<8} │ {psi_str:<8} │ {status}{' ' * (26 - len(channel_name))}{Colors.CYAN}║{Colors.RESET}")
                
            except Exception as e:
                print(f"{Colors.CYAN}║{Colors.RED} ❌ {channel_name}  │ ERRO     │   -      │ Erro na leitura: {str(e)[:15]:<15}{Colors.CYAN}║{Colors.RESET}")
        
        print(f"{Colors.CYAN}╚{'═'*58}╝{Colors.RESET}\n")
        
        # Resumo
        if active_channels:
            print(f"{Colors.GREEN}{Colors.BOLD}✅ CANAIS ATIVOS ENCONTRADOS: {len(active_channels)}{Colors.RESET}")
            for ch_name, ch_voltage, ch_psi in active_channels:
                print(f"{Colors.GREEN}   • {ch_name}: {ch_voltage:.3f}V = {ch_psi:.2f} PSI{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  NENHUM SENSOR ATIVO DETECTADO{Colors.RESET}")
            print(f"{Colors.YELLOW}   Conecte sensores nos canais A0-A3{Colors.RESET}")
        
        return active_channels
        
    except ImportError as e:
        print(f"{Colors.RED}❌ Erro de importação: {e}{Colors.RESET}")
        print(f"{Colors.YELLOW}💡 Instale as dependências:{Colors.RESET}")
        print(f"   pip install adafruit-circuitpython-ads1x15 adafruit-blinka\n")
        return []
    except Exception as e:
        print(f"{Colors.RED}❌ Erro ao escanear canais: {e}{Colors.RESET}\n")
        return []

def test_ads1115_pressure_detailed(channel_name='A0'):
    """Testa a leitura detalhada do sensor de pressão em um canal específico"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}🔍 TESTE DETALHADO - CANAL {channel_name}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1115 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn
        
        # Mapear nome do canal para pino
        channel_map = {
            'A0': 0,
            'A1': 1,
            'A2': 2,
            'A3': 3,
        }
        
        if channel_name not in channel_map:
            print(f"{Colors.RED}❌ Canal inválido: {channel_name}{Colors.RESET}")
            return False
        
        # Configurar ADS1115
        print(f"{Colors.BLUE}🔌 Configurando ADS1115...{Colors.RESET}")
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c, address=0x48)
        ads.gain = 1  # ±4.096V range
        
        # Canal especificado
        channel = AnalogIn(ads, channel_map[channel_name])
        print(f"{Colors.GREEN}✅ ADS1115 configurado no canal {channel_name}{Colors.RESET}")
        
        print(f"\n{Colors.BLUE}📊 Fazendo 5 leituras do sensor no canal {channel_name}...{Colors.RESET}")
        readings = []
        
        for i in range(5):
            voltage = channel.voltage
            # Sensor: 0.5V=0PSI, 4.5V=30PSI
            if voltage < 0.4:
                psi = 0.0
            else:
                psi = (voltage - 0.5) * 7.5  # 30/4.0 = 7.5
                
                # CALIBRAÇÃO: Fator de correção
                CALIBRATION_FACTOR = 1.553
                psi = psi * CALIBRATION_FACTOR
                psi = max(0.0, psi)
            
            readings.append((voltage, psi))
            print(f"  {Colors.YELLOW}Leitura {i+1}:{Colors.RESET} {voltage:.3f}V = {Colors.GREEN}{psi:.2f} PSI{Colors.RESET}")
            time.sleep(0.5)
        
        # Calcular média
        avg_voltage = sum(r[0] for r in readings) / len(readings)
        avg_psi = sum(r[1] for r in readings) / len(readings)
        
        print(f"\n{Colors.CYAN}📈 RESULTADOS:{Colors.RESET}")
        print(f"   {Colors.BOLD}Tensão média:{Colors.RESET} {avg_voltage:.3f}V")
        print(f"   {Colors.BOLD}Pressão média:{Colors.RESET} {avg_psi:.2f} PSI")
        
        # Validar se está dentro do range esperado
        if 0.4 <= avg_voltage <= 4.6:  # Margem de erro
            print(f"\n{Colors.GREEN}{Colors.BOLD}✅ SENSOR FUNCIONANDO CORRETAMENTE!{Colors.RESET}")
            return True
        else:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  TENSÃO FORA DO RANGE ESPERADO{Colors.RESET}")
            print(f"{Colors.YELLOW}   Range esperado: 0.5-4.5V{Colors.RESET}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ Erro ao ler sensor: {e}{Colors.RESET}")
        return False

def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}🧪 TESTE DO SENSOR DE PRESSÃO ADS1115{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    
    print(f"\n{Colors.CYAN}📋 Configuração esperada:{Colors.RESET}")
    print(f"   • ADS1115 no endereço I2C 0x48")
    print(f"   • Sensor conectado no canal A0")
    print(f"   • SDA: GPIO 2, SCL: GPIO 3")
    print(f"   • Sensor: 0-30 PSI, saída 0.5-4.5V")
    
    # Verificar se I2C está habilitado
    i2c_enabled = check_i2c_enabled()
    
    if not i2c_enabled:
        print(f"\n{Colors.RED}{Colors.BOLD}⚠️  ATENÇÃO: I2C pode não estar configurado corretamente{Colors.RESET}")
        print(f"{Colors.YELLOW}   Execute: sudo raspi-config{Colors.RESET}")
        print(f"{Colors.YELLOW}   Navegue: Interface Options -> I2C -> Enable{Colors.RESET}\n")
    
    # Escanear dispositivos I2C
    i2c_ok = test_i2c_detection()
    
    if not i2c_ok:
        print(f"\n{Colors.RED}{'='*60}{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}❌ TESTE FALHOU - I2C não detectado{Colors.RESET}")
        print(f"{Colors.RED}{'='*60}{Colors.RESET}\n")
        return
    
    # NOVO: Escanear todos os canais analógicos
    active_channels = scan_all_ads1115_channels()
    
    # Se houver canais ativos, fazer teste detalhado do primeiro canal ativo
    if active_channels:
        # Pegar o primeiro canal ativo
        first_channel = active_channels[0][0]  # Nome do canal (A0, A1, etc)
        
        print(f"\n{Colors.BLUE}{'─'*60}{Colors.RESET}")
        print(f"{Colors.BLUE}📋 Fazendo teste detalhado do canal {first_channel}...{Colors.RESET}")
        print(f"{Colors.BLUE}{'─'*60}{Colors.RESET}")
        
        # Teste detalhado no primeiro canal ativo
        sensor_ok = test_ads1115_pressure_detailed(first_channel)
    else:
        print(f"\n{Colors.YELLOW}⚠️  Nenhum sensor ativo para teste detalhado{Colors.RESET}")
        sensor_ok = False
    
    # Resultado final
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    if active_channels and sensor_ok:
        print(f"{Colors.GREEN}{Colors.BOLD}✅ TESTE CONCLUÍDO COM SUCESSO!{Colors.RESET}")
        print(f"{Colors.GREEN}   {len(active_channels)} sensor(es) de pressão funcionando corretamente.{Colors.RESET}")
    elif active_channels:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  TESTE PARCIALMENTE BEM-SUCEDIDO{Colors.RESET}")
        print(f"{Colors.YELLOW}   Sensores detectados mas com leituras inconsistentes.{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}❌ TESTE FALHOU!{Colors.RESET}")
        print(f"{Colors.RED}   Nenhum sensor detectado. Verifique as conexões.{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
