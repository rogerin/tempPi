#!/usr/bin/env python3
"""
Script isolado para testar motor de passo do tambor rotativo.
Controla diretamente os GPIOs 13 (DIR) e 19 (PUL).

USO:
    python3 test_motor.py --steps 200 --direction forward
    python3 test_motor.py --steps 400 --direction reverse --speed 1000
"""

import argparse
import time
import sys

# Tentar importar RPi.GPIO
try:
    import RPi.GPIO as GPIO
    USE_RPI = True
    print("✅ RPi.GPIO importado - Modo REAL")
except ImportError:
    USE_RPI = False
    print("⚠️  RPi.GPIO não disponível - Modo SIMULAÇÃO")

# Configuração dos pinos (conexão física real)
PIN_DIR = 6   # GPIO6 - Direção (DIR+) - Pino físico 31
PIN_PUL = 19  # GPIO19 - Pulsos (PUL+) - Pino físico 35 (suporta PWM)
PIN_ENA = 5   # GPIO5 - Enable (ENA+) - Pino físico 29

def setup_gpio():
    """Configura os pinos GPIO."""
    if not USE_RPI:
        print("⚠️  Modo simulação - GPIOs não serão acionados")
        return
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PIN_DIR, GPIO.OUT)
    GPIO.setup(PIN_PUL, GPIO.OUT)
    GPIO.setup(PIN_ENA, GPIO.OUT)
    
    # Inicializar
    GPIO.output(PIN_ENA, GPIO.LOW)   # Enable = LOW (motor habilitado)
    GPIO.output(PIN_DIR, GPIO.HIGH)  # Direção padrão (CCW)
    GPIO.output(PIN_PUL, GPIO.HIGH)  # Pulso inicia em HIGH (borda de descida)
    
    print(f"✅ GPIOs configurados:")
    print(f"   - PIN_DIR (GPIO{PIN_DIR}): Direção - Pino físico 31")
    print(f"   - PIN_PUL (GPIO{PIN_PUL}): Pulsos (PWM) - Pino físico 35")
    print(f"   - PIN_ENA (GPIO{PIN_ENA}): Enable - Pino físico 29")
    print(f"   💡 Motor habilitado (ENA=LOW)")

def cleanup_gpio():
    """Limpa os GPIOs."""
    if USE_RPI:
        # Desabilitar motor antes de limpar
        GPIO.output(PIN_ENA, GPIO.HIGH)  # Enable = HIGH (motor desabilitado)
        GPIO.cleanup()
        print("🧹 GPIOs limpos")
        print("✅ Motor desabilitado (ENA=HIGH)")

