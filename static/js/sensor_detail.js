// TempPi Dashboard - Detalhes do Sensor

let temperatureChart = null;
let pressureChart = null;
let velocityChart = null;
let autoRefreshInterval = null;
let lastDataCount = 0; // Para evitar atualizações desnecessárias

// Carregar dados do sensor
async function loadSensorData(hours = 24, forceUpdate = false) {
    try {
        // Limitar dados para evitar sobrecarga
        const maxDataPoints = 500;
        const data = await fetchAPI(`chart/${encodeURIComponent(sensorName)}?hours=${hours}&limit=${maxDataPoints}`);
        
        // Verificar se há novos dados (evitar atualização desnecessária)
        if (!forceUpdate && data.length === lastDataCount) {
            console.log('Nenhum dado novo, pulando atualização dos gráficos');
            document.getElementById('last-update').textContent = new Date().toLocaleTimeString('pt-BR');
            return;
        }
        
        lastDataCount = data.length;
        
        // Atualizar gráficos apenas se necessário
        updateTemperatureChart(data);
        updatePressureChart(data);
        updateVelocityChart(data);
        
        // Atualizar estatísticas
        updateSensorStats(data, hours);
        
        // Atualizar dados recentes
        updateRecentData(data.slice(-10)); // Últimos 10 registros
        
        // Atualizar timestamp
        document.getElementById('last-update').textContent = new Date().toLocaleTimeString('pt-BR');
        
    } catch (error) {
        console.error('Erro ao carregar dados do sensor:', error);
        showToast(`Erro ao carregar dados: ${error.message}`, 'danger');
    }
}

// Atualizar gráfico de temperatura
function updateTemperatureChart(data) {
    const ctx = document.getElementById('temperature-chart');
    if (!ctx) return;
    
    const temperatureData = data
        .filter(d => d.temperature !== null)
        .map(d => ({
            x: new Date(d.timestamp).getTime(),
            y: d.temperature
        }))
        .filter(d => !isNaN(d.x));
    
    // Se o gráfico já existe, apenas atualizar os dados
    if (temperatureChart && temperatureChart.data) {
        temperatureChart.data.datasets[0].data = temperatureData;
        temperatureChart.update('none'); // Atualização sem animação para melhor performance
    } else {
        // Criar novo gráfico apenas se não existir
        if (temperatureChart) {
            temperatureChart.destroy();
        }
        
        temperatureChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Temperatura (°C)',
                    data: temperatureData,
                    borderColor: chartColors.temperature,
                    backgroundColor: chartColors.background.temperature,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                ...defaultChartOptions,
                animation: {
                    duration: 0 // Desabilitar animação para melhor performance
                },
                plugins: {
                    ...defaultChartOptions.plugins,
                    title: {
                        display: false
                    }
                },
                scales: {
                    ...defaultChartOptions.scales,
                    y: {
                        ...defaultChartOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Temperatura (°C)'
                        }
                    }
                }
            }
        });
    }
    
    // Atualizar valor atual
    if (temperatureData.length > 0) {
        const current = temperatureData[temperatureData.length - 1].y;
        const tempCurrentEl = document.getElementById('temp-current');
        if (tempCurrentEl) {
            tempCurrentEl.textContent = formatValue(current);
        }
    }
}

// Atualizar gráfico de pressão
function updatePressureChart(data) {
    const ctx = document.getElementById('pressure-chart');
    if (!ctx) return;
    
    const pressureData = data
        .filter(d => d.pressure !== null)
        .map(d => ({
            x: new Date(d.timestamp).getTime(),
            y: d.pressure
        }))
        .filter(d => !isNaN(d.x));
    
    // Se o gráfico já existe, apenas atualizar os dados
    if (pressureChart && pressureChart.data) {
        pressureChart.data.datasets[0].data = pressureData;
        pressureChart.update('none');
    } else {
        if (pressureChart) {
            pressureChart.destroy();
        }
        
        pressureChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Pressão (bar)',
                    data: pressureData,
                    borderColor: chartColors.pressure,
                    backgroundColor: chartColors.background.pressure,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                ...defaultChartOptions,
                animation: {
                    duration: 0
                },
                plugins: {
                    ...defaultChartOptions.plugins,
                    title: {
                        display: false
                    }
                },
                scales: {
                    ...defaultChartOptions.scales,
                    y: {
                        ...defaultChartOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Pressão (bar)'
                        }
                    }
                }
            }
        });
    }
    
    // Atualizar valor atual
    if (pressureData.length > 0) {
        const current = pressureData[pressureData.length - 1].y;
        const pressureCurrentEl = document.getElementById('pressure-current');
        if (pressureCurrentEl) {
            pressureCurrentEl.textContent = formatValue(current);
        }
    }
}

