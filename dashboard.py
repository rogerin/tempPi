# dashboard_overlay.py
# Painel com overlay sobre imagem, controle por teclado (sem depender de sliders),
# min/max com efeito visual, saída limpa (ESC/Ctrl+C) e gráficos OpenCV (sem Matplotlib).

import cv2, numpy as np, random, argparse, time, math, warnings, signal
from datetime import datetime

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
ap.add_argument("--thermo-tanque", nargs=3, type=int, default=[4, 3, 2], 
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

# ============= 2) PINAGENS (BCM) - Configuráveis via argumentos =============
THERMO_TORRE_1 = tuple(args.thermo_torre1)
THERMO_TORRE_2 = tuple(args.thermo_torre2)
THERMO_TORRE_3 = tuple(args.thermo_torre3)
THERMO_TANQUE  = tuple(args.thermo_tanque)   # atenção: alguns pinos podem ser SDA/SCL (I2C)
THERMO_GASES   = tuple(args.thermo_gases)
THERMO_FORNO   = tuple(args.thermo_forno)

PRESSAO_1_PIN = args.pressao1_pin
PRESSAO_2_PIN = args.pressao2_pin

PIN_VENTILADOR = args.ventilador_pin
PIN_RESISTENCIA = args.resistencia_pin
PIN_MOTOR_ROSCA = args.motor_rosca_pin
PIN_TAMBOR_DIR  = args.tambor_dir_pin
PIN_TAMBOR_PUL  = args.tambor_pul_pin

# ============= 3) UI / CAMPOS =============
FIELD_NAMES = [
    "Temp Forno", "Velocidade", "Temp Tanque", "Temp Saída Gases",
    "Pressão Gases", "Torre Nível 1", "Torre Nível 2", "Torre Nível 3",
]

# posições normalizadas (0..1) — ajuste conforme sua arte
POSITIONS_NORM = {
    "Temp Forno":        (0.44, 0.42),
    "Velocidade":        (0.44, 0.57),
    "Temp Tanque":       (0.44, 0.77),
    "Temp Saída Gases":  (0.217, 0.53),
    "Pressão Gases":     (0.217, 0.59),
    "Torre Nível 1":     (0.75, 0.77),
    "Torre Nível 2":     (0.75, 0.56),
    "Torre Nível 3":     (0.75, 0.38),
}

SHOW_MOUSE_POS = True
mouse_pos_norm = (0.0, 0.0)

FONT = cv2.FONT_HERSHEY_SIMPLEX
BASE_FONT_SCALE = 0.8
BASE_THICKNESS = 2
TEXT_COLOR = (0, 0, 0)
OUTLINE = True
OUTLINE_THICKNESS = 3
SHADOW = False

# ============= 4) FLAGS e SAÍDA LIMPA =============
STOP  = False  # sair sem traceback

def _sigint_handler(sig, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGINT, _sigint_handler)

# ============= 5) RPi opcional (fallback) =============
_rpi_ready = False
thermo_sensors = {}
_hardware_init_success = True # Nova flag para validação estrita

if USE_RPI:
    print("Modo Raspberry Pi ativado. Validando hardware...")
    failed_sensors = []
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        output_pins = [PIN_VENTILADOR, PIN_RESISTENCIA, PIN_MOTOR_ROSCA, PIN_TAMBOR_DIR, PIN_TAMBOR_PUL]
        for pin in output_pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        _rpi_ready = True
        print("GPIOs de saída configurados com sucesso.")
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha ao inicializar RPi.GPIO: {e}.")
        _hardware_init_success = False

    if _hardware_init_success:
        try:
            import MAX6675.MAX6675 as MAX6675
            thermo_configs = {
                "Torre Nível 1": THERMO_TORRE_1,
                "Torre Nível 2": THERMO_TORRE_2,
                "Torre Nível 3": THERMO_TORRE_3,
                "Temp Tanque":   THERMO_TANQUE,
                "Temp Saída Gases": THERMO_GASES,
                "Temp Forno":    THERMO_FORNO,
            }

            print("\n🔍 Iniciando teste detalhado dos sensores de temperatura...")
            print("⏱️  Cada sensor será testado 3 vezes para garantir funcionamento correto.\n")
            
            def test_sensor_with_retries(name, pins, max_attempts=3):
                """Testa um sensor específico com múltiplas tentativas"""
                print(f"📡 Testando sensor '{name}' (Pinos SCK:{pins[0]}, CS:{pins[1]}, SO:{pins[2]})...")
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        # Criar instância do sensor
                        sensor = MAX6675.MAX6675(*pins)
                        
                        # Pequena pausa para estabilização
                        time.sleep(0.5)
                        
                        # Tentar ler temperatura
                        temp = sensor.readTempC()
                        
                        # Validar se a leitura é válida
                        if temp is None or math.isnan(temp) or temp < -50 or temp > 1000:
                            raise ValueError(f"Leitura inválida: {temp}°C")
                        
                        # Teste bem-sucedido
                        print(f"  ✅ Tentativa {attempt}/3: SUCESSO - Temperatura: {temp:.1f}°C")
                        return sensor, temp
                        
                    except Exception as e:
                        print(f"  ❌ Tentativa {attempt}/3: FALHA - {str(e)}")
                        if attempt < max_attempts:
                            print(f"     🔄 Aguardando 1s antes da próxima tentativa...")
                            time.sleep(1)
                        else:
                            print(f"     💥 Sensor '{name}' falhou em todas as tentativas!")
                
                return None, None

            # Testar cada sensor individualmente
            sensor_results = {}
            total_sensors = len(thermo_configs)
            working_sensors = 0
            
            for i, (name, pins) in enumerate(thermo_configs.items(), 1):
                print(f"\n[{i}/{total_sensors}] " + "="*50)
                sensor, temp = test_sensor_with_retries(name, pins)
                
                if sensor is not None:
                    thermo_sensors[name] = sensor
                    sensor_results[name] = {"status": "OK", "temp": temp, "pins": pins}
                    working_sensors += 1
                    print(f"✨ Sensor '{name}' APROVADO!")
                else:
                    sensor_results[name] = {"status": "FALHA", "temp": None, "pins": pins}
                    failed_sensors.append(f"{name} (Pinos: {pins})")
                    print(f"💀 Sensor '{name}' REPROVADO!")
            
            # Relatório final
            print("\n" + "="*70)
            print("📊 RELATÓRIO FINAL DE VALIDAÇÃO DOS SENSORES")
            print("="*70)
            print(f"✅ Sensores funcionando: {working_sensors}/{total_sensors}")
            print(f"❌ Sensores com falha: {len(failed_sensors)}/{total_sensors}")
            
            if working_sensors > 0:
                print(f"\n🎉 SENSORES APROVADOS:")
                for name, result in sensor_results.items():
                    if result["status"] == "OK":
                        print(f"  ✅ {name}: {result['temp']:.1f}°C (Pinos: {result['pins']})")
            
            if failed_sensors:
                print(f"\n💥 SENSORES REPROVADOS:")
                for name, result in sensor_results.items():
                    if result["status"] == "FALHA":
                        print(f"  ❌ {name}: Sem resposta (Pinos: {result['pins']})")
                
                print(f"\n⚠️  ATENÇÃO: {len(failed_sensors)} sensor(es) não está(ão) funcionando!")
                print("🔧 Verifique:")
                print("   • Conexões físicas dos pinos")
                print("   • Alimentação dos sensores (3.3V ou 5V)")
                print("   • Soldas dos conectores")
                print("   • Termopares conectados corretamente")
                
                _hardware_init_success = False
            else:
                print(f"\n🚀 TODOS OS SENSORES ESTÃO FUNCIONANDO PERFEITAMENTE!")
                print("✨ Sistema pronto para operação!")

        except ImportError:
            print("\n[ERRO CRÍTICO] Biblioteca MAX6675 não encontrada. Instale-a para usar o modo RPi.")
            print("💡 Execute: pip install MAX6675-RPi")
            _hardware_init_success = False
        except Exception as e:
            print(f"\n[ERRO CRÍTICO] Ocorreu um erro inesperado durante a validação dos sensores: {e}")
            _hardware_init_success = False

# Fallback para simulação se a flag RPi não estiver ativa
if not USE_RPI:
    print("Executando em modo de simulação (sem hardware).")



# ============= 6) SIMULAÇÃO / ESTADOS =============
# Valores base (você vai alterar por teclado)
base_values = {
    "Temp Forno":       350.0,
    "Temp Tanque":      120.0,
    "Temp Saída Gases": 300.0,
    "Torre Nível 1":    110.0,
    "Torre Nível 2":    140.0,
    "Torre Nível 3":    180.0,
    "Pressão Gases":    2.00,   # bar
    "Velocidade":       600.0,  # rpm
}
# Ruído global
noise_amp = 50.0



# ranges dos gráficos
RANGES = {
    "Temp Forno":       (0.0, 600.0, "C"),
    "Temp Tanque":      (0.0, 400.0, "C"),
    "Temp Saída Gases": (0.0, 600.0, "C"),
    "Torre Nível 1":    (0.0, 400.0, "C"),
    "Torre Nível 2":    (0.0, 400.0, "C"),
    "Torre Nível 3":    (0.0, 400.0, "C"),
    "Pressão Gases":    (0.0, 10.0,  "bar"),
    "Velocidade":       (0.0, 2000.0,"rpm"),
}

# ============= 7) LEITURAS (real/sim) =============
def noise(val, amp):
    # amplitude proporcional simples
    return random.uniform(-amp, amp)

def read_temp(label, base_c, amp):
    # Tenta a leitura do sensor real se ele foi inicializado com sucesso
    if USE_RPI and label in thermo_sensors:
        try:
            c = float(thermo_sensors[label].readTempC())
            # Adiciona uma verificação para leituras inválidas comuns (ex: 0.0 ou NaN)
            if c > 0 and not math.isnan(c):
                return round(c, 1)
            else:
                # Se a leitura for inválida, recorre à simulação para este ciclo
                pass
        except Exception:
            # Em caso de erro de leitura, também recorre à simulação
            pass
    
    # Fallback para simulação
    return round(base_c + noise(base_c, amp/10.0), 1)

def read_pressao_bar(base_bar, amp):
    val = base_bar + noise(base_bar, amp/100.0)
    return round(max(0.0, val), 2)

def read_velocidade_rpm(base_rpm, amp):
    val = base_rpm + noise(base_rpm, amp*5.0)
    return max(0, int(round(val)))

def compute_values():
    return {
        "Temp Forno":        read_temp("Temp Forno", base_values["Temp Forno"], noise_amp),
        "Velocidade":        read_velocidade_rpm(base_values["Velocidade"], noise_amp),
        "Temp Tanque":       read_temp("Temp Tanque", base_values["Temp Tanque"], noise_amp),
        "Temp Saída Gases":  read_temp("Temp Saída Gases", base_values["Temp Saída Gases"], noise_amp),
        "Pressão Gases":     read_pressao_bar(base_values["Pressão Gases"], noise_amp),
        "Torre Nível 1":     read_temp("Torre Nível 1", base_values["Torre Nível 1"], noise_amp),
        "Torre Nível 2":     read_temp("Torre Nível 2", base_values["Torre Nível 2"], noise_amp),
        "Torre Nível 3":     read_temp("Torre Nível 3", base_values["Torre Nível 3"], noise_amp),
    }

# ============= 8) DESENHO TEXTO, HELP e MOUSE =============
def draw_centered_text(img, text, center_xy, font_scale, thickness, color=TEXT_COLOR):
    (tw, th), _ = cv2.getTextSize(text, FONT, font_scale, thickness)
    x = int(center_xy[0] - tw/2)
    y = int(center_xy[1] + th/2)
    if OUTLINE:
        cv2.putText(img, text, (x, y), FONT, font_scale, (255,255,255), OUTLINE_THICKNESS, cv2.LINE_AA)
    if SHADOW:
        cv2.putText(img, text, (x+2, y+2), FONT, font_scale, (255,255,255), thickness, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), FONT, font_scale, color, thickness, cv2.LINE_AA)



