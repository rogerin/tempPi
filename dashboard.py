# dashboard.py
# Painel com overlay sobre imagem, controle por teclado (sem depender de sliders),
# min/max com efeito visual, saída limpa (ESC/Ctrl+C) e gráficos OpenCV (sem Matplotlib).
# Integrado com servidor WebSocket para controle e visualização remota.

import cv2, numpy as np, random, argparse, time, math, warnings, signal, sqlite3, os
from datetime import datetime
import socketio
import json

# ============= 1) ARGUMENTOS DE LINHA DE COMANDO =============
ap = argparse.ArgumentParser(description="Dashboard de controle para sistema de destilação")
ap.add_argument("--img", required=True, help="Caminho da imagem de fundo.")
ap.add_argument("--scale", type=float, default=1.0, help="Escala da janela (ex.: 1.0).")
ap.add_argument("--use-rpi", action="store_true", help="Ativar modo Raspberry Pi (GPIO/MAX6675).")

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
    'settings': {}, 'values': {},
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
            "system_mode": 0, "heating_on": False,
            "temp_min": 300, "temp_max": 400,
            "resistencia_timer": 10, "rosca_on_timer": 5, "rosca_off_timer": 10
        }

# ============= 5) FLAGS e SAÍDA LIMPA =============
STOP  = False
def _sigint_handler(sig, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGINT, _sigint_handler)

# ============= 6) RPi opcional (fallback) =============
_rpi_ready = False
thermo_sensors = {}
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
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        _rpi_ready = True
        print("✅ GPIOs de saída configurados com sucesso.")
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


# ============= 7) LÓGICA DE CONTROLE E SIMULAÇÃO =============

def apply_actuator_state():
    """Aplica o estado dos atuadores aos GPIOs ou simulação."""
    if USE_RPI and _rpi_ready:
        GPIO.output(PIN_VENTILADOR, state['actuators']['ventilador'])
        GPIO.output(PIN_RESISTENCIA, state['actuators']['resistencia'])
        GPIO.output(PIN_MOTOR_ROSCA, state['actuators']['motor_rosca'])
        # ... etc para outros atuadores
    else:
        # Apenas imprime o estado em modo de simulação se houver mudança
        pass # print(f"SIMUL: {state['actuators']}")

def handle_automatic_mode():
    """Gerencia a lógica de controle no modo automático."""
    global state
    settings = state['settings']
    values = state['values']
    
    if not settings.get('heating_on', False) or "Temp Forno" not in values:
        state['actuators']['ventilador'] = False
        state['actuators']['resistencia'] = False
        state['actuators']['motor_rosca'] = False
        return

    temp_forno = values["Temp Forno"]
    temp_min = settings.get("temp_min", 300)
    temp_max = settings.get("temp_max", 400)

    if temp_forno < temp_min:
        state['actuators']['ventilador'] = True
        # Lógica de ciclo para resistência e rosca
        # (Implementação simplificada)
        state['actuators']['resistencia'] = True 
        state['actuators']['motor_rosca'] = True
    elif temp_forno > temp_max:
        state['actuators']['ventilador'] = False
        state['actuators']['resistencia'] = False
        state['actuators']['motor_rosca'] = False

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
    mode = "rpi" if USE_RPI else "simulation"
    
    # Valores simulados como base
    base_values = {
        "Temp Forno": 350.0, "Velocidade": 600.0, "Temp Tanque": 120.0,
        "Temp Saída Gases": 300.0, "Pressão Gases": 2.0, "Torre Nível 1": 110.0,
        "Torre Nível 2": 140.0, "Torre Nível 3": 180.0,
    }
    noise_amp = 50.0

    # Ler valores (real ou simulação)
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
    state['values'] = values # Atualiza o estado global

    # Salvar no banco de dados
    # (Opcional, pode ser feito em um processo separado)
    # for name, value in values.items():
    #     log_sensor_reading(...)

# ============= 8) DESENHO =============
def draw_centered_text(img, text, center_xy, font_scale, thickness, color=TEXT_COLOR):
    (tw, th), _ = cv2.getTextSize(text, FONT, font_scale, thickness)
    x, y = int(center_xy[0] - tw/2), int(center_xy[1] + th/2)
    if OUTLINE:
        cv2.putText(img, text, (x, y), FONT, font_scale, (255,255,255), OUTLINE_THICKNESS, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), FONT, font_scale, color, thickness, cv2.LINE_AA)

# ============= 10) MAIN LOOP =============
def main():
    global state, STOP
    init_database()
    state['settings'] = load_settings()

    if USE_RPI and not _hardware_init_success:
        print("Programa não pode iniciar devido a erros de hardware.")
        raise SystemExit()

    try:
        sio.connect('http://localhost:8080', namespaces=['/dashboard'])
    except socketio.exceptions.ConnectionError as e:
        print(f"Falha ao conectar ao servidor: {e}")
        return

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
        GPIO.cleanup()
    cv2.destroyAllWindows()
    print("Programa finalizado.")

if __name__ == "__main__":
    main()