// Atualizar gráfico de velocidade
function updateVelocityChart(data) {
    const ctx = document.getElementById('velocity-chart');
    if (!ctx) return;
    
    const velocityData = data
        .filter(d => d.velocity !== null)
        .map(d => ({
            x: new Date(d.timestamp).getTime(),
            y: d.velocity
        }))
        .filter(d => !isNaN(d.x));
    
    // Se o gráfico já existe, apenas atualizar os dados
    if (velocityChart && velocityChart.data) {
        velocityChart.data.datasets[0].data = velocityData;
        velocityChart.update('none');
    } else {
        if (velocityChart) {
            velocityChart.destroy();
        }
        
        velocityChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Velocidade (rpm)',
                    data: velocityData,
                    borderColor: chartColors.velocity,
                    backgroundColor: chartColors.background.velocity,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                ...defaultChartOptions,
                animation: {
                    duration: 0
                },
                plugins: {
                    ...defaultChartOptions.plugins,
                    title: {
                        display: false
                    }
                },
                scales: {
                    ...defaultChartOptions.scales,
                    y: {
                        ...defaultChartOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Velocidade (rpm)'
                        }
                    }
                }
            }
        });
    }
    
    // Atualizar valor atual
    if (velocityData.length > 0) {
        const current = velocityData[velocityData.length - 1].y;
        const velocityCurrentEl = document.getElementById('velocity-current');
        if (velocityCurrentEl) {
            velocityCurrentEl.textContent = formatValue(current, '', 0);
        }
    }
}

// Atualizar estatísticas do sensor
function updateSensorStats(data, hours) {
    // Extrair valores
    const temperatures = data.map(d => d.temperature).filter(v => v !== null);
    const pressures = data.map(d => d.pressure).filter(v => v !== null);
    const velocities = data.map(d => d.velocity).filter(v => v !== null);
    
    // Calcular estatísticas
    const tempStats = calculateStats(temperatures);
    const pressureStats = calculateStats(pressures);
    const velocityStats = calculateStats(velocities);
    
    // Atualizar elementos
    document.getElementById('temp-avg').textContent = formatValue(tempStats.avg);
    document.getElementById('temp-min').textContent = formatValue(tempStats.min);
    document.getElementById('temp-max').textContent = formatValue(tempStats.max);
    
    document.getElementById('pressure-avg').textContent = formatValue(pressureStats.avg);
    document.getElementById('pressure-min').textContent = formatValue(pressureStats.min);
    document.getElementById('pressure-max').textContent = formatValue(pressureStats.max);
    
    document.getElementById('velocity-avg').textContent = formatValue(velocityStats.avg, '', 0);
    document.getElementById('velocity-min').textContent = formatValue(velocityStats.min, '', 0);
    document.getElementById('velocity-max').textContent = formatValue(velocityStats.max, '', 0);
    
    document.getElementById('data-count').textContent = data.length;
    document.getElementById('data-period').textContent = `${hours}h`;
}

// Atualizar dados recentes
function updateRecentData(recentData) {
    const tbody = document.getElementById('recent-data');
    if (!tbody) return;
    
    if (recentData.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center text-muted">
                    <i class="fas fa-info-circle"></i> Nenhum dado recente
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = recentData
        .reverse() // Mais recente primeiro
        .map(row => `
            <tr>
                <td><small>${formatDateTime(row.timestamp)}</small></td>
                <td>${row.temperature ? formatValue(row.temperature, '°C') : '-'}</td>
                <td>${row.pressure ? formatValue(row.pressure, ' bar') : '-'}</td>
                <td>${row.velocity ? formatValue(row.velocity, ' rpm', 0) : '-'}</td>
                <td>
                    <span class="badge ${row.mode === 'rpi' ? 'bg-success' : 'bg-warning'} badge-sm">
                        ${row.mode === 'rpi' ? 'HW' : 'SIM'}
                    </span>
                </td>
            </tr>
        `).join('');
}

// Alternar auto-refresh
function toggleAutoRefresh() {
    const btn = document.getElementById('auto-refresh');
    const isActive = btn.dataset.active === 'true';
    
    if (isActive) {
        // Parar auto-refresh
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
        btn.dataset.active = 'false';
        btn.innerHTML = '<i class="fas fa-play"></i> Auto-refresh';
        btn.classList.remove('auto-refresh-active');
        showToast('Auto-refresh desativado', 'info');
    } else {
        // Iniciar auto-refresh
        const hours = parseInt(document.getElementById('time-range').value);
        autoRefreshInterval = setInterval(() => {
            loadSensorData(hours);
        }, 30000); // Atualizar a cada 30 segundos
        
        btn.dataset.active = 'true';
        btn.innerHTML = '<i class="fas fa-pause"></i> Auto-refresh';
        btn.classList.add('auto-refresh-active');
        showToast('Auto-refresh ativado (30s)', 'success');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Carregar dados iniciais
    loadSensorData(24, true); // Forçar carregamento inicial
    
    // Atualizar gráfico
    document.getElementById('update-chart').addEventListener('click', function() {
        const hours = parseInt(document.getElementById('time-range').value);
        loadSensorData(hours, true); // Forçar atualização manual
        showToast('Gráficos atualizados!', 'success');
    });
    
    // Mudança de período
    document.getElementById('time-range').addEventListener('change', function() {
        const hours = parseInt(this.value);
        lastDataCount = 0; // Reset contador para forçar recriação dos gráficos
        loadSensorData(hours, true); // Forçar atualização ao mudar período
    });
    
    // Auto-refresh
    document.getElementById('auto-refresh').addEventListener('click', toggleAutoRefresh);
});

// Função para limpar todos os gráficos
function destroyAllCharts() {
    if (temperatureChart) {
        temperatureChart.destroy();
        temperatureChart = null;
    }
    if (pressureChart) {
        pressureChart.destroy();
        pressureChart = null;
    }
    if (velocityChart) {
        velocityChart.destroy();
        velocityChart = null;
    }
}

// Limpar intervalos e gráficos quando sair da página
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    destroyAllCharts();
});