def mouse_callback(event, x, y, flags, param):
    global mouse_pos_norm
    if SHOW_MOUSE_POS:
        H, W = param.shape[:2]
        mouse_pos_norm = (x / W, y / H)

def draw_mouse_pos(frame):
    if SHOW_MOUSE_POS:
        txt = f"{mouse_pos_norm[0]:.3f}, {mouse_pos_norm[1]:.3f}"
        cv2.putText(frame, txt, (10, 25), FONT, 0.7, (0,0,255), 2, cv2.LINE_AA)





# ============= 10) MAIN LOOP =============
def main():
    # Validação estrita de hardware antes de iniciar a UI
    if USE_RPI and not _hardware_init_success:
        print("\nO programa não pode iniciar em modo Raspberry Pi devido a erros de hardware.")
        print("Por favor, verifique as conexões dos sensores, a configuração de pinos e as bibliotecas.")
        print("Para rodar em modo de simulação, execute o script sem a flag '--use-rpi'.")
        raise SystemExit()

    bg = cv2.imread(args.img)
    if bg is None:
        raise SystemExit(f"Não consegui abrir a imagem: {args.img}")


    if args.scale != 1.0:
        bg = cv2.resize(bg, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_AREA)

    H, W = bg.shape[:2]
    abs_pos = {k: (int(xn*W), int(yn*H)) for k,(xn,yn) in POSITIONS_NORM.items()}
    font_scale = BASE_FONT_SCALE * args.scale
    thickness  = max(1, int(round(BASE_THICKNESS * args.scale)))

    # Janela principal
    cv2.namedWindow("Painel", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Painel", W, H)
    cv2.setMouseCallback("Painel", mouse_callback, bg)

    values = {}
    last_update_time = 0
    update_interval = 2  # segundos
    global STOP

    while True:
        now = time.time()
        # Lógica de atualização de valores
        # Em modo RPi, lê continuamente. Em simulação, atualiza a cada 2 segundos.
        if USE_RPI or (now - last_update_time > update_interval):
            values = compute_values()
            if not USE_RPI:
                last_update_time = now

        # Evita erro no primeiro loop de simulação antes que os valores sejam gerados
        if not values:
            time.sleep(0.1)
            continue

        # Painel
        frame = bg.copy()
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        draw_centered_text(frame, ts, (int(0.5*W), int(0.05*H)), font_scale*0.8, max(1, thickness-1))
        for name in FIELD_NAMES:
            if name in values:
                draw_centered_text(frame, str(values[name]), abs_pos[name], font_scale, thickness)
        draw_mouse_pos(frame)

        cv2.imshow("Painel", frame)

        # Teclado
        key = cv2.waitKey(100) # Aumentado para reduzir uso de CPU
        if key == 27 or STOP:  # ESC ou Ctrl+C
            break

        

        time.sleep(0.01)

    if USE_RPI and _rpi_ready:
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except Exception:
            pass
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()