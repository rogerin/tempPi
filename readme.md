# Dashboard Overlay (Painel-Apenas) – README

Projeto em Python para simular e/ou ler dados (Raspberry Pi) e sobrepor valores em pontos de uma imagem (ex.: fluxograma da planta). Esta é uma versão simplificada que exibe apenas o painel principal, sem a janela de gráficos.

## 1) Requisitos

- **Python 3.9+** (recomendado 3.10/3.11)
- **Sistema**: macOS, Windows ou Linux (Raspberry Pi opcional)

### Dependências

```bash
pip install opencv-python
```

Se você usa virtualenv:

```bash
python -m venv .venv
source .venv/bin/activate     # macOS/Linux
# .venv\Scripts\activate      # Windows
pip install opencv-python
```

## 2) Arquivo principal

O projeto é um único arquivo:

- `dashboard.py`

Coloque a sua imagem de fundo (jpg/png) na mesma pasta do projeto.

## 3) Como rodar

```bash
python dashboard.py --img "/caminho/para/sua_imagem.jpg" --scale 1.0
```

**Parâmetros:**
- `--img`: caminho da imagem de fundo (obrigatório)
- `--scale`: escala da janela principal (opcional). Ex.: 0.8, 1.0, 1.2

Na janela **Painel**, você verá os valores sobrepostos nos campos da sua imagem.

## 4) Modo Simulação

Por padrão, o script é executado em modo de simulação (`USE_RPI = False`). Neste modo:

- Os valores são gerados aleatoriamente para simular a chegada de dados de sensores.
- As atualizações ocorrem a cada 2 segundos com pequenas variações para parecerem mais realistas.
- Não há controles de teclado para ajustar os valores; a simulação é automática.

## 5) Controles

- **ESC** ou **Ctrl+C**: fecha o programa.

## 6) Posicionamento dos valores na imagem

As posições dos 8 campos são proporcionais à imagem (0.0–1.0) e podem ser ajustadas no dicionário `POSITIONS_NORM` dentro do arquivo `dashboard.py`.

Para encontrar as coordenadas, mova o cursor sobre a imagem; no canto superior esquerdo aparecem as coordenadas normalizadas (x, y) que você pode usar.
