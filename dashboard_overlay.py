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
    "Torre Nível 1":     (0.78, 0.81),
    "Torre Nível 2":     (0.77, 0.56),
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

# min/max observados
stats_min = {k: float("+inf") for k in FIELD_NAMES}
stats_max = {k: float("-inf") for k in FIELD_NAMES}

# Eventos de novo min/max (para flash)
# guardamos timestamps dos últimos eventos
hit_min_ts = {k: 0.0 for k in FIELD_NAMES}
hit_max_ts = {k: 0.0 for k in FIELD_NAMES}
HIT_DURATION = 0.8  # segundos de efeito visual

# seleção atual para edição por teclado
selected_idx = 0  # 0..7
show_help = True  # ajuda rápida na tela

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

def draw_help_overlay(frame, selected_name):
    lines = [
        f"[Selecionado] {selected_name}",
        "1 a 8: selecionar variavel",
        "cima/baixo: base +/-   |  PgUp/PgDn: base +/- (grande)",
        "[ / ]: ruido -/+",
        "R: reset min/max  |  H: ajuda on/off",
        "ESC/Ctrl+C: sair",
    ]
    x, y = 12, 60
    for ln in lines:
        cv2.putText(frame, ln, (x, y), FONT, 0.6, (10,10,10), 2, cv2.LINE_AA)
        y += 24

def mouse_callback(event, x, y, flags, param):
    global mouse_pos_norm
    if SHOW_MOUSE_POS:
        H, W = param.shape[:2]
        mouse_pos_norm = (x / W, y / H)

def draw_mouse_pos(frame):
    if SHOW_MOUSE_POS:
        txt = f"{mouse_pos_norm[0]:.3f}, {mouse_pos_norm[1]:.3f}"
        cv2.putText(frame, txt, (10, 25), FONT, 0.7, (0,0,255), 2, cv2.LINE_AA)

def update_minmax(field, current_value, now_ts):
    global stats_min, stats_max, hit_min_ts, hit_max_ts
    # novo min?
    if current_value < stats_min[field]:
        stats_min[field] = current_value
        hit_min_ts[field] = now_ts
    # novo max?
    if current_value > stats_max[field]:
        stats_max[field] = current_value
        hit_max_ts[field] = now_ts

def draw_minmax(frame, pos_xy, field, font_scale, thickness):
    x, y = pos_xy
    offset = int(26 * font_scale)
    miv = stats_min[field] if stats_min[field] != float('+inf') else float('nan')
    mav = stats_max[field] if stats_max[field] != float('-inf') else float('nan')
    txt = f"min {miv} | max {mav}"
    (tw, th), _ = cv2.getTextSize(txt, FONT, font_scale*0.6, max(1, thickness-1))
    pos = (int(x - tw/2), int(y + offset + th/2))
    cv2.putText(frame, txt, pos, FONT, font_scale*0.6, (40,40,40), max(1, thickness-1), cv2.LINE_AA)

# ============= 9) GRÁFICOS (sem Matplotlib) =============
def flash_color(base_color, strength):
    # mistura cor base com branco para efeito de flash
    b,g,r = base_color
    s = min(max(strength, 0.0), 1.0)
    return (int(b + (255-b)*s), int(g + (255-g)*s), int(r + (255-r)*s))

