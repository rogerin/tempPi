// TempPi Dashboard - Gráficos e Visualizações

let overviewChart = null;

// Configurações de cores para os gráficos
const chartColors = {
    temperature: '#dc3545',
    pressure: '#007bff',
    velocity: '#28a745',
    background: {
        temperature: 'rgba(220, 53, 69, 0.1)',
        pressure: 'rgba(0, 123, 255, 0.1)',
        velocity: 'rgba(40, 167, 69, 0.1)'
    }
};

// Configuração padrão dos gráficos
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        intersect: false,
        mode: 'index'
    },
    plugins: {
        legend: {
            position: 'top'
        },
        tooltip: {
            backgroundColor: 'rgba(0,0,0,0.8)',
            titleColor: 'white',
            bodyColor: 'white',
            borderColor: '#dee2e6',
            borderWidth: 1
        }
    },
    scales: {
        x: {
            type: 'time',
            time: {
                displayFormats: {
                    hour: 'HH:mm',
                    day: 'DD/MM'
                }
            },
            grid: {
                color: 'rgba(0,0,0,0.1)'
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: 'rgba(0,0,0,0.1)'
            }
        }
    }
};

// Carregar gráfico de overview
async function loadOverviewChart() {
    try {
        const sensors = await fetchAPI('sensors');
        const ctx = document.getElementById('overview-chart');
        
        if (!ctx || sensors.length === 0) return;
        
        // Buscar dados dos primeiros 4 sensores para o overview
        const datasets = [];
        const colors = ['#dc3545', '#007bff', '#28a745', '#ffc107'];
        
        for (let i = 0; i < Math.min(4, sensors.length); i++) {
            const sensorData = await fetchAPI(`chart/${encodeURIComponent(sensors[i])}?hours=24`);
            
            if (sensorData.length > 0) {
                // Determinar qual valor usar baseado no tipo de sensor
                let dataPoints = [];
                let label = sensors[i];
                
                if (sensors[i].includes('Temp') || sensors[i].includes('Torre')) {
                    dataPoints = sensorData.map(d => ({
                        x: d.timestamp,
                        y: d.temperature
                    })).filter(d => d.y !== null);
                    label += ' (°C)';
                } else if (sensors[i].includes('Pressão')) {
                    dataPoints = sensorData.map(d => ({
                        x: d.timestamp,
                        y: d.pressure
                    })).filter(d => d.y !== null);
                    label += ' (bar)';
                } else if (sensors[i].includes('Velocidade')) {
                    dataPoints = sensorData.map(d => ({
                        x: d.timestamp,
                        y: d.velocity
                    })).filter(d => d.y !== null);
                    label += ' (rpm)';
                }
                
                if (dataPoints.length > 0) {
                    datasets.push({
                        label: label,
                        data: dataPoints,
                        borderColor: colors[i],
                        backgroundColor: colors[i] + '20',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4
                    });
                }
            }
        }
        
        // Destruir gráfico anterior se existir
        if (overviewChart) {
            overviewChart.destroy();
        }
        
        // Criar novo gráfico
        overviewChart = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                ...defaultChartOptions,
                plugins: {
                    ...defaultChartOptions.plugins,
                    title: {
                        display: true,
                        text: 'Visão Geral dos Sensores - Últimas 24 Horas'
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar gráfico de overview:', error);
        const ctx = document.getElementById('overview-chart');
        if (ctx) {
            ctx.getContext('2d').fillText('Erro ao carregar gráfico', 10, 50);
        }
    }
}

// Atualizar estatísticas em tempo real
async function updateStats() {
    try {
        const stats = await fetchAPI('stats');
        
        // Atualizar cards de estatísticas se existirem
        const elements = {
            'total_readings': stats.total_readings || 0,
            'readings_24h': stats.readings_24h || 0,
            'sensor_count': Object.keys(stats.sensor_counts || {}).length
        };
        
        Object.entries(elements).forEach(([key, value]) => {
            const element = document.querySelector(`[data-stat="${key}"]`);
            if (element) {
                element.textContent = value.toLocaleString('pt-BR');
            }
        });
        
    } catch (error) {
        console.error('Erro ao atualizar estatísticas:', error);
    }
}

// Função para formatar datas para gráficos
function formatChartDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Calcular estatísticas básicas de um array
function calculateStats(data) {
    if (!data || data.length === 0) {
        return { min: 0, max: 0, avg: 0, count: 0 };
    }
    
    const values = data.filter(v => v !== null && v !== undefined);
    if (values.length === 0) {
        return { min: 0, max: 0, avg: 0, count: 0 };
    }
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    
    return {
        min: parseFloat(min.toFixed(2)),
        max: parseFloat(max.toFixed(2)),
        avg: parseFloat(avg.toFixed(2)),
        count: values.length
    };
}

// Event listeners específicos do dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Carregar gráfico de overview se estivermos na página principal
    if (document.getElementById('overview-chart')) {
        loadOverviewChart();
        
        // Atualizar gráfico a cada 5 minutos
        setInterval(loadOverviewChart, 5 * 60 * 1000);
    }
    
    // Atualizar estatísticas a cada 30 segundos
    updateStats();
    setInterval(updateStats, 30000);
});

// Função para exportar dados do gráfico (placeholder)
function exportChartData(chartId) {
    showToast('Funcionalidade de exportação em desenvolvimento', 'info');
}

// Função para alternar fullscreen do gráfico
function toggleChartFullscreen(chartId) {
    const chartContainer = document.getElementById(chartId).parentElement;
    
    if (!document.fullscreenElement) {
        chartContainer.requestFullscreen().catch(err => {
            console.error('Erro ao entrar em fullscreen:', err);
        });
    } else {
        document.exitFullscreen();
    }
}
