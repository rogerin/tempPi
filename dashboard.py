# dashboard_overlay.py
# Painel com overlay sobre imagem, controle por teclado (sem depender de sliders),
# min/max com efeito visual, saída limpa (ESC/Ctrl+C) e gráficos OpenCV (sem Matplotlib).

import cv2, numpy as np, random, argparse, time, math, warnings, signal
from datetime import datetime

# ============= 1) CHAVE DE EXECUÇÃO (RPi) =============
USE_RPI = False  # False = simulação; True = tenta usar Raspberry Pi (GPIO/MAX6675)

# ============= 2) PINAGENS (BCM) =============
THERMO_TORRE_1 = (25, 24, 18)
THERMO_TORRE_2 = (7,  8,  23)
THERMO_TORRE_3 = (21, 20, 16)
THERMO_TANQUE  = (4,  3,  2)   # atenção: 2/3 = SDA/SCL (I2C)
THERMO_GASES   = (22, 27, 17)
THERMO_FORNO   = (11, 9,  10)

PRESSAO_1_PIN = 2
PRESSAO_2_PIN = 3

PIN_VENTILADOR = 14
PIN_RESISTENCIA = 26
PIN_MOTOR_ROSCA = 12
PIN_TAMBOR_DIR  = 13
PIN_TAMBOR_PUL  = 19

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
DIRTY = True   # recalcular valores
STOP  = False  # sair sem traceback

def _sigint_handler(sig, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGINT, _sigint_handler)

# ============= 5) RPi opcional (fallback) =============
_rpi_ready = False
try:
    if USE_RPI:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        for p in [PIN_VENTILADOR, PIN_RESISTENCIA, PIN_MOTOR_ROSCA, PIN_TAMBOR_DIR, PIN_TAMBOR_PUL]:
            GPIO.setup(p, GPIO.OUT, initial=GPIO.LOW)
        thermo = {}
        try:
            import MAX6675.MAX6675 as MAX6675
            thermo = {
                "Torre Nível 1": MAX6675.MAX6675(*THERMO_TORRE_1),
                "Torre Nível 2": MAX6675.MAX6675(*THERMO_TORRE_2),
                "Torre Nível 3": MAX6675.MAX6675(*THERMO_TORRE_3),
                "Temp Tanque":   MAX6675.MAX6675(*THERMO_TANQUE),
                "Temp Saída Gases": MAX6675.MAX6675(*THERMO_GASES),
                "Temp Forno":    MAX6675.MAX6675(*THERMO_FORNO),
            }
        except Exception:
            thermo = {}
        _rpi_ready = True
except Exception:
    _rpi_ready = False
if USE_RPI and not _rpi_ready:
    warnings.warn("USE_RPI=True, mas GPIO/termopar não inicializaram. Usando simulação.")

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
    if USE_RPI and _rpi_ready and label in globals().get("thermo", {}):
        try:
            c = float(thermo[label].readTempC())
            return round(c, 1)
        except Exception:
            pass
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--img", required=True, help="Caminho da imagem de fundo.")
    ap.add_argument("--scale", type=float, default=1.0, help="Escala da janela (ex.: 1.0).")
    args = ap.parse_args()

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

    last_values = {}
    global DIRTY, STOP, noise_amp

    while True:
        # só recalcula quando DIRTY
        if DIRTY or not last_values:
            values = compute_values()
            last_values = values
            DIRTY = False
        else:
            values = last_values

        # Painel
        frame = bg.copy()
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        draw_centered_text(frame, ts, (int(0.5*W), int(0.05*H)), font_scale*0.8, max(1, thickness-1))
        for name in FIELD_NAMES:
            draw_centered_text(frame, str(values[name]), abs_pos[name], font_scale, thickness)
        draw_mouse_pos(frame)

        

        cv2.imshow("Painel", frame)

        # Teclado
        key = cv2.waitKey(10)
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