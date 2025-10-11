# dashboard.py
# Painel com overlay sobre imagem, controle por teclado (sem depender de sliders),
# min/max com efeito visual, saída limpa (ESC/Ctrl+C) e gráficos OpenCV (sem Matplotlib).
# Integrado com servidor WebSocket para controle e visualização remota.

import cv2, numpy as np, random, argparse, time, math, warnings, signal, sqlite3, os
from datetime import datetime
import socketio
import json
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ============= 1) ARGUMENTOS DE LINHA DE COMANDO =============
ap = argparse.ArgumentParser(description="Dashboard de controle para sistema de destilação")
ap.add_argument("--img", required=True, help="Caminho da imagem de fundo.")
ap.add_argument("--scale", type=float, default=1.0, help="Escala da janela (ex.: 1.0).")
ap.add_argument("--use-rpi", action="store_true", help="Ativar modo Raspberry Pi (GPIO/MAX6675).")
ap.add_argument("--skip-test", action="store_true", help="Pula a rotina de teste ao iniciar")

# Argumentos para sensores de temperatura (3 pinos cada: SCK, CS, SO)
ap.add_argument("--thermo-torre1", nargs=3, type=int, default=[25, 24, 18], 
                metavar=('SCK', 'CS', 'SO'), help="Pinos GPIO para sensor temperatura Torre Nível 1 (padrão: 25 24 18)")
ap.add_argument("--thermo-torre2", nargs=3, type=int, default=[7, 8, 23], 
                metavar=('SCK', 'CS', 'SO'), help="Pinos GPIO para sensor temperatura Torre Nível 2 (padrão: 7 8 23)")
ap.add_argument("--thermo-torre3", nargs=3, type=int, default=[21, 20, 16], 
                metavar=('SCK', 'CS', 'SO'), help="Pinos GPIO para sensor temperatura Torre Nível 3 (padrão: 21 20 16)")
ap.add_argument("--thermo-tanque", nargs=3, type=int, default=[4, 6, 5],
                metavar=('SCK', 'CS', 'SO'), help="Pinos GPIO para sensor temperatura Tanque (padrão: 4 3 2)")
ap.add_argument("--thermo-gases", nargs=3, type=int, default=[22, 27, 17], 
                metavar=('SCK', 'CS', 'SO'), help="Pinos GPIO para sensor temperatura Saída Gases (padrão: 22 27 17)")
ap.add_argument("--thermo-forno", nargs=3, type=int, default=[11, 9, 10], 
                metavar=('SCK', 'CS', 'SO'), help="Pinos GPIO para sensor temperatura Forno (padrão: 11 9 10)")

# Argumentos para sensores de pressão
ap.add_argument("--pressao1-pin", type=int, default=2, help="Pino GPIO para Sensor Transdutor de Pressão 1 (padrão: 2)")
ap.add_argument("--pressao2-pin", type=int, default=3, help="Pino GPIO para Sensor Transdutor de Pressão 2 (padrão: 3)")

# Argumentos para controles/atuadores
ap.add_argument("--ventilador-pin", type=int, default=14, help="Pino GPIO para controle do Ventilador (padrão: 14)")
ap.add_argument("--resistencia-pin", type=int, default=26, help="Pino GPIO para controle da Resistência (padrão: 26)")
ap.add_argument("--motor-rosca-pin", type=int, default=12, help="Pino GPIO para Motor Rosca Alimentação (padrão: 12)")
ap.add_argument("--tambor-dir-pin", type=int, default=13, help="Pino GPIO para DIR+ Driver Motor Tambor (padrão: 13)")
ap.add_argument("--tambor-pul-pin", type=int, default=19, help="Pino GPIO para PUL+ Driver Motor Tambor (padrão: 19)")

args = ap.parse_args()
USE_RPI = args.use_rpi

# ============= 2) CONFIGURAÇÕES GLOBAIS =============
# Pinagens (BCM) - Configuráveis via argumentos
THERMO_TORRE_1 = tuple(args.thermo_torre1)
THERMO_TORRE_2 = tuple(args.thermo_torre2)
THERMO_TORRE_3 = tuple(args.thermo_torre3)
THERMO_TANQUE  = tuple(args.thermo_tanque)
THERMO_GASES   = tuple(args.thermo_gases)
THERMO_FORNO   = tuple(args.thermo_forno)
PRESSAO_1_PIN = args.pressao1_pin
PRESSAO_2_PIN = args.pressao2_pin
PIN_VENTILADOR = args.ventilador_pin
PIN_RESISTENCIA = args.resistencia_pin
PIN_MOTOR_ROSCA = args.motor_rosca_pin
PIN_TAMBOR_DIR  = args.tambor_dir_pin
PIN_TAMBOR_PUL  = args.tambor_pul_pin

