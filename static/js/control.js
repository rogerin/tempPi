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
            tambor_dir: false,
            tambor_pul: false
        }
    };

    // Mapear elementos da UI
    const settingInputs = document.querySelectorAll('#temp-settings-form input, #pressure-time-settings-form input');
    const modeRadios = document.querySelectorAll('input[name="system_mode"]');
    const heatingBtn = document.getElementById('heating-status-btn');
    const manualControls = document.getElementById('manual-controls');
    const manualButtons = document.querySelectorAll('#manual-fan-btn, #manual-screw-btn, #manual-drum-fwd-btn, #manual-drum-rev-btn');

    // Conexão WebSocket
    socket.on('connect', () => {
        console.log('Conectado ao servidor WebSocket!');
        // Solicita os dados mais recentes ao se conectar
        socket.emit('request_initial_data');
        fetchSensorData();
    });

    // Listener para atualizações do backend
    socket.on('update_from_dashboard', (data) => {
        console.log('Update recebido:', data);
        updateUI(data);
    });

    function fetchSensorData() {
        fetch('/api/sensors')
            .then(response => response.json())
            .then(data => {
                console.log('Dados dos sensores recebidos:', data);
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

        // Atualizar modo de operação
        const currentMode = state.settings['system_mode'] || 0;
        const radio = document.querySelector(`input[name="system_mode"][value="${currentMode}"]`);
        if(radio) radio.checked = true;
        toggleManualControls(currentMode == 1);

        // Atualizar botão de aquecimento
        const currentHeatingStatus = state.settings['heating_status'] || 0;
        updateHeatingButton(currentHeatingStatus);

        // Atualizar estado dos botões manuais
        if(currentMode == 1) {
            updateManualButton('manual-fan-btn', state.actuators.ventilador);
            updateManualButton('manual-screw-btn', state.actuators.motor_rosca);
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
            'Temp Saída Gases': 'display_temp_gases'
        };

        Object.entries(sensorMapping).forEach(([sensorName, displayId]) => {
            const element = document.getElementById(displayId);
            if (element && values[sensorName] !== undefined) {
                element.textContent = `${values[sensorName].toFixed(1)} °C`;
            }
        });
    }

    function updateActuatorStatus(actuators) {
        const statusMap = {
            'status_ventilador': actuators.ventilador,
            'status_resistencia': actuators.resistencia,
            'status_motor_rosca': actuators.motor_rosca,
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
    }

    function emitControlEvent(command, payload) {
        console.log(`📤 Enviando comando: ${command}`, payload);
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

    manualButtons.forEach(button => {
        const id = button.id;
        const isDrumFwd = id === 'manual-drum-fwd-btn';
        const isDrumRev = id === 'manual-drum-rev-btn';

        button.addEventListener('click', () => {
            if (isDrumFwd) {
                // Toggle tambor forward
                const isActive = state.actuators?.tambor_pul && state.actuators?.tambor_dir;
                if (isActive) {
                    emitControlEvent('MANUAL_CONTROL', { target: 'tambor_pul', state: false });
                } else {
                    emitControlEvent('MANUAL_CONTROL', { target: 'tambor_dir', state: true });
                    emitControlEvent('MANUAL_CONTROL', { target: 'tambor_pul', state: true });
                }
            } else if (isDrumRev) {
                // Toggle tambor reverse
                const isActive = state.actuators?.tambor_pul && !state.actuators?.tambor_dir;
                if (isActive) {
                    emitControlEvent('MANUAL_CONTROL', { target: 'tambor_pul', state: false });
                } else {
                    emitControlEvent('MANUAL_CONTROL', { target: 'tambor_dir', state: false });
                    emitControlEvent('MANUAL_CONTROL', { target: 'tambor_pul', state: true });
                }
            } else {
                // Toggle ventilador ou rosca
                const targetMap = {
                    'manual-fan-btn': 'ventilador',
                    'manual-screw-btn': 'motor_rosca'
                };
                const target = targetMap[id];
                if (target && state.actuators) {
                    const currentState = state.actuators[target] || false;
                    emitControlEvent('MANUAL_CONTROL', { target, state: !currentState });
                }
            }
        });
    });

    // Funções auxiliares da UI
    function toggleManualControls(isManual) {
        manualControls.classList.toggle('disabled', !isManual);
    }

    function updateHeatingButton(status) {
        heatingBtn.dataset.status = status;
        if (status == 1) {
            heatingBtn.classList.replace('btn-danger', 'btn-success');
            heatingBtn.innerHTML = '<i class="fas fa-check"></i> Aquecimento Ligado';
        } else {
            heatingBtn.classList.replace('btn-success', 'btn-danger');
            heatingBtn.innerHTML = '<i class="fas fa-power-off"></i> Ligar Aquecimento';
        }
    }

    function updateManualButton(id, isActive) {
        const button = document.getElementById(id);
        if (button) {
            button.classList.toggle('active', isActive);
        }
    }
});