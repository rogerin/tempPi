// TempPi Sensor Detail - Gráficos e Histórico por Sensor

let temperatureChart = null;
let pressureChart = null;
let velocityChart = null;
let autoRefreshInterval = null;

// Carregar dados do sensor
async function loadSensorData(hours = 24) {
    try {
        const response = await fetch(`/api/sensor/${encodeURIComponent(sensorName)}/data?hours=${hours}`);
        if (!response.ok) throw new Error('Falha ao carregar dados');
        return await response.json();
    } catch (error) {
        console.error('Erro ao carregar dados do sensor:', error);
        showToast(`Erro ao carregar dados: ${error.message}`, 'danger');
        return [];
    }
}

// Renderizar gráfico de temperatura
function renderTemperatureChart(data) {
    const ctx = document.getElementById('temperature-chart');
    if (!ctx) return;

    const tempData = data.filter(d => d.temperature !== null && d.temperature !== undefined);
    if (tempData.length === 0) {
        ctx.parentElement.innerHTML = '<div class="alert alert-info text-center">Nenhum dado de temperatura disponível</div>';
        return;
    }

    const chartData = tempData.map(d => ({
        x: new Date(d.timestamp).getTime(),
        y: d.temperature
    }));

    if (temperatureChart) temperatureChart.destroy();

    temperatureChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Temperatura (°C)',
                data: chartData,
                borderColor: '#dc3545',
                backgroundColor: '#dc354520',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        displayFormats: { hour: 'HH:mm' }
                    }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Temperatura (°C)' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `Temperatura: ${ctx.parsed.y.toFixed(1)}°C`
                    }
                }
            }
        }
    });

    // Atualizar estatísticas
    const current = tempData[tempData.length - 1]?.temperature;
    const avg = tempData.reduce((sum, d) => sum + d.temperature, 0) / tempData.length;
    document.getElementById('temp-current').textContent = current ? current.toFixed(1) : '-';
    document.getElementById('temp-avg').textContent = avg.toFixed(1);
}

// Renderizar gráfico de pressão
function renderPressureChart(data) {
    const ctx = document.getElementById('pressure-chart');
    if (!ctx) return;

    const pressureData = data.filter(d => d.pressure !== null && d.pressure !== undefined);
    if (pressureData.length === 0) {
        ctx.parentElement.innerHTML = '<div class="alert alert-info text-center">Nenhum dado de pressão disponível</div>';
        return;
    }

    const chartData = pressureData.map(d => ({
        x: new Date(d.timestamp).getTime(),
        y: d.pressure
    }));

    if (pressureChart) pressureChart.destroy();

    pressureChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Pressão (bar)',
                data: chartData,
                borderColor: '#007bff',
                backgroundColor: '#007bff20',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        displayFormats: { hour: 'HH:mm' }
                    }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Pressão (bar)' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `Pressão: ${ctx.parsed.y.toFixed(2)} bar`
                    }
                }
            }
        }
    });

    // Atualizar estatísticas
    const current = pressureData[pressureData.length - 1]?.pressure;
    const avg = pressureData.reduce((sum, d) => sum + d.pressure, 0) / pressureData.length;
    document.getElementById('pressure-current').textContent = current ? current.toFixed(2) : '-';
    document.getElementById('pressure-avg').textContent = avg.toFixed(2);
}

// Renderizar gráfico de velocidade
function renderVelocityChart(data) {
    const ctx = document.getElementById('velocity-chart');
    if (!ctx) return;

    const velocityData = data.filter(d => d.velocity !== null && d.velocity !== undefined);
    if (velocityData.length === 0) {
        ctx.parentElement.innerHTML = '<div class="alert alert-info text-center">Nenhum dado de velocidade disponível</div>';
        return;
    }

    const chartData = velocityData.map(d => ({
        x: new Date(d.timestamp).getTime(),
        y: d.velocity
    }));

    if (velocityChart) velocityChart.destroy();

    velocityChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: [{
                label: 'Velocidade (rpm)',
                data: chartData,
                borderColor: '#28a745',
                backgroundColor: '#28a74520',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        displayFormats: { hour: 'HH:mm' }
                    }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Velocidade (rpm)' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => `Velocidade: ${ctx.parsed.y.toFixed(0)} rpm`
                    }
                }
            }
        }
    });

    // Atualizar estatísticas
    const current = velocityData[velocityData.length - 1]?.velocity;
    const avg = velocityData.reduce((sum, d) => sum + d.velocity, 0) / velocityData.length;
    document.getElementById('velocity-current').textContent = current ? current.toFixed(0) : '-';
    document.getElementById('velocity-avg').textContent = avg.toFixed(0);
}