# UI / Campos
FIELD_NAMES = [
    "Temp Forno", "Velocidade", "Temp Tanque", "Temp Saída Gases",
    "Pressão Gases", "Torre Nível 1", "Torre Nível 2", "Torre Nível 3",
]
POSITIONS_NORM = {
    "Temp Forno":        (0.44, 0.42), "Velocidade":        (0.44, 0.57),
    "Temp Tanque":       (0.44, 0.77), "Temp Saída Gases":  (0.217, 0.53),
    "Pressão Gases":     (0.217, 0.59), "Torre Nível 1":     (0.75, 0.77),
    "Torre Nível 2":     (0.75, 0.56), "Torre Nível 3":     (0.75, 0.38),
}
FONT = cv2.FONT_HERSHEY_SIMPLEX
BASE_FONT_SCALE = 0.8
BASE_THICKNESS = 2
TEXT_COLOR = (0, 0, 0)
OUTLINE = True
OUTLINE_THICKNESS = 3

# Estado global do sistema
state = {
    'settings': {
        'velocidade_tambor': 1000,  # Hz (pulsos por segundo)
    }, 
    'values': {},
    'actuators': {
        'ventilador': False, 'resistencia': False, 'motor_rosca': False,
        'tambor_dir': False, 'tambor_pul': False
    },
    'timers': {'resistencia_start_time': None, 'rosca_cycle_start': None}
}

# ============= 3) CLIENTE WEBSOCKET =============
sio = socketio.Client()

@sio.event(namespace='/dashboard')
def connect():
    print("Conectado ao servidor WebSocket.")
    sio.emit('request_full_update', namespace='/dashboard')

@sio.event(namespace='/dashboard')
def disconnect():
    print("Desconectado do servidor WebSocket.")

@sio.on('command_from_server', namespace='/dashboard')
def handle_command(data):
    global state
    print(f"Comando recebido: {data}")
    command = data.get('command')
    payload = data.get('payload')

    if command == 'SET_SETTING':
        state['settings'][payload['name']] = payload['value']
        save_settings(state['settings']) # Persiste a configuração

    elif command == 'MANUAL_CONTROL':
        if state['settings'].get('system_mode', 0) == 1: # Apenas em Modo Manual
            target = payload.get('target')
            if target in state['actuators']:
                state['actuators'][target] = bool(payload.get('state'))
                print(f"MANUAL: {target} = {payload.get('state')}")
            else:
                print(f"ERRO: Target '{target}' não encontrado em actuators!")

@sio.on('request_full_update', namespace='/dashboard')
def send_full_update():
    sio.emit('dashboard_update', state, namespace='/dashboard')

# ============= 4) BANCO DE DADOS e CONFIGURAÇÕES =============
DATABASE_PATH = "sensor_data.db"
SETTINGS_PATH = "settings.json"

def init_database():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, sensor_name TEXT NOT NULL,
            temperature REAL, pressure REAL, velocity REAL,
            sensor_type TEXT NOT NULL, pins TEXT, mode TEXT DEFAULT 'simulation'
        )
    ''')
    conn.commit()
    conn.close()
    print(f"📊 Banco de dados inicializado: {DATABASE_PATH}")

def log_sensor_reading(sensor_name, value, sensor_type, pins=None, mode="simulation"):
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        temperature, pressure, velocity = None, None, None
        if sensor_type == "temperature": temperature = value
        elif sensor_type == "pressure": pressure = value
        elif sensor_type == "velocity": velocity = value
        
        cursor.execute('''
            INSERT INTO sensor_readings (sensor_name, temperature, pressure, velocity, sensor_type, pins, mode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (sensor_name, temperature, pressure, velocity, sensor_type, str(pins) if pins else None, mode))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"❌ Erro ao salvar no banco: {e}")

def save_settings(settings_dict):
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings_dict, f, indent=4)

def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, 'r') as f:
            return json.load(f)
    else: # Valores padrão se o arquivo não existir
        return {
            # Modo e aquecimento
            "system_mode": 0,              # 0=auto, 1=manual
            "heating_status": 0,           # 0=desligado, 1=ligado
            # Setpoints de temperatura (mín/max)
            "temp_forno_min": 60, "temp_forno_max": 100,
            "temp_torre1_min": 80,  "temp_torre1_max": 200,
            "temp_torre2_min": 80,  "temp_torre2_max": 220,
            "temp_torre3_min": 80,  "temp_torre3_max": 240,
            "temp_tanque_min": 50,  "temp_tanque_max": 150,
            "temp_gases_min": 50,   "temp_gases_max": 300,
            # Pressão de linha
            "pressao_linha_min": 0.5, "pressao_linha_max": 3.0,
            # Tempos (segundos)
            "tempo_acionamento_resistencia": 10,
            "tempo_acionamento_rosca": 5,
            "tempo_pausa_rosca": 10,
            # Velocidade tambor (Hz)
            "velocidade_tambor": 1000,
        }

def list_i2c_devices():
    """Lista todos os dispositivos I2C conectados"""
    if not USE_RPI:
        return []
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        while not i2c.try_lock():
            pass
        devices = i2c.scan()
        i2c.unlock()
        return [hex(device) for device in devices]
    except Exception as e:
        print(f"❌ Erro ao escanear I2C: {e}")
        return []

