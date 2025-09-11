// TempPi Dashboard - Detalhes do Sensor

let temperatureChart = null;
let pressureChart = null;
let velocityChart = null;
let autoRefreshInterval = null;

// Carregar dados do sensor
async function loadSensorData(hours = 24) {
    try {
        const data = await fetchAPI(`chart/${encodeURIComponent(sensorName)}?hours=${hours}`);
        
        // Atualizar gráficos
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
            x: d.timestamp,
            y: d.temperature
        }));
    
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
    
    // Atualizar valor atual
    if (temperatureData.length > 0) {
        const current = temperatureData[temperatureData.length - 1].y;
        document.getElementById('temp-current').textContent = formatValue(current);
    }
}

// Atualizar gráfico de pressão
function updatePressureChart(data) {
    const ctx = document.getElementById('pressure-chart');
    if (!ctx) return;
    
    const pressureData = data
        .filter(d => d.pressure !== null)
        .map(d => ({
            x: d.timestamp,
            y: d.pressure
        }));
    
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
    
    // Atualizar valor atual
    if (pressureData.length > 0) {
        const current = pressureData[pressureData.length - 1].y;
        document.getElementById('pressure-current').textContent = formatValue(current);
    }
}

// Atualizar gráfico de velocidade
function updateVelocityChart(data) {
    const ctx = document.getElementById('velocity-chart');
    if (!ctx) return;
    
    const velocityData = data
        .filter(d => d.velocity !== null)
        .map(d => ({
            x: d.timestamp,
            y: d.velocity
        }));
    
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
    
    // Atualizar valor atual
    if (velocityData.length > 0) {
        const current = velocityData[velocityData.length - 1].y;
        document.getElementById('velocity-current').textContent = formatValue(current, '', 0);
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
        }, 10000); // Atualizar a cada 10 segundos
        
        btn.dataset.active = 'true';
        btn.innerHTML = '<i class="fas fa-pause"></i> Auto-refresh';
        btn.classList.add('auto-refresh-active');
        showToast('Auto-refresh ativado (10s)', 'success');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Carregar dados iniciais
    loadSensorData();
    
    // Atualizar gráfico
    document.getElementById('update-chart').addEventListener('click', function() {
        const hours = parseInt(document.getElementById('time-range').value);
        loadSensorData(hours);
        showToast('Gráficos atualizados!', 'success');
    });
    
    // Mudança de período
    document.getElementById('time-range').addEventListener('change', function() {
        const hours = parseInt(this.value);
        loadSensorData(hours);
    });
    
    // Auto-refresh
    document.getElementById('auto-refresh').addEventListener('click', toggleAutoRefresh);
});

// Limpar intervalos quando sair da página
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});
