# dashboard_overlay.py
# Mostra valores aleatórios sobre uma imagem, atualizando a cada 1 segundo.
# Posições são normalizadas (proporcionais) para funcionar em qualquer escala.
# Ctrl+C ou ESC para sair.

import cv2
import numpy as np
import random
import argparse
import time
from datetime import datetime

# ---------- PARÂMETROS ----------
# Nomes dos 8 campos (ajuste livre). Use nomes curtos para caber nas caixas verdes.
FIELD_NAMES = [
    "Temp Forno",        # 1
    "Velocidade",        # 2
    "Temp Tanque",       # 3
    "Temp Saída Gases",  # 4
    "Pressão Gases",     # 5
    "Torre Nível 1",     # 6
    "Torre Nível 2",     # 7
    "Torre Nível 3",     # 8
]

# Posições NORMALIZADAS (x,y em 0..1) aproximadas para a imagem fornecida.
# Ajuste fino se necessário (ficam salvos aqui, é só alterar).
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

# ---------- CONFIG EXTRA ----------
SHOW_MOUSE_POS = True  # Se True, mostra x,y normalizados do mouse
mouse_pos_norm = (0, 0)

def mouse_callback(event, x, y, flags, param):
    global mouse_pos_norm
    if SHOW_MOUSE_POS:
        H, W = param.shape[:2]
        mouse_pos_norm = (x / W, y / H)

def draw_mouse_pos(frame):
    if SHOW_MOUSE_POS:
        text = f"{mouse_pos_norm[0]:.3f}, {mouse_pos_norm[1]:.3f}"
        cv2.putText(frame, text, (10, 25), FONT, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

# Faixas de valores de exemplo (aleatórios por enquanto).
# Quando ligar sensores, substitua as funções get_* por leituras reais.
def get_temp_c():
    return round(random.uniform(25, 380), 1)  # C

def get_pressao_bar():
    return round(random.uniform(0.8, 4.5), 2) # bar

def get_velocidade_rpm():
    return random.randint(120, 980)          # rpm

DATA_SOURCES = {
    "Temp Forno":        lambda: f"{get_temp_c():.1f} C",
    "Velocidade":        lambda: f"{get_velocidade_rpm()} rpm",
    "Temp Tanque":       lambda: f"{get_temp_c():.1f} C",
    "Temp Saída Gases":  lambda: f"{get_temp_c():.1f} C",
    "Pressão Gases":     lambda: f"{get_pressao_bar():.2f} bar",
    "Torre Nível 1":     lambda: f"{get_temp_c():.1f} C",
    "Torre Nível 2":     lambda: f"{get_temp_c():.1f} C",
    "Torre Nível 3":     lambda: f"{get_temp_c():.1f} C",
}

# Estilo do texto
FONT = cv2.FONT_HERSHEY_SIMPLEX
BASE_FONT_SCALE = 0.6     # escala base (ajustada automaticamente pelo scale)
BASE_THICKNESS = 2
TEXT_COLOR = (0, 0, 0)    # preto
OUTLINE = True            # contorno branco fino para legibilidade
OUTLINE_THICKNESS = 3
SHADOW = False            # sombra opcional

# ---------- FUNÇÕES ----------
def draw_centered_text(img, text, center_xy, font_scale, thickness):
    # mede o texto
    (tw, th), baseline = cv2.getTextSize(text, FONT, font_scale, thickness)
    x = int(center_xy[0] - tw / 2)
    y = int(center_xy[1] + th / 2)

    if OUTLINE:
        cv2.putText(img, text, (x, y), FONT, font_scale, (255, 255, 255), OUTLINE_THICKNESS, cv2.LINE_AA)
    if SHADOW:
        cv2.putText(img, text, (x+2, y+2), FONT, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    cv2.putText(img, text, (x, y), FONT, font_scale, TEXT_COLOR, thickness, cv2.LINE_AA)

def main():
    
    ap = argparse.ArgumentParser(description="Overlay de valores em imagem (8 campos).")
    ap.add_argument("--img", required=True, help="Caminho da imagem de fundo.")
    ap.add_argument("--scale", type=float, default=1.0, help="Escala da janela (ex.: 0.8, 1.0, 1.2).")
    ap.add_argument("--fps", type=float, default=1.0, help="Atualizações por segundo (1.0 = a cada 1s).")
    args = ap.parse_args()

    bg = cv2.imread(args.img)
    if bg is None:
        raise SystemExit(f"Não consegui abrir a imagem: {args.img}")

    # Redimensiona imagem conforme scale (sem perder proporção das posições)
    if args.scale != 1.0:
        bg = cv2.resize(bg, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_AREA)

    H, W = bg.shape[:2]

    cv2.namedWindow("Painel", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Painel", W, H)

    # Pre-calcula coordenadas absolutas a partir das normalizadas
    abs_positions = {}
    for name in FIELD_NAMES:
        if name not in POSITIONS_NORM:
            raise SystemExit(f"Faltou posição para o campo: {name}")
        xn, yn = POSITIONS_NORM[name]
        abs_positions[name] = (int(xn * W), int(yn * H))

    font_scale = BASE_FONT_SCALE * args.scale
    thickness = max(1, int(round(BASE_THICKNESS * args.scale)))
    interval = 1.0 / max(0.001, args.fps)

    cv2.namedWindow("Painel", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Painel", W, H)
    cv2.setMouseCallback("Painel", mouse_callback, bg)  # passa a imagem como param
    last = 0.0
    while True:
        
        frame = bg.copy()
        draw_mouse_pos(frame)

        # Desenha timestamp (opcional)
        ts = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        draw_centered_text(frame, ts, (int(0.5*W), int(0.05*H)), font_scale*0.8, max(1, thickness-1))

        # Atualiza e desenha os 8 campos
        for name in FIELD_NAMES:
            val = DATA_SOURCES[name]()
            draw_centered_text(frame, val, abs_positions[name], font_scale, thickness)

        cv2.imshow("Painel", frame)

        # Espera ~interval (e captura ESC)
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break

        # controla taxa de atualização simplificada
        now = time.time()
        if now - last < interval:
            time.sleep(max(0, interval - (now - last)))
        last = time.time()

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()