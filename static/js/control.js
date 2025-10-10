document.addEventListener('DOMContentLoaded', function() {
    const socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/web');

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

    function updateUI(state) {
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
    }

    function updateTemperatureDisplays(values) {
        // Mapear nomes dos sensores para IDs dos displays
        const sensorMapping = {
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

    manualButtons.forEach(button => {
        const id = button.id;
        const isDrumFwd = id === 'manual-drum-fwd-btn';
        const isDrumRev = id === 'manual-drum-rev-btn';

        button.addEventListener('mousedown', () => { // Ação imediata
            if (isDrumFwd) {
                emitControlEvent('MANUAL_CONTROL', { target: 'tambor_dir', state: true });
                emitControlEvent('MANUAL_CONTROL', { target: 'tambor_pul', state: true });
            } else if (isDrumRev) {
                emitControlEvent('MANUAL_CONTROL', { target: 'tambor_dir', state: false });
                emitControlEvent('MANUAL_CONTROL', { target: 'tambor_pul', state: true });
            } else {
                const target = id.replace('manual-', '').replace('-btn', '');
                emitControlEvent('MANUAL_CONTROL', { target, state: true });
            }
        });

        const stopDrum = () => {
            if (isDrumFwd || isDrumRev) {
                // Para o pulso do tambor
                emitControlEvent('MANUAL_CONTROL', { target: 'tambor_pul', state: false });
            } else {
                const target = id.replace('manual-', '').replace('-btn', '');
                emitControlEvent('MANUAL_CONTROL', { target, state: false });
            }
        };

        button.addEventListener('mouseup', stopDrum);
        button.addEventListener('mouseleave', stopDrum);
        button.addEventListener('touchend', stopDrum);
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