class PressureSensorADS1115:
    """Lê sensor de pressão via ADS1115 no canal A0"""
    
    def __init__(self, channel=0, i2c_address=0x48):
        """
        Inicializa o sensor de pressão no ADS1115
        - Sensor: 0-30 PSI com saída 0.5-4.5V
        - Level shifter: 5V->3.3V
        - Ganho: ±4.096V (GAIN=1)
        """
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c, address=i2c_address)
        self.ads.gain = 1  # ±4.096V range
        
        if channel == 0:
            self.channel = AnalogIn(self.ads, ADS.P0)
        elif channel == 1:
            self.channel = AnalogIn(self.ads, ADS.P1)
        else:
            raise ValueError("Canal inválido (use 0-3)")
    
    def read_pressure_psi(self):
        """Lê pressão em PSI"""
        try:
            voltage = self.channel.voltage
            # Sensor: 0.5V=0PSI, 4.5V=30PSI
            # Fórmula: PSI = (V - 0.5) * (30 / 4.0)
            if voltage < 0.4:  # Abaixo do mínimo esperado
                return 0.0
            psi = (voltage - 0.5) * 7.5  # 30/4.0 = 7.5
            return max(0.0, round(psi, 2))
        except Exception as e:
            raise Exception(f"Erro ao ler pressão: {e}")

def validate_sensors():
    """
    Valida se os sensores estão conectados e funcionando.
    Retorna True se pelo menos um sensor está funcionando.
    """
    global _sensor_status, _sensors_validated
    
    if not (USE_RPI and _rpi_ready):
        print("⚠️  Modo simulação - sensores não validados")
        _sensors_validated = False
        return False
    
    print("\n" + "="*70)
    print("🔍 VALIDANDO SENSORES")
    print("="*70)
    
    working_sensors = 0
    failed_sensors = []
    
    # Mapear sensor_name para chave do thermo_sensors dict
    sensors_to_test = [
        ('Temp Torre 1', 'Torre Nível 1'),
        ('Temp Torre 2', 'Torre Nível 2'),
        ('Temp Torre 3', 'Torre Nível 3'),
        ('Temp Tanque', 'Temp Tanque'),
        ('Temp Gases', 'Temp Saída Gases'),
        ('Temp Forno', 'Temp Forno'),
        ('Pressão 1', None),  # Sensor de pressão via ADS1115
    ]
    
    for sensor_name, thermo_key in sensors_to_test:
        success = False
        
        # Sensor de pressão - lógica diferente
        if sensor_name == 'Pressão 1':
            if pressure_sensor is None:
                print(f"  ❌ {sensor_name}: Sensor não inicializado")
                _sensor_status[sensor_name] = False
                failed_sensors.append(sensor_name)
                continue
            
            for attempt in range(3):
                try:
                    value = pressure_sensor.read_pressure_psi()
                    if value is not None and 0 <= value <= 50:
                        _sensor_status[sensor_name] = True
                        working_sensors += 1
                        success = True
                        print(f"  ✅ {sensor_name}: {value:.2f} PSI - OK")
                        break
                except Exception as e:
                    if attempt == 2:
                        print(f"  ❌ {sensor_name}: FALHA - {e}")
                        failed_sensors.append(sensor_name)
                time.sleep(0.1)
            
            if not success:
                _sensor_status[sensor_name] = False
            continue
        
        # Verificar se sensor foi inicializado
        if thermo_key not in thermo_sensors:
            print(f"  ❌ {sensor_name}: Sensor não inicializado")
            _sensor_status[sensor_name] = False
            failed_sensors.append(sensor_name)
            continue
        
        # Testar sensor (3 tentativas)
        for attempt in range(3):
            try:
                value = thermo_sensors[thermo_key].readTempC()
                
                # Validar se é um valor real (não None, não NaN, dentro de limites)
                if value is not None and not math.isnan(value) and -50 < value < 1500:
                    _sensor_status[sensor_name] = True
                    working_sensors += 1
                    success = True
                    print(f"  ✅ {sensor_name}: {value:.1f}°C - OK")
                    break
                else:
                    if attempt == 2:
                        print(f"  ❌ {sensor_name}: Leitura inválida ({value}°C)")
            except Exception as e:
                if attempt == 2:  # Última tentativa
                    print(f"  ❌ {sensor_name}: FALHA - {e}")
                    failed_sensors.append(sensor_name)
            time.sleep(0.1)
        
        if not success:
            _sensor_status[sensor_name] = False
    
    print("="*70)
    print(f"📊 Resultado: {working_sensors}/{len(sensors_to_test)} sensores funcionando")
    
    if working_sensors == 0:
        print("❌ ERRO CRÍTICO: Nenhum sensor funcionando!")
        _sensors_validated = False
        return False
    elif failed_sensors:
        print(f"⚠️  AVISO: {len(failed_sensors)} sensor(es) com falha")
        _sensors_validated = True
        return True
    else:
        print("✅ TODOS OS SENSORES FUNCIONANDO PERFEITAMENTE!")
        _sensors_validated = True
        return True