def rotate_motor(direction='forward', steps=200, speed=500):
    """
    Gira o motor de passo.
    
    Args:
        direction: 'forward' (avanço) ou 'reverse' (retorno)
        steps: Número de passos (pulsos)
        speed: Velocidade em Hz (pulsos por segundo)
    """
    # Configurar direção (baseado no Arduino: HIGH=CCW, LOW=CW)
    if USE_RPI:
        # HIGH = CCW (anti-horário), LOW = CW (horário)
        dir_value = GPIO.LOW if direction == 'forward' else GPIO.HIGH
    else:
        dir_value = 0 if direction == 'forward' else 1  # Simulação
    
    dir_name = "CW (horário)" if direction == 'forward' else "CCW (anti-horário)"
    
    print(f"\n{'='*60}")
    print(f"🔧 GIRANDO MOTOR - {dir_name}")
    print(f"{'='*60}")
    print(f"   Direção: {direction.upper()}")
    print(f"   Passos: {steps}")
    print(f"   Velocidade: {speed} Hz")
    print(f"   Tempo estimado: {steps/speed:.2f}s")
    print(f"{'='*60}\n")
    
    if USE_RPI:
        # Definir direção
        GPIO.output(PIN_DIR, dir_value)
        time.sleep(0.001)  # Pequeno delay para estabilizar
        
        # Gerar pulsos (similar ao Arduino - borda de descida)
        delay = 1.0 / (speed * 2)  # Tempo entre HIGH e LOW
        
        for i in range(steps):
            GPIO.output(PIN_PUL, GPIO.LOW)   # Borda de descida
            time.sleep(delay)
            GPIO.output(PIN_PUL, GPIO.HIGH)  # Borda de subida
            time.sleep(delay)
            
            # Mostrar progresso a cada 10%
            if steps >= 10 and (i + 1) % (steps // 10) == 0:
                progress = ((i + 1) / steps) * 100
                print(f"   Progresso: {progress:.0f}% ({i+1}/{steps} passos)")
        
        print(f"\n✅ Motor girou {steps} passos em {dir_name}")
    else:
        # Simulação
        print(f"🔄 SIMULAÇÃO: Girando {steps} passos em {dir_name}")
        time.sleep(steps / speed)
        print(f"✅ Simulação concluída")

def test_sequence():
    """Executa uma sequência de testes."""
    print("\n" + "="*60)
    print("🧪 SEQUÊNCIA DE TESTE DO MOTOR DE PASSO")
    print("="*60)
    
    tests = [
        ("Teste 1: Avanço lento (100 passos, 200 Hz)", 'forward', 100, 200),
        ("Teste 2: Retorno lento (100 passos, 200 Hz)", 'reverse', 100, 200),
        ("Teste 3: Avanço médio (200 passos, 500 Hz)", 'forward', 200, 500),
        ("Teste 4: Retorno médio (200 passos, 500 Hz)", 'reverse', 200, 500),
        ("Teste 5: Avanço rápido (400 passos, 1000 Hz)", 'forward', 400, 1000),
        ("Teste 6: Retorno rápido (400 passos, 1000 Hz)", 'reverse', 400, 1000),
    ]
    
    for i, (desc, direction, steps, speed) in enumerate(tests, 1):
        print(f"\n{'='*60}")
        print(f"📋 {desc}")
        print(f"{'='*60}")
        
        input("Pressione ENTER para continuar (ou Ctrl+C para sair)...")
        
        rotate_motor(direction, steps, speed)
        time.sleep(1)  # Pausa entre testes
    
    print("\n" + "="*60)
    print("✅ TODOS OS TESTES CONCLUÍDOS")
    print("="*60)

def interactive_mode():
    """Modo interativo para controlar o motor."""
    print("\n" + "="*60)
    print("🎮 MODO INTERATIVO - CONTROLE DO MOTOR")
    print("="*60)
    
    while True:
        print("\n" + "-"*60)
        print("Opções:")
        print("  1. Girar AVANÇO")
        print("  2. Girar RETORNO")
        print("  3. Teste rápido (10 passos cada direção)")
        print("  4. Sequência de testes completa")
        print("  0. Sair")
        print("-"*60)
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            steps = int(input("Número de passos [200]: ") or "200")
            speed = int(input("Velocidade (Hz) [500]: ") or "500")
            rotate_motor('forward', steps, speed)
        elif choice == '2':
            steps = int(input("Número de passos [200]: ") or "200")
            speed = int(input("Velocidade (Hz) [500]: ") or "500")
            rotate_motor('reverse', steps, speed)
        elif choice == '3':
            print("\n🔄 Teste rápido...")
            rotate_motor('forward', 10, 200)
            time.sleep(0.5)
            rotate_motor('reverse', 10, 200)
        elif choice == '4':
            test_sequence()
        else:
            print("❌ Opção inválida")

def main():
    parser = argparse.ArgumentParser(
        description="Teste isolado do motor de passo (tambor rotativo)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Girar 200 passos para frente
  python3 test_motor.py --steps 200 --direction forward
  
  # Girar 400 passos para trás, velocidade 1000 Hz
  python3 test_motor.py --steps 400 --direction reverse --speed 1000
  
  # Sequência de testes automática
  python3 test_motor.py --sequence
  
  # Modo interativo
  python3 test_motor.py --interactive
        """
    )
    
    parser.add_argument('--steps', type=int, default=200,
                        help='Número de passos (padrão: 200)')
    parser.add_argument('--direction', choices=['forward', 'reverse'], default='forward',
                        help='Direção: forward (avanço) ou reverse (retorno)')
    parser.add_argument('--speed', type=int, default=500,
                        help='Velocidade em Hz - pulsos por segundo (padrão: 500)')
    parser.add_argument('--sequence', action='store_true',
                        help='Executar sequência de testes automática')
    parser.add_argument('--interactive', action='store_true',
                        help='Modo interativo')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("🔧 TESTE DO MOTOR DE PASSO - TAMBOR ROTATIVO")
    print("="*60)
    print(f"Modo: {'REAL (Raspberry Pi)' if USE_RPI else 'SIMULAÇÃO'}")
    print("="*60)
    
    try:
        setup_gpio()
        
        if args.interactive:
            interactive_mode()
        elif args.sequence:
            test_sequence()
        else:
            rotate_motor(args.direction, args.steps, args.speed)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_gpio()
        print("\n👋 Programa finalizado\n")

if __name__ == "__main__":
    main()
