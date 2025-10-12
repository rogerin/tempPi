// TempPi All Sensors - Visualização Consolidada de Todos os Sensores

let allSensorsChart = null;
let autoRefreshInterval = null;
let currentPressureUnit = 'psi'; // 'psi' ou 'bar'

// Carregar dados de todos os sensores
async function loadAllSensorsData(hours = 24) {
    try {
        const response = await fetch(`/api/all-sensors/data?hours=${hours}`);
        if (!response.ok) throw new Error('Falha ao carregar dados');
        return await response.json();
    } catch (error) {
        console.error('Erro ao carregar dados dos sensores:', error);
        showToast(`Erro ao carregar dados: ${error.message}`, 'danger');
        return [];
    }
}

// Renderizar gráfico consolidado
function renderAllSensorsChart(data) {
    const ctx = document.getElementById('all-sensors-chart');
    if (!ctx) return;

    if (data.length === 0) {
        ctx.parentElement.innerHTML = '<div class="alert alert-info text-center">Nenhum dado disponível</div>';
        return;
    }

    // Preparar dados para o gráfico
    const chartData = data.map(d => ({
        x: new Date(d.timestamp).getTime(),
        temp_forno: d.temp_forno,
        torre_nivel_1: d.torre_nivel_1,
        torre_nivel_2: d.torre_nivel_2,
        torre_nivel_3: d.torre_nivel_3,
        temp_tanque: d.temp_tanque,
        temp_gases: d.temp_gases,
        pressao_gases: d.pressao_gases,
        velocity: d.velocity
    }));

    if (allSensorsChart) allSensorsChart.destroy();

    // Configurar datasets
    const datasets = [
        // Temperaturas (Eixo Y Esquerdo)
        {
            label: 'Temp Forno',
            data: chartData.map(d => ({ x: d.x, y: d.temp_forno })).filter(d => d.y !== null),
            borderColor: '#dc3545',
            backgroundColor: '#dc354520',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y'
        },
        {
            label: 'Torre Nível 1',
            data: chartData.map(d => ({ x: d.x, y: d.torre_nivel_1 })).filter(d => d.y !== null),
            borderColor: '#fd7e14',
            backgroundColor: '#fd7e1420',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y'
        },
        {
            label: 'Torre Nível 2',
            data: chartData.map(d => ({ x: d.x, y: d.torre_nivel_2 })).filter(d => d.y !== null),
            borderColor: '#ffc107',
            backgroundColor: '#ffc10720',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y'
        },
        {
            label: 'Torre Nível 3',
            data: chartData.map(d => ({ x: d.x, y: d.torre_nivel_3 })).filter(d => d.y !== null),
            borderColor: '#28a745',
            backgroundColor: '#28a74520',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y'
        },
        {
            label: 'Temp Tanque',
            data: chartData.map(d => ({ x: d.x, y: d.temp_tanque })).filter(d => d.y !== null),
            borderColor: '#17a2b8',
            backgroundColor: '#17a2b820',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y'
        },
        {
            label: 'Temp Gases',
            data: chartData.map(d => ({ x: d.x, y: d.temp_gases })).filter(d => d.y !== null),
            borderColor: '#6f42c1',
            backgroundColor: '#6f42c120',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y'
        },
        // Pressão (Eixo Y Direito)
        {
            label: `Pressão Gases (${currentPressureUnit.toUpperCase()})`,
            data: chartData.map(d => {
                if (d.pressao_gases === null) return null;
                const value = currentPressureUnit === 'bar' ? d.pressao_gases / 14.504 : d.pressao_gases;
                return { x: d.x, y: value };
            }).filter(d => d !== null),
            borderColor: '#007bff',
            backgroundColor: '#007bff20',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            yAxisID: 'y1'
        }
    ];

    allSensorsChart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'hour',
                        displayFormats: { hour: 'HH:mm' }
                    },
                    title: { display: true, text: 'Tempo' }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: { display: true, text: 'Temperatura (°C)' },
                    beginAtZero: true
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: { 
                        display: true, 
                        text: `Pressão (${currentPressureUnit.toUpperCase()})` 
                    },
                    beginAtZero: true,
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                legend: { 
                    display: true,
                    position: 'top',
                    onClick: function(e, legendItem, legend) {
                        const index = legendItem.datasetIndex;
                        const chart = legend.chart;
                        const meta = chart.getDatasetMeta(index);
                        meta.hidden = meta.hidden === null ? !chart.data.datasets[index].hidden : null;
                        chart.update();
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y;
                            
                            if (label.includes('Pressão')) {
                                return `${label}: ${value.toFixed(2)} ${currentPressureUnit.toUpperCase()}`;
                            } else if (label.includes('Temp') || label.includes('Torre')) {
                                return `${label}: ${value.toFixed(1)}°C`;
                            } else {
                                return `${label}: ${value.toFixed(1)}`;
                            }
                        }
                    }
                }
            }
        }
    });

    // Atualizar estatísticas
    updateCurrentValues(data);
    renderRecentData(data);
}

// Atualizar valores atuais
function updateCurrentValues(data) {
    if (data.length === 0) return;
    
    const latest = data[data.length - 1];
    
    // Temperaturas
    document.getElementById('temp-forno-current').textContent = 
        latest.temp_forno ? `${latest.temp_forno.toFixed(1)}°C` : '-';
    document.getElementById('torre-1-current').textContent = 
        latest.torre_nivel_1 ? `${latest.torre_nivel_1.toFixed(1)}°C` : '-';
    document.getElementById('torre-2-current').textContent = 
        latest.torre_nivel_2 ? `${latest.torre_nivel_2.toFixed(1)}°C` : '-';
    document.getElementById('torre-3-current').textContent = 
        latest.torre_nivel_3 ? `${latest.torre_nivel_3.toFixed(1)}°C` : '-';
    document.getElementById('temp-tanque-current').textContent = 
        latest.temp_tanque ? `${latest.temp_tanque.toFixed(1)}°C` : '-';
    document.getElementById('temp-gases-current').textContent = 
        latest.temp_gases ? `${latest.temp_gases.toFixed(1)}°C` : '-';
    
    // Pressão
    const pressureValue = latest.pressao_gases;
    if (pressureValue !== null) {
        const displayValue = currentPressureUnit === 'bar' 
            ? (pressureValue / 14.504).toFixed(3)
            : pressureValue.toFixed(2);
        document.getElementById('pressao-current').textContent = 
            `${displayValue} ${currentPressureUnit.toUpperCase()}`;
    } else {
        document.getElementById('pressao-current').textContent = '-';
    }
    
    // Velocidade
    document.getElementById('velocity-current').textContent = 
        latest.velocity ? `${latest.velocity.toFixed(0)} rpm` : '-';
    
    // Modo
    document.getElementById('mode-current').textContent = 
        latest.mode === 'rpi' ? 'Hardware' : 'Simulação';
}

// Renderizar tabela de dados recentes
function renderRecentData(data) {
    const tbody = document.getElementById('recent-data');
    if (!tbody) return;

    const recentData = data.slice(-10).reverse(); // Últimos 10, mais recentes primeiro
    
    if (recentData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted">Nenhum dado disponível</td></tr>';
        return;
    }

    tbody.innerHTML = recentData.map(d => {
        const timestamp = new Date(d.timestamp).toLocaleString('pt-BR');
        
        // Converter pressão se necessário
        let pressureDisplay = '-';
        if (d.pressao_gases !== null) {
            const value = currentPressureUnit === 'bar' 
                ? (d.pressao_gases / 14.504).toFixed(3)
                : d.pressao_gases.toFixed(2);
            pressureDisplay = `${value} ${currentPressureUnit.toUpperCase()}`;
        }
        
        return `
            <tr>
                <td><small>${timestamp}</small></td>
                <td>${d.temp_forno !== null ? d.temp_forno.toFixed(1) + '°C' : '-'}</td>
                <td>${d.torre_nivel_1 !== null ? d.torre_nivel_1.toFixed(1) + '°C' : '-'}</td>
                <td>${d.torre_nivel_2 !== null ? d.torre_nivel_2.toFixed(1) + '°C' : '-'}</td>
                <td>${d.torre_nivel_3 !== null ? d.torre_nivel_3.toFixed(1) + '°C' : '-'}</td>
                <td>${d.temp_tanque !== null ? d.temp_tanque.toFixed(1) + '°C' : '-'}</td>
                <td>${d.temp_gases !== null ? d.temp_gases.toFixed(1) + '°C' : '-'}</td>
                <td>${pressureDisplay}</td>
                <td>${d.velocity !== null ? d.velocity.toFixed(0) + ' rpm' : '-'}</td>
                <td><span class="badge ${d.mode === 'rpi' ? 'bg-success' : 'bg-warning'}">${d.mode === 'rpi' ? 'Hardware' : 'Simulação'}</span></td>
            </tr>
        `;
    }).join('');
}

// Carregar e renderizar todos os dados
async function loadAndRenderData(hours = 24) {
    const data = await loadAllSensorsData(hours);
    renderAllSensorsChart(data);
    
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

// Função para mostrar toast
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

    // Toggle PSI/BAR
    document.querySelectorAll('input[name="pressure-unit"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentPressureUnit = e.target.value;
            // Recarregar dados para atualizar o gráfico
            const hours = parseInt(document.getElementById('time-range').value);
            loadAndRenderData(hours);
        });
    });
});