def draw_card(canvas, x, y, w, h, title, value, vmin, vmax, unit, now_ts):
    # Detecta se teve novo min/max recentemente
    t_min = hit_min_ts.get(title, 0.0)
    t_max = hit_max_ts.get(title, 0.0)
    glow_min = max(0.0, 1.0 - (now_ts - t_min)/HIT_DURATION) if now_ts - t_min < HIT_DURATION else 0.0
    glow_max = max(0.0, 1.0 - (now_ts - t_max)/HIT_DURATION) if now_ts - t_max < HIT_DURATION else 0.0

    # fundo do card + borda
    base_bg = (230,230,230)
    bg = base_bg
    if glow_min > 0:  # flash avermelhado para novo mínimo
        bg = flash_color((230,210,210), glow_min*0.7)
    if glow_max > 0:  # flash azulado para novo máximo
        # combina com possível min (levemente roxo acinzentado)
        cmax = flash_color((210,230,255), glow_max*0.7)
        bg = tuple(int((a+b)/2) for a,b in zip(bg, cmax))
    cv2.rectangle(canvas, (x, y), (x+w, y+h), bg, -1)
    cv2.rectangle(canvas, (x, y), (x+w, y+h), (200,200,200), 2)

    # título
    cv2.putText(canvas, title, (x+12, y+28), FONT, 0.7, (30,30,30), 2, cv2.LINE_AA)

    # faixa e barra
    bar_x, bar_y = x+12, y + h//2 - 14
    bar_w, bar_h = w-24, 28
    cv2.rectangle(canvas, (bar_x, bar_y), (bar_x+bar_w, bar_y+bar_h), (210,210,210), -1)
    cv2.rectangle(canvas, (bar_x, bar_y), (bar_x+bar_w, bar_y+bar_h), (160,160,160), 2)

    lo, hi = vmin, vmax
    try:
        cur = float(value)
    except Exception:
        cur = lo
    pct = (cur - lo) / max(1e-9, (hi - lo))
    pct = min(1.0, max(0.0, pct))
    fill_w = int(pct * bar_w)
    cv2.rectangle(canvas, (bar_x, bar_y), (bar_x+fill_w, bar_y+bar_h), (100,180,255), -1)

    # ticks
    for t in range(0, 6):
        tx = bar_x + int(t * bar_w / 5)
        cv2.line(canvas, (tx, bar_y+bar_h), (tx, bar_y+bar_h+6), (120,120,120), 1)
        tval = lo + t*(hi-lo)/5.0
        ttxt = f"{tval:.0f}"
        cv2.putText(canvas, ttxt, (tx-12, bar_y+bar_h+22), FONT, 0.45, (80,80,80), 1, cv2.LINE_AA)

    # valor numérico
    vtxt = f"{value} {unit}".strip()
    (tw, th), _ = cv2.getTextSize(vtxt, FONT, 0.8, 2)
    cv2.putText(canvas, vtxt, (x + w - tw - 12, y + 28), FONT, 0.8, (20,20,20), 2, cv2.LINE_AA)

    # min/max observados
    obs_min = stats_min.get(title, float('nan'))
    obs_max = stats_max.get(title, float('nan'))
    mtxt = f"min {obs_min} | max {obs_max}"
    cv2.putText(canvas, mtxt, (x+12, y+h-14), FONT, 0.5, (60,60,60), 1, cv2.LINE_AA)

    # marcadores visuais quando bate min/max
    if glow_min > 0:
        # marcador no início da barra
        cv2.circle(canvas, (bar_x, bar_y + bar_h//2), 8, (0,0,255), -1)
    if glow_max > 0:
        # marcador no fim da barra
        cv2.circle(canvas, (bar_x + bar_w, bar_y + bar_h//2), 8, (255,0,0), -1)

def render_charts_window(values, show_selected_idx):
    # grid 2 col x 4 linhas
    W, H = 900, 720
    pad = 16
    cols, rows = 2, 4
    cw = (W - pad*(cols+1)) // cols
    ch = (H - pad*(rows+1)) // rows

    canvas = np.full((H, W, 3), 245, dtype=np.uint8)

    title = "Gráficos de Processo"
    (tw, th), _ = cv2.getTextSize(title, FONT, 0.9, 2)
    cv2.putText(canvas, title, ((W - tw)//2, 28), FONT, 0.9, (30,30,30), 2, cv2.LINE_AA)

    idx = 0
    now_ts = time.time()
    for name in FIELD_NAMES:
        r = idx // cols
        c = idx % cols
        x = pad + c*(cw + pad)
        y = 44 + pad + r*(ch + pad)
        lo, hi, unit = RANGES[name]
        draw_card(canvas, x, y, cw, ch, name, values[name], lo, hi, unit, now_ts)

        # destaque da seleção atual
        if idx == show_selected_idx:
            cv2.rectangle(canvas, (x, y), (x+cw, y+ch), (50,120,255), 3)

        idx += 1

    cv2.imshow("Gráficos", canvas)

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
    global DIRTY, STOP, selected_idx, noise_amp, show_help

    while True:
        # só recalcula quando DIRTY
        if DIRTY or not last_values:
            values = compute_values()
            last_values = values
            DIRTY = False
            # atualiza min/max + timestamp de hits
            now_ts = time.time()
            for name in FIELD_NAMES:
                try:
                    v = float(values[name])
                except Exception:
                    continue
                update_minmax(name, v, now_ts)
        else:
            values = last_values

        # Painel
        frame = bg.copy()
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        draw_centered_text(frame, ts, (int(0.5*W), int(0.05*H)), font_scale*0.8, max(1, thickness-1))
        for name in FIELD_NAMES:
            draw_centered_text(frame, str(values[name]), abs_pos[name], font_scale, thickness)
            draw_minmax(frame, abs_pos[name], name, font_scale, thickness)
        draw_mouse_pos(frame)

        # Ajuda
        if show_help:
            draw_help_overlay(frame, FIELD_NAMES[selected_idx])

        cv2.imshow("Painel", frame)
        render_charts_window(values, selected_idx)

        # Teclado
        key = cv2.waitKey(10)
        if key == 27 or STOP:  # ESC ou Ctrl+C
            break

        # Seleção 1..8
        if key in [ord(str(d)) for d in range(1,9)]:
            selected_idx = int(chr(key)) - 1
        # Arrrows e PageUp/Down
        step_small = 1.0
        step_big   = 10.0
        sel_name = FIELD_NAMES[selected_idx]
        if key == 82 or key == 2490368:  # Up
            base_values[sel_name] += step_small
            DIRTY = True
        elif key == 84 or key == 2621440:  # Down
            base_values[sel_name] -= step_small
            DIRTY = True
        elif key == ord('q') or key == ord('Q'):  # Q para + grande
            base_values[sel_name] += step_big
            DIRTY = True
        elif key == ord('a') or key == ord('A'):  # A para - grande
            base_values[sel_name] -= step_big
            DIRTY = True
        # Ruído [ / ]
        elif key == ord('['):
            noise_amp = max(0.0, noise_amp - 5.0)
        elif key == ord(']'):
            noise_amp = noise_amp + 5.0
        # Reset min/max
        elif key == ord('r') or key == ord('R'):
            for k in FIELD_NAMES:
                stats_min[k] = float('+inf')
                stats_max[k] = float('-inf')
                hit_min_ts[k] = 0.0
                hit_max_ts[k] = 0.0
        # Toggle help
        elif key == ord('h') or key == ord('H'):
            show_help = not show_help

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