// Calcular e exibir estatísticas
function updateStatistics(data) {
    const tempData = data.filter(d => d.temperature !== null && d.temperature !== undefined);
    const pressureData = data.filter(d => d.pressure !== null && d.pressure !== undefined);
    const velocityData = data.filter(d => d.velocity !== null && d.velocity !== undefined);

    // Temperatura
    if (tempData.length > 0) {
        const temps = tempData.map(d => d.temperature);
        document.getElementById('temp-min').textContent = Math.min(...temps).toFixed(1);
        document.getElementById('temp-max').textContent = Math.max(...temps).toFixed(1);
    }

    // Pressão
    if (pressureData.length > 0) {
        const pressures = pressureData.map(d => d.pressure);
        document.getElementById('pressure-min').textContent = Math.min(...pressures).toFixed(2);
        document.getElementById('pressure-max').textContent = Math.max(...pressures).toFixed(2);
    }

    // Velocidade
    if (velocityData.length > 0) {
        const velocities = velocityData.map(d => d.velocity);
        document.getElementById('velocity-min').textContent = Math.min(...velocities).toFixed(0);
        document.getElementById('velocity-max').textContent = Math.max(...velocities).toFixed(0);
    }

    // Dados gerais
    document.getElementById('data-count').textContent = data.length;
    document.getElementById('data-period').textContent = `${data.length > 0 ? 'Últimas 24h' : 'Nenhum'}`;
}

// Renderizar tabela de dados recentes
function renderRecentData(data) {
    const tbody = document.getElementById('recent-data');
    if (!tbody) return;

    const recentData = data.slice(-10).reverse(); // Últimos 10, mais recentes primeiro
    
    if (recentData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Nenhum dado disponível</td></tr>';
        return;
    }

    tbody.innerHTML = recentData.map(d => {
        const timestamp = new Date(d.timestamp).toLocaleString('pt-BR');
        return `
            <tr>
                <td><small>${timestamp}</small></td>
                <td>${d.temperature !== null ? d.temperature.toFixed(1) + '°C' : '-'}</td>
                <td>${d.pressure !== null ? d.pressure.toFixed(2) + ' bar' : '-'}</td>
                <td>${d.velocity !== null ? d.velocity.toFixed(0) + ' rpm' : '-'}</td>
                <td><span class="badge ${d.mode === 'rpi' ? 'bg-success' : 'bg-warning'}">${d.mode === 'rpi' ? 'Hardware' : 'Simulação'}</span></td>
            </tr>
        `;
    }).join('');
}

// Carregar e renderizar todos os dados
async function loadAndRenderData(hours = 24) {
    const data = await loadSensorData(hours);
    
    renderTemperatureChart(data);
    renderPressureChart(data);
    renderVelocityChart(data);
    updateStatistics(data);
    renderRecentData(data);
    
    // Atualizar timestamp
    document.getElementById('last-update').textContent = new Date().toLocaleString('pt-BR');
}

// Auto-refresh
function toggleAutoRefresh() {
    const btn = document.getElementById('auto-refresh');
    const isActive = btn.dataset.active === 'true';
    
    if (isActive) {
        clearInterval(autoRefreshInterval);
        btn.dataset.active = 'false';
        btn.innerHTML = '<i class="fas fa-play"></i> Auto-refresh';
        btn.classList.remove('btn-danger');
        btn.classList.add('btn-success');
    } else {
        autoRefreshInterval = setInterval(() => loadAndRenderData(), 30000);
        btn.dataset.active = 'true';
        btn.innerHTML = '<i class="fas fa-pause"></i> Parar';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-danger');
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Carregar dados iniciais
    loadAndRenderData();

    // Seletor de período
    document.getElementById('time-range').addEventListener('change', (e) => {
        loadAndRenderData(parseInt(e.target.value));
    });

    // Botão atualizar
    document.getElementById('update-chart').addEventListener('click', () => {
        const hours = parseInt(document.getElementById('time-range').value);
        loadAndRenderData(hours);
    });

    // Auto-refresh
    document.getElementById('auto-refresh').addEventListener('click', toggleAutoRefresh);
});

// Função para mostrar toast (reutilizar do main.js se disponível)
function showToast(message, type = 'info') {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
        return;
    }
    
    // Fallback simples
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentNode) toast.remove();
    }, 5000);
}