# ============= 5) FLAGS e SAÍDA LIMPA =============
STOP  = False
def _sigint_handler(sig, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGINT, _sigint_handler)

# ============= 6) RPi opcional (fallback) =============
_rpi_ready = False
_hardware_init_success = False
_sensors_validated = False

# Estado de cada sensor
_sensor_status = {
    'Temp Torre 1': False,
    'Temp Torre 2': False,
    'Temp Torre 3': False,
    'Temp Tanque': False,
    'Temp Gases': False,
    'Temp Forno': False,
    'Pressão 1': False,
    'Pressão 2': False,
}
thermo_sensors = {}
pressure_sensor = None  # NOVO
_hardware_init_success = True

if USE_RPI:
    print("Modo Raspberry Pi ativado. Validando hardware...")
    failed_sensors = []
    
    # Verificar se estamos realmente em um Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        if 'BCM' not in cpuinfo and 'Raspberry Pi' not in cpuinfo:
            print("⚠️  AVISO: Este não parece ser um Raspberry Pi real.")
    except:
        print("⚠️  AVISO: Não foi possível verificar se este é um Raspberry Pi.")
    
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        output_pins = [PIN_VENTILADOR, PIN_RESISTENCIA, PIN_MOTOR_ROSCA, PIN_TAMBOR_DIR, PIN_TAMBOR_PUL]
        for pin in output_pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # Relés desligados ao iniciar
        _rpi_ready = True
        print("✅ GPIOs de saída configurados com sucesso.")
        print(f"🔧 GPIOs configurados: {output_pins} - Todos iniciando em HIGH (relés desligados)")
    except ImportError as e:
        print("\n💥 [ERRO CRÍTICO] Biblioteca RPi.GPIO não encontrada!")
        print("🔧 SOLUÇÃO:")
        print("   1. Instale a biblioteca RPi.GPIO:")
        print("      pip install RPi.GPIO")
        print("   2. Ou se estiver usando ambiente virtual:")
        print("      source .venv/bin/activate")
        print("      pip install RPi.GPIO")
        print("   3. Em alguns sistemas pode ser necessário:")
        print("      sudo apt update")
        print("      sudo apt install python3-rpi.gpio")
        print("      pip install RPi.GPIO")
        print(f"\n🐛 Erro técnico: {e}")
        _hardware_init_success = False
    except Exception as e:
        print(f"\n💥 [ERRO CRÍTICO] Falha ao inicializar RPi.GPIO: {e}")
        print("🔧 POSSÍVEIS CAUSAS:")
        print("   • Não está executando em um Raspberry Pi")
        print("   • Usuário sem permissões GPIO (tente: sudo)")
        print("   • Conflito com outro programa usando GPIO")
        print("   • Sistema operacional não suportado")
        _hardware_init_success = False

    if _hardware_init_success:
        # Implementação nativa do MAX6675 usando apenas RPi.GPIO
        print("🔍 Iniciando implementação nativa MAX6675 (sem bibliotecas externas)...")
        
        class NativeMAX6675:
            """Implementação nativa do protocolo MAX6675 usando apenas RPi.GPIO"""
            
            def __init__(self, sck_pin, cs_pin, so_pin):
                self.sck_pin = sck_pin
                self.cs_pin = cs_pin
                self.so_pin = so_pin
                GPIO.setup(self.sck_pin, GPIO.OUT)
                GPIO.setup(self.cs_pin, GPIO.OUT)
                GPIO.setup(self.so_pin, GPIO.IN)
                GPIO.output(self.cs_pin, GPIO.HIGH)
                GPIO.output(self.sck_pin, GPIO.LOW)
                
            def readTempC(self):
                """Lê temperatura em Celsius"""
                try:
                    GPIO.output(self.cs_pin, GPIO.LOW)
                    time.sleep(0.001)
                    data = 0
                    for i in range(16):
                        GPIO.output(self.sck_pin, GPIO.HIGH)
                        time.sleep(0.0001)
                        bit = GPIO.input(self.so_pin)
                        data = (data << 1) | bit
                        GPIO.output(self.sck_pin, GPIO.LOW)
                        time.sleep(0.0001)
                    GPIO.output(self.cs_pin, GPIO.HIGH)
                    if data & 0x4:
                        raise ValueError("Erro no termopar")
                    temp_data = (data >> 3) & 0x1FFF
                    return temp_data * 0.25
                except Exception as e:
                    raise Exception(f"Erro na leitura SPI: {e}")

        MAX6675_lib = NativeMAX6675
        print("✅ Usando implementação nativa MAX6675 com RPi.GPIO!")
        
        thermo_configs = {
            "Torre Nível 1": THERMO_TORRE_1, "Torre Nível 2": THERMO_TORRE_2,
            "Torre Nível 3": THERMO_TORRE_3, "Temp Tanque":   THERMO_TANQUE,
            "Temp Saída Gases": THERMO_GASES, "Temp Forno":    THERMO_FORNO,
        }

        print("\n🔍 Iniciando teste detalhado dos sensores...")
        def test_sensor_with_retries(name, pins, max_attempts=3):
            print(f"📡 Testando sensor '{name}' (Pinos SCK:{pins[0]}, CS:{pins[1]}, SO:{pins[2]})...")
            for attempt in range(1, max_attempts + 1):
                try:
                    sensor = MAX6675_lib(*pins)
                    time.sleep(0.5)
                    temp = sensor.readTempC()
                    if temp is None or math.isnan(temp) or temp < -50 or temp > 1000:
                        raise ValueError(f"Leitura inválida: {temp}°C")
                    print(f"  ✅ Tentativa {attempt}/{max_attempts}: SUCESSO - Temp: {temp:.1f}°C")
                    return sensor, temp
                except Exception as e:
                    print(f"  ❌ Tentativa {attempt}/{max_attempts}: FALHA - {str(e)}")
                    if attempt < max_attempts: time.sleep(1)
            return None, None

        working_sensors = 0
        for name, pins in thermo_configs.items():
            sensor, temp = test_sensor_with_retries(name, pins)
            if sensor:
                thermo_sensors[name] = sensor
                working_sensors += 1
            else:
                failed_sensors.append(f"{name} (Pinos: {pins})")
        
        if failed_sensors:
            print("\n" + "="*70)
            print("💥 RELATÓRIO DE FALHAS DOS SENSORES")
            print("="*70)
            for sensor_name in failed_sensors:
                print(f"  ❌ {sensor_name}: Sem resposta")
            print("\n⚠️  ATENÇÃO: O sistema não pode iniciar com sensores falhando!")
            _hardware_init_success = False
        else:
            print("\n🚀 TODOS OS SENSORES ESTÃO FUNCIONANDO PERFEITAMENTE!")

        # ============= INICIALIZAR SENSORES DE PRESSÃO (ADS1115) =============
        print("\n🔍 Detectando dispositivos I2C...")
        i2c_devices = list_i2c_devices()
        if i2c_devices:
            print(f"✅ Dispositivos I2C encontrados: {', '.join(i2c_devices)}")
        else:
            print("⚠️  Nenhum dispositivo I2C detectado")
        
        print("\n🔍 Inicializando sensor de pressão (ADS1115)...")
        pressure_sensor = None
        try:
            pressure_sensor = PressureSensorADS1115(channel=0, i2c_address=0x48)
            # Teste de leitura
            test_pressure = pressure_sensor.read_pressure_psi()
            print(f"  ✅ Sensor de pressão OK - Leitura teste: {test_pressure:.2f} PSI")
            _sensor_status['Pressão 1'] = True
        except Exception as e:
            print(f"  ❌ Falha ao inicializar sensor de pressão: {e}")
            _sensor_status['Pressão 1'] = False
            failed_sensors.append(f"Sensor Pressão 1 (ADS1115 A0)")


# ============= 7) LÓGICA DE CONTROLE E SIMULAÇÃO =============

def apply_actuator_state():
    """Aplica o estado dos atuadores aos GPIOs (lógica invertida para relés)."""
    if USE_RPI and _rpi_ready:
        # Relés: HIGH=desligado, LOW=ligado (inverter estado)
        GPIO.output(PIN_VENTILADOR, not state['actuators']['ventilador'])
        GPIO.output(PIN_RESISTENCIA, not state['actuators']['resistencia'])
        GPIO.output(PIN_MOTOR_ROSCA, not state['actuators']['motor_rosca'])
        # Tambor: DIR define direção, PUL é o pulso/enable (manter lógica direta para driver)
        GPIO.output(PIN_TAMBOR_DIR, state['actuators'].get('tambor_dir', False))
        GPIO.output(PIN_TAMBOR_PUL, state['actuators'].get('tambor_pul', False))
        print(f"GPIO: VENT={not state['actuators']['ventilador']}, RES={not state['actuators']['resistencia']}, "
              f"ROSCA={not state['actuators']['motor_rosca']}, DIR={state['actuators'].get('tambor_dir', False)}, "
              f"PUL={state['actuators'].get('tambor_pul', False)}")
    else:
        # Modo simulação - mostrar estado (lógica invertida)
        sim_state = {k: ('LOW' if v else 'HIGH') for k, v in state['actuators'].items()}
        print(f"SIMUL: {state['actuators']} → GPIO = {sim_state}")

def rotate_drum(direction, duration_seconds):
    """
    Gira o tambor rotativo com velocidade controlada.
    
    Args:
        direction: True = forward (CW), False = reverse (CCW)
        duration_seconds: Tempo de rotação em segundos
    """
    global state
    
    if not (USE_RPI and _rpi_ready):
        print(f"SIMUL: Girando tambor {'FORWARD' if direction else 'REVERSE'} por {duration_seconds}s")
        return
    
    velocidade = state['settings'].get('velocidade_tambor', 1000)  # Hz
    steps = int(velocidade * duration_seconds)  # Total de passos
    delay = 1.0 / (velocidade * 2)  # Tempo entre HIGH e LOW
    
    print(f"🔧 Girando tambor: {velocidade} Hz, {steps} passos, {duration_seconds}s")
    
    # Definir direção
    GPIO.output(PIN_TAMBOR_DIR, direction)
    time.sleep(0.001)
    
    # Gerar pulsos
    for i in range(steps):
        GPIO.output(PIN_TAMBOR_PUL, GPIO.LOW)
        time.sleep(delay)
        GPIO.output(PIN_TAMBOR_PUL, GPIO.HIGH)
        time.sleep(delay)
    
    print(f"✅ Tambor girado: {steps} passos em {direction}")

def handle_automatic_mode():
    """Gerencia a lógica de controle no modo automático."""
    global state
    settings = state['settings']
    values = state['values']
    
    if settings.get('heating_status', 0) != 1 or "Temp Forno" not in values:
        state['actuators']['ventilador'] = False
        state['actuators']['resistencia'] = False
        state['actuators']['motor_rosca'] = False
        state['timers']['resistencia_start_time'] = None
        state['timers']['rosca_cycle_start'] = None
        return

    temp_forno = values["Temp Forno"]
    temp_min = settings.get("temp_forno_min", 300)
    temp_max = settings.get("temp_forno_max", 400)

    if temp_forno < temp_min:
        state['actuators']['ventilador'] = True
        
        # Timer resistência - liga por tempo determinado, depois desliga permanentemente
        now = time.time()
        resistencia_duration = max(1, int(settings.get('tempo_acionamento_resistencia', 10)))
        if state['timers']['resistencia_start_time'] is None:
            state['timers']['resistencia_start_time'] = now
        elapsed_resistencia = now - state['timers']['resistencia_start_time']
        state['actuators']['resistencia'] = (elapsed_resistencia < resistencia_duration)
        
        # Ciclo rosca - alterna entre ligado/desligado
        on_t = max(1, int(settings.get('tempo_acionamento_rosca', 5)))
        off_t = max(1, int(settings.get('tempo_pausa_rosca', 10)))
        cycle = on_t + off_t
        if state['timers']['rosca_cycle_start'] is None:
            state['timers']['rosca_cycle_start'] = now
        elapsed_rosca = (now - state['timers']['rosca_cycle_start']) % cycle
        state['actuators']['motor_rosca'] = (elapsed_rosca < on_t)
        
    elif temp_forno > temp_max:
        state['actuators']['ventilador'] = False
        state['actuators']['resistencia'] = False
        state['actuators']['motor_rosca'] = False
        # Resetar timers para próximo ciclo
        state['timers']['resistencia_start_time'] = None
        state['timers']['rosca_cycle_start'] = None

def noise(val, amp): return random.uniform(-amp, amp)

def read_temp(label, base_c, amp):
    if USE_RPI and label in thermo_sensors:
        try:
            c = float(thermo_sensors[label].readTempC())
            if c > 0 and not math.isnan(c): return round(c, 1)
        except Exception: pass
    return round(base_c + noise(base_c, amp/10.0), 1)

def compute_values():
    """Computa valores dos sensores, atualiza o estado global e salva no banco."""
    global state
    
    if USE_RPI and _rpi_ready and _sensors_validated:
        # ===== MODO RASPBERRY PI - LEITURA REAL =====
        values = {}
        
        # Mapeamento: _sensor_status key -> thermo_sensors key -> values key
        sensor_mapping = {
            'Temp Torre 1': ('Torre Nível 1', 'Torre Nível 1'),
            'Temp Torre 2': ('Torre Nível 2', 'Torre Nível 2'),
            'Temp Torre 3': ('Torre Nível 3', 'Torre Nível 3'),
            'Temp Tanque': ('Temp Tanque', 'Temp Tanque'),
            'Temp Gases': ('Temp Saída Gases', 'Temp Saída Gases'),
            'Temp Forno': ('Temp Forno', 'Temp Forno'),
        }
        
        for status_key, (thermo_key, values_key) in sensor_mapping.items():
            if _sensor_status.get(status_key, False):
                try:
                    if thermo_key in thermo_sensors:
                        temp = thermo_sensors[thermo_key].readTempC()
                        if temp is not None and not math.isnan(temp) and -50 < temp < 1500:
                            values[values_key] = round(temp, 1)
                        else:
                            print(f"⚠️  {status_key}: Leitura inválida ({temp})")
                except Exception as e:
                    print(f"❌ Erro ao ler {status_key}: {e}")
        
        # Leitura do sensor de pressão
        if _sensor_status.get('Pressão 1', False) and pressure_sensor:
            try:
                pressure_psi = pressure_sensor.read_pressure_psi()
                values["Pressão Gases"] = round(pressure_psi, 2)
            except Exception as e:
                print(f"❌ Erro ao ler sensor de pressão: {e}")
        
        # Adicionar valores simulados para sensores não disponíveis
        if "Velocidade" not in values:
            values["Velocidade"] = max(0, int(round(600.0 + noise(600.0, 50.0*5.0))))
        if "Pressão Gases" not in values:
            values["Pressão Gases"] = round(max(0.0, 2.0 + noise(2.0, 0.5)), 2)
        
        state['values'] = values
        
    else:
        # ===== MODO SIMULAÇÃO - DADOS ALEATÓRIOS =====
        if not USE_RPI:
            # Apenas em modo simulação (não no Raspberry Pi)
            base_values = {
                "Temp Forno": 350.0, "Velocidade": 600.0, "Temp Tanque": 120.0,
                "Temp Saída Gases": 300.0, "Pressão Gases": 2.0, "Torre Nível 1": 110.0,
                "Torre Nível 2": 140.0, "Torre Nível 3": 180.0,
            }
            noise_amp = 50.0

            values = {
                "Temp Forno": read_temp("Temp Forno", base_values["Temp Forno"], noise_amp),
                "Velocidade": max(0, int(round(base_values["Velocidade"] + noise(base_values["Velocidade"], noise_amp*5.0)))),
                "Temp Tanque": read_temp("Temp Tanque", base_values["Temp Tanque"], noise_amp),
                "Temp Saída Gases": read_temp("Temp Saída Gases", base_values["Temp Saída Gases"], noise_amp),
                "Pressão Gases": round(max(0.0, base_values["Pressão Gases"] + noise(base_values["Pressão Gases"], noise_amp/100.0)), 2),
                "Torre Nível 1": read_temp("Torre Nível 1", base_values["Torre Nível 1"], noise_amp),
                "Torre Nível 2": read_temp("Torre Nível 2", base_values["Torre Nível 2"], noise_amp),
                "Torre Nível 3": read_temp("Torre Nível 3", base_values["Torre Nível 3"], noise_amp),
            }
            state['values'] = values
        else:
            # Raspberry Pi sem sensores validados - não gerar dados
            print("⚠️  Sensores não validados - sem dados disponíveis")
            state['values'] = {}

    # Salvar no banco de dados periodicamente (a cada 5 segundos)
    if state.get('last_save_time', 0) == 0 or (time.time() - state.get('last_save_time', 0)) > 5:
        # Apenas salvar se houver dados válidos
        if USE_RPI and _sensors_validated:
            for name, value in state['values'].items():
                # Validar valor antes de salvar
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    continue  # Pula sensor com dado inválido
                
                # Validar range
                if 'Temp' in name and not (-50 < value < 1500):
                    continue  # Temperatura fora do range válido
                if 'Pressão' in name and not (0 < value < 100):
                    continue  # Pressão fora do range válido
                
                sensor_type = 'temperature' if 'Temp' in name or 'Torre' in name else ('pressure' if 'Pressão' in name else 'velocity')
                log_sensor_reading(name, value, sensor_type, mode='real')
        elif not USE_RPI:
            # Modo simulação - salvar dados simulados
            for name, value in state['values'].items():
                if value is None or (isinstance(value, float) and math.isnan(value)):
                    continue
                
                sensor_type = 'temperature' if 'Temp' in name or 'Torre' in name else ('pressure' if 'Pressão' in name else 'velocity')
                log_sensor_reading(name, value, sensor_type, mode='simulation')
        
        state['last_save_time'] = time.time()

# ============= 8) DESENHO =============
def draw_centered_text(img, text, center_xy, font_scale, thickness, color=TEXT_COLOR):
    (tw, th), _ = cv2.getTextSize(text, FONT, font_scale, thickness)
    x, y = int(center_xy[0] - tw/2), int(center_xy[1] + th/2)
    if OUTLINE:
        cv2.putText(img, text, (x, y), FONT, font_scale, (255,255,255), OUTLINE_THICKNESS, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), FONT, font_scale, color, thickness, cv2.LINE_AA)

