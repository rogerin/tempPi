# Tabela Completa de Pinagem - Raspberry Pi

## Resumo das Alterações para Resolver Conflitos

### GPIOs Alterados:
1. **Temp Tanque SCK**: GPIO 4 → GPIO 1
2. **Temp Tanque CS**: GPIO 6 → GPIO 15  
3. **Temp Tanque SO**: GPIO 5 → GPIO 0
4. **Tambor DIR**: GPIO 6 → GPIO 4

### GPIOs Mantidos (sem conflito):
- Tambor PUL: GPIO 19 ✅
- Tambor ENA: GPIO 5 ✅ (agora livre)

---

## Tabela Completa de GPIO

| Componente | Função | GPIO | Pino Físico | Observações |
|------------|--------|------|-------------|-------------|
| **SENSORES DE TEMPERATURA (MAX6675 - SPI)** |
| Torre Nível 1 | SCK | 25 | 22 | Clock SPI |
| Torre Nível 1 | CS | 24 | 18 | Chip Select |
| Torre Nível 1 | SO | 18 | 12 | Data Out |
| Torre Nível 2 | SCK | 7 | 26 | Clock SPI |
| Torre Nível 2 | CS | 8 | 24 | Chip Select |
| Torre Nível 2 | SO | 23 | 16 | Data Out |
| Torre Nível 3 | SCK | 21 | 40 | Clock SPI |
| Torre Nível 3 | CS | 20 | 38 | Chip Select |
| Torre Nível 3 | SO | 16 | 36 | Data Out |
| **Temp Tanque (T4)** | **SCK** | **1** | **28** | Clock SPI - ALTERADO |
| **Temp Tanque (T4)** | **CS** | **15** | **10** | Chip Select - MANTIDO |
| **Temp Tanque (T4)** | **SO** | **0** | **27** | Data Out - ALTERADO |
| Temp Gases | SCK | 22 | 15 | Clock SPI |
| Temp Gases | CS | 27 | 13 | Chip Select |
| Temp Gases | SO | 17 | 11 | Data Out |
| Temp Forno | SCK | 11 | 23 | Clock SPI |
| Temp Forno | CS | 9 | 21 | Chip Select |
| Temp Forno | SO | 10 | 19 | Data Out |
| **SENSORES DE PRESSÃO (ADS1115 - I2C)** |
| Pressão 1 | SDA | 2 | 3 | I2C Data |
| Pressão 1 | SCL | 3 | 5 | I2C Clock |
| **ATUADORES (Relés e Motor)** |
| Ventilador | OUT | 14 | 8 | Relé (LOW=ligado) |
| Resistência | OUT | 26 | 37 | Relé (LOW=ligado) |
| Motor Rosca | OUT | 12 | 32 | Relé (LOW=ligado) |
| **MOTOR TAMBOR (Driver de Passo)** |
| Tambor | DIR | **4** | **7** | Direção - ALTERADO |
| Tambor | PUL | 19 | 35 | Pulsos (PWM) |
| Tambor | ENA | 5 | 29 | Enable |

---

## Verificação de Conflitos

Após as mudanças, todos os GPIOs estão livres:
- ✅ GPIO 5: Tambor ENA (liberado)
- ✅ GPIO 13: Temp Tanque SCK
- ✅ GPIO 15: Tambor DIR (liberado)
- ✅ GPIO 19: Temp Tanque SO (liberado)

## Benefícios

- ✅ Zero conflitos de GPIO
- ✅ Mantém tambor PUL e ENA onde está
- ✅ Mudanças mínimas (apenas 4 pinos alterados)
- ✅ Usa GPIOs disponíveis e seguros

## Verificação Final de Conflitos

### GPIOs Usados (após correção):
- GPIO 0: Temp Tanque SO ✅
- GPIO 1: Temp Tanque SCK ✅
- GPIO 2: I2C SDA ✅
- GPIO 3: I2C SCL ✅
- GPIO 4: Tambor DIR ✅
- GPIO 5: Tambor ENA ✅
- GPIO 7: Torre 2 SCK ✅
- GPIO 8: Torre 2 CS ✅
- GPIO 9: Forno CS ✅
- GPIO 10: Forno SO ✅
- GPIO 11: Forno SCK ✅
- GPIO 12: Motor Rosca ✅
- GPIO 14: Ventilador ✅
- GPIO 15: Temp Tanque CS ✅
- GPIO 16: Torre 3 SO ✅
- GPIO 17: Gases SO ✅
- GPIO 18: Torre 1 SO ✅
- GPIO 19: Tambor PUL ✅
- GPIO 20: Torre 3 CS ✅
- GPIO 21: Torre 3 SCK ✅
- GPIO 22: Gases SCK ✅
- GPIO 23: Torre 2 SO ✅
- GPIO 24: Torre 1 CS ✅
- GPIO 25: Torre 1 SCK ✅
- GPIO 26: Resistência ✅
- GPIO 27: Gases CS ✅

**✅ RESULTADO: ZERO CONFLITOS DE GPIO!**

## Comandos de Teste

```bash
# Testar motor de passo
python3 test_motor.py --steps 200 --direction forward

# Testar sensor de pressão
python3 test_ads1115.py

# Executar dashboard
python3 dashboard.py --img background.jpg --use-rpi
```
