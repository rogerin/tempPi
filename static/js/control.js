document.addEventListener('DOMContentLoaded', function() {
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/web');

    // Estado local do frontend
    let state = {
        settings: {},
        values: {},
        actuators: {
            ventilador: false,
            resistencia: false,
            motor_rosca: false,
            ventilacao_resfriador: false,
            tambor_dir: false,
            tambor_pul: false,
            tambor_ena: false
        }
    };

    // Mapear elementos da UI
    const settingInputs = document.querySelectorAll('#temp-settings-form input, #pressure-time-settings-form input');
    const modeRadios = document.querySelectorAll('input[name="system_mode"]');
    const heatingBtn = document.getElementById('heating-status-btn');
    const manualControls = document.getElementById('manual-controls');
    const manualButtons = document.querySelectorAll('#manual-fan-btn, #manual-screw-btn, #manual-cooling-btn, #manual-drum-fwd-btn, #manual-drum-rev-btn');

    // Conexão WebSocket
    socket.on('connect', () => {
        // Solicita os dados mais recentes ao se conectar
        socket.emit('request_initial_data');
        fetchSensorData();
    });

    // Listener para atualizações do backend
    socket.on('update_from_dashboard', (data) => {
        updateUI(data);
    });

    function fetchSensorData() {
        fetch('/api/sensors')
            .then(response => response.json())
            .then(data => {
                // Dados dos sensores processados silenciosamente
            })
            .catch(error => console.error('Erro ao buscar dados dos sensores:', error));
    }

    function updateUI(data) {
        // Atualizar state local
        state = { ...state, ...data };

        // Atualizar campos de settings
        for (const [key, value] of Object.entries(state.settings)) {
            const input = document.getElementById(key);
            if (input && document.activeElement !== input) {
                input.value = value;
            }
        }

        // Atualizar velocidade tambor
        if (state.settings.velocidade_tambor && velocidadeTamborSlider) {
            velocidadeTamborSlider.value = state.settings.velocidade_tambor;
            const hz = state.settings.velocidade_tambor;
            const rpm = Math.round(hz * 0.3);
            velocidadeTamborDisplay.textContent = `${hz} Hz`;
            velocidadeTamborRpm.textContent = `${rpm} RPM`;
        }

        // Atualizar modo de operação
        const currentMode = state.settings['system_mode'] || 0;
        const radio = document.querySelector(`input[name="system_mode"][value="${currentMode}"]`);
        if(radio) radio.checked = true;
        toggleManualControls(currentMode == 1);

        // Atualizar botão de aquecimento
        const currentHeatingStatus = state.settings['heating_status'] || 0;
        updateHeatingButton(currentHeatingStatus);
        
        // Atualizar botões do tambor
        updateDrumButtons();

        // Atualizar estado dos botões manuais
        if(currentMode == 1) {
            updateManualButton('manual-fan-btn', state.actuators.ventilador);
            updateManualButton('manual-screw-btn', state.actuators.motor_rosca);
            updateManualButton('manual-cooling-btn', state.actuators.ventilacao_resfriador);
            // Lógica para tambor é mais complexa, pode ser ajustada
            updateManualButton('manual-drum-fwd-btn', state.actuators.tambor_pul && state.actuators.tambor_dir);
            updateManualButton('manual-drum-rev-btn', state.actuators.tambor_pul && !state.actuators.tambor_dir);
        }

        // Atualizar displays de temperatura em tempo real
        if (state.values) {
            updateTemperatureDisplays(state.values);
        }

        // Atualizar status dos atuadores
        if (state.actuators) {
            updateActuatorStatus(state.actuators);
        }

        // Atualizar badges dos botões manuais
        updateManualButtonBadges();
    }

    function updateTemperatureDisplays(values) {
        // Mapear nomes dos sensores para IDs dos displays
        const sensorMapping = {
            'Temp Forno': 'display_temp_forno',
            'Torre Nível 1': 'display_temp_torre1',
            'Torre Nível 2': 'display_temp_torre2', 
            'Torre Nível 3': 'display_temp_torre3',
            'Temp Tanque': 'display_temp_tanque',
            'Temp Saída Gases': 'display_temp_gases',
            'Pressão Gases': 'display_pressao_gases'
        };

        Object.entries(sensorMapping).forEach(([sensorName, displayId]) => {
            const element = document.getElementById(displayId);
            if (element && values[sensorName] !== undefined) {
                if (sensorName === 'Pressão Gases') {
                    element.textContent = `${values[sensorName].toFixed(2)} PSI`;
                } else {
                    element.textContent = `${values[sensorName].toFixed(1)} °C`;
                }
            }
        });

        // Calcular e exibir pressão em BAR
        const barElement = document.getElementById('display_pressao_gases_bar');
        if (barElement && values['Pressão Gases'] !== undefined) {
            const psi = values['Pressão Gases'];
            const bar = psi / 14.504;
            barElement.textContent = `${bar.toFixed(3)} BAR`;
        }
    }

    function updateActuatorStatus(actuators) {
        const statusMap = {
            'status_ventilador': actuators.ventilador,
            'status_resistencia': actuators.resistencia,
            'status_motor_rosca': actuators.motor_rosca,
            'status_ventilacao_resfriador': actuators.ventilacao_resfriador,
            'status_tambor': actuators.tambor_pul // Considera ligado se pulso ativo
        };
        
        Object.entries(statusMap).forEach(([id, isActive]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = isActive ? 'ON' : 'OFF';
                element.className = `badge ${isActive ? 'bg-success' : 'bg-secondary'}`;
            }
        });

        // Atualizar direção do tambor
        const dirIcon = document.getElementById('tambor_direction_icon');
        const dirStatus = document.getElementById('status_tambor_dir');
        
        if (dirIcon && dirStatus) {
            if (actuators.tambor_pul) {
                if (actuators.tambor_dir) {
                    dirIcon.className = 'fas fa-arrow-right me-2';
                    dirStatus.textContent = 'AVANÇO';
                    dirStatus.className = 'badge bg-primary';
                } else {
                    dirIcon.className = 'fas fa-arrow-left me-2';
                    dirStatus.textContent = 'RETORNO';
                    dirStatus.className = 'badge bg-warning';
                }
            } else {
                dirIcon.className = 'fas fa-stop me-2';
                dirStatus.textContent = 'PARADO';
                dirStatus.className = 'badge bg-secondary';
            }
        }
    }

    function updateManualButtonBadges() {
        const updateBadge = (buttonId, target) => {
            const button = document.getElementById(buttonId);
            if (!button) return;
            
            const badge = button.querySelector('.badge');
            if (!badge) return;
            
            const isActive = state.actuators[target];
            badge.textContent = isActive ? 'Ligado' : 'Desligado';
            badge.className = `badge ms-2 ${isActive ? 'bg-success' : 'bg-secondary'}`;
            button.className = `btn ${isActive ? 'btn-success' : 'btn-outline-success'}`;
        };
        
        updateBadge('manual-fan-btn', 'ventilador');
        updateBadge('manual-screw-btn', 'motor_rosca');
        updateBadge('manual-cooling-btn', 'ventilacao_resfriador');
    }

    function emitControlEvent(command, payload) {
        socket.emit('control_event', { command, payload });
    }

    // Adicionar Event Listeners para enviar comandos
    settingInputs.forEach(input => {
        input.addEventListener('change', () => {
            emitControlEvent('SET_SETTING', { name: input.id, value: parseFloat(input.value) });
        });
    });

    modeRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            emitControlEvent('SET_SETTING', { name: 'system_mode', value: parseInt(radio.value) });
        });
    });

    heatingBtn.addEventListener('click', () => {
        const newStatus = heatingBtn.dataset.status == '1' ? 0 : 1;
        emitControlEvent('SET_SETTING', { name: 'heating_status', value: newStatus });
    });

    // Controle de velocidade do tambor
    const velocidadeTamborSlider = document.getElementById('velocidade_tambor');
    const velocidadeTamborDisplay = document.getElementById('velocidade_tambor_display');
    const velocidadeTamborRpm = document.getElementById('velocidade_tambor_rpm');
    

    if (velocidadeTamborSlider) {
        velocidadeTamborSlider.addEventListener('input', (e) => {
            const hz = parseInt(e.target.value);
            const rpm = Math.round(hz * 0.3); // 200 passos/volta
            velocidadeTamborDisplay.textContent = `${hz} Hz`;
            velocidadeTamborRpm.textContent = `${rpm} RPM`;
            
            // Atualizar no backend
            emitControlEvent('SET_SETTING', { name: 'velocidade_tambor', value: hz });
        });
    }
    

    manualButtons.forEach(button => {
        const id = button.id;
        const isDrumFwd = id === 'manual-drum-fwd-btn';
        const isDrumRev = id === 'manual-drum-rev-btn';

        button.addEventListener('click', () => {
            if (isDrumFwd) {
                // Enviar comando de rotação forward (toggle)
                emitControlEvent('MANUAL_CONTROL', { target: 'tambor_fwd', state: true });
            } else if (isDrumRev) {
                // Enviar comando de rotação reverse (toggle)
                emitControlEvent('MANUAL_CONTROL', { target: 'tambor_rev', state: true });
            } else {
                // Toggle ventilador ou rosca (comportamento normal)
                const targetMap = {
                    'manual-fan-btn': 'ventilador',
                    'manual-screw-btn': 'motor_rosca',
                    'manual-cooling-btn': 'ventilacao_resfriador'
                };
                const target = targetMap[id];
                if (target && state.actuators) {
                    const currentState = state.actuators[target] || false;
                    emitControlEvent('MANUAL_CONTROL', { target, state: !currentState });
                }
            }
        });
    });

    // Atualizar estado visual dos botões do tambor
    function updateDrumButtons() {
        const fwdBtn = document.getElementById('manual-drum-fwd-btn');
        const revBtn = document.getElementById('manual-drum-rev-btn');
        
        if (fwdBtn && revBtn && state.actuators) {
            const isFwdActive = state.actuators.tambor_pul && state.actuators.tambor_dir && state.actuators.tambor_ena;
            const isRevActive = state.actuators.tambor_pul && !state.actuators.tambor_dir && state.actuators.tambor_ena;
            
            fwdBtn.classList.toggle('active', isFwdActive);
            revBtn.classList.toggle('active', isRevActive);
        }
    }

    // Funções auxiliares da UI
    function toggleManualControls(isManual) {
        // Todos os botões permanecem habilitados (sem desabilitar nada)
        // Mantém a função para compatibilidade, mas não aplica disabled
    }

    function updateHeatingButton(status) {
        heatingBtn.dataset.status = status;
        
        if (status == 1) {
            heatingBtn.classList.remove('btn-danger');
            heatingBtn.classList.add('btn-success');
            heatingBtn.innerHTML = '<i class="fas fa-fire"></i> Aquecimento <span class="badge bg-success ms-2">Ligado</span>';
        } else {
            heatingBtn.classList.remove('btn-success');
            heatingBtn.classList.add('btn-danger');
            heatingBtn.innerHTML = '<i class="fas fa-power-off"></i> Aquecimento <span class="badge bg-secondary ms-2">Desligado</span>';
        }
    }

    function updateManualButton(id, isActive) {
        const button = document.getElementById(id);
        if (button) {
            button.classList.toggle('active', isActive);
        }
    }
});