# ============= 9.5) STARTUP TEST ROUTINE =============
def run_startup_test():
    """Executa rotina de teste de todos os atuadores ao iniciar."""
    global state
    
    print("\n" + "="*50)
    print("🧪 INICIANDO ROTINA DE TESTE DOS ATUADORES")
    print("="*50)
    
    # Salvar estado original
    original_mode = state['settings'].get('system_mode', 0)
    state['settings']['system_mode'] = 1  # Força modo manual para teste
    
    # Lista de testes
    tests = [
        ("Ventilador", "ventilador", 1.0),
        ("Resistência", "resistencia", 1.0),
        ("Rosca de Alimentação", "motor_rosca", 1.0),
    ]
    
    # Testar atuadores simples
    for name, actuator, duration in tests:
        print(f"\n🔧 Testando {name}...")
        state['actuators'][actuator] = True
        apply_actuator_state()
        sio.emit('dashboard_update', state, namespace='/dashboard')
        time.sleep(duration)
        
        state['actuators'][actuator] = False
        apply_actuator_state()
        sio.emit('dashboard_update', state, namespace='/dashboard')
        time.sleep(0.5)
    
    # Testar Tambor Avanço
    print(f"\n🔧 Testando Tambor Avanço...")
    state['actuators']['tambor_dir'] = True
    state['actuators']['tambor_pul'] = True
    apply_actuator_state()
    sio.emit('dashboard_update', state, namespace='/dashboard')
    time.sleep(2.0)
    
    state['actuators']['tambor_pul'] = False
    apply_actuator_state()
    sio.emit('dashboard_update', state, namespace='/dashboard')
    time.sleep(0.5)
    
    # Testar Tambor Retorno
    print(f"\n🔧 Testando Tambor Retorno...")
    state['actuators']['tambor_dir'] = False
    state['actuators']['tambor_pul'] = True
    apply_actuator_state()
    sio.emit('dashboard_update', state, namespace='/dashboard')
    time.sleep(2.0)
    
    # Desligar tudo
    state['actuators']['tambor_pul'] = False
    apply_actuator_state()
    sio.emit('dashboard_update', state, namespace='/dashboard')
    
    # Restaurar modo original
    state['settings']['system_mode'] = original_mode
    
    print("\n" + "="*50)
    print("✅ ROTINA DE TESTE CONCLUÍDA")
    print("="*50 + "\n")

# ============= 10) MAIN LOOP =============
def main():
    global state, STOP
    init_database()
    state['settings'] = load_settings()
    
    print(f"🚀 Estado inicial dos atuadores: {state['actuators']}")
    print(f"🔧 Modo do sistema: {'Manual' if state['settings'].get('system_mode', 0) == 1 else 'Automático'}")
    
    # Mostrar modo de operação
    if USE_RPI:
        print("\n" + "="*70)
        print("🤖 MODO RASPBERRY PI - LEITURA REAL DOS SENSORES")
        print("="*70)
        
        if not _hardware_init_success:
            print("❌ Hardware não inicializado corretamente!")
            raise SystemExit()
        
        # Validar sensores
        if not validate_sensors():
            print("❌ Sensores não validados - impossível continuar!")
            raise SystemExit()
    else:
        print("\n" + "="*70)
        print("🎮 MODO SIMULAÇÃO - DADOS ALEATÓRIOS")
        print("="*70)
        print("⚠️  Este modo é apenas para desenvolvimento/teste")
        print("⚠️  Use --use-rpi para modo produção com sensores reais")
        print("="*70)

    try:
        sio.connect('http://localhost:3333', namespaces=['/dashboard'])
    except socketio.exceptions.ConnectionError as e:
        print(f"Falha ao conectar ao servidor: {e}")
        return

    # NOVO: Executar rotina de teste
    if not args.skip_test:
        print("⏳ Aguardando 2 segundos antes de iniciar teste...")
        time.sleep(2)
        run_startup_test()
    else:
        print("⏭️  Rotina de teste pulada (--skip-test)")

    bg = cv2.imread(args.img)
    if bg is None: raise SystemExit(f"Não consegui abrir a imagem: {args.img}")
    if args.scale != 1.0:
        bg = cv2.resize(bg, None, fx=args.scale, fy=args.scale)
    
    H, W = bg.shape[:2]
    abs_pos = {k: (int(xn*W), int(yn*H)) for k,(xn,yn) in POSITIONS_NORM.items()}
    font_scale = BASE_FONT_SCALE * args.scale
    thickness  = max(1, int(round(BASE_THICKNESS * args.scale)))

    cv2.namedWindow("Painel", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Painel", W, H)

    while not STOP:
        compute_values()

        if state['settings'].get('system_mode', 0) == 0: # Modo Automático
            handle_automatic_mode()
        
        apply_actuator_state()
        sio.emit('dashboard_update', state, namespace='/dashboard')

        frame = bg.copy()
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        draw_centered_text(frame, ts, (int(0.5*W), int(0.05*H)), font_scale*0.8, max(1, thickness-1))
        
        for name in FIELD_NAMES:
            if name in state['values']:
                draw_centered_text(frame, str(state['values'][name]), abs_pos[name], font_scale, thickness)

        cv2.imshow("Painel", frame)

        key = cv2.waitKey(100)
        if key == 27: STOP = True
        
        sio.sleep(0.1) # Permite que o cliente websocket processe eventos

    sio.disconnect()
    if USE_RPI and _rpi_ready:
        # Desligar todos os relés (HIGH) antes de limpar GPIOs
        print("🔌 Desligando todos os relés...")
        GPIO.output(PIN_VENTILADOR, GPIO.HIGH)
        GPIO.output(PIN_RESISTENCIA, GPIO.HIGH)
        GPIO.output(PIN_MOTOR_ROSCA, GPIO.HIGH)
        GPIO.output(PIN_TAMBOR_DIR, GPIO.HIGH)
        GPIO.output(PIN_TAMBOR_PUL, GPIO.HIGH)
        GPIO.cleanup()
    cv2.destroyAllWindows()
    print("Programa finalizado.")

if __name__ == "__main__":
    main()
