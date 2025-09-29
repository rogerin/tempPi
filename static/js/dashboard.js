// TempPi Dashboard - Gráficos e Visualizações
// (Configurações globais estão em main.js)

let overviewChart = null;
let averageTempChart = null;

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
                        x: new Date(d.timestamp).getTime(),
                        y: d.temperature
                    })).filter(d => d.y !== null && !isNaN(d.x));
                    label += ' (°C)';
                } else if (sensors[i].includes('Pressão')) {
                    dataPoints = sensorData.map(d => ({
                        x: new Date(d.timestamp).getTime(),
                        y: d.pressure
                    })).filter(d => d.y !== null && !isNaN(d.x));
                    label += ' (bar)';
                } else if (sensors[i].includes('Velocidade')) {
                    dataPoints = sensorData.map(d => ({
                        x: new Date(d.timestamp).getTime(),
                        y: d.velocity
                    })).filter(d => d.y !== null && !isNaN(d.x));
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
        
        // Verificar se há dados para mostrar
        if (datasets.length === 0) {
            const canvas = document.getElementById('overview-chart');
            if (canvas) {
                const container = canvas.parentElement;
                container.innerHTML = `
                    <div class="alert alert-info text-center">
                        <i class="fas fa-info-circle"></i>
                        <h6>Aguardando dados dos sensores</h6>
                        <p class="mb-0">
                            <small>Execute o dashboard principal para começar a coletar dados.</small>
                        </p>
                        <div class="mt-2">
                            <code>python3 dashboard.py --img assets/base.jpeg</code>
                        </div>
                    </div>
                `;
            }
            return;
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
        
        // Mostrar mensagem de erro amigável
        const canvas = document.getElementById('overview-chart');
        if (canvas) {
            const container = canvas.parentElement;
            container.innerHTML = `
                <div class="alert alert-warning text-center">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h6>Gráfico temporariamente indisponível</h6>
                    <p class="mb-0">
                        <small>Execute o dashboard para gerar dados ou aguarde alguns minutos.</small>
                    </p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="loadOverviewChart()">
                        <i class="fas fa-sync-alt"></i> Tentar novamente
                    </button>
                </div>
            `;
        }
    }
}

// Carregar gráfico de média de temperatura
async function loadAverageTempChart() {
    try {
        const ctx = document.getElementById('average-temp-chart');
        if (!ctx) return;

        const avgData = await fetchAPI('chart/average_temperature?hours=24');

        if (avgData.length === 0) {
            // Mensagem se não houver dados
            return;
        }

        const dataPoints = avgData.map(d => ({
            x: new Date(d.timestamp).getTime(),
            y: d.temperature
        }));

        const dataset = {
            label: 'Média de Temperatura (°C)',
            data: dataPoints,
            borderColor: '#ff6384',
            backgroundColor: '#ff638420',
            borderWidth: 2,
            fill: true,
            tension: 0.4
        };

        if (averageTempChart) {
            averageTempChart.destroy();
        }

        averageTempChart = new Chart(ctx, {
            type: 'line',
            data: { datasets: [dataset] },
            options: {
                ...defaultChartOptions,
                plugins: {
                    ...defaultChartOptions.plugins,
                    title: {
                        display: true,
                        text: 'Média de Temperatura - Últimas 24 Horas'
                    }
                }
            }
        });

    } catch (error) {
        console.error('Erro ao carregar gráfico de média de temperatura:', error);
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

// Função calculateStats agora está em main.js (global)

// Event listeners específicos do dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Carregar gráfico de overview se estivermos na página principal
    if (document.getElementById('overview-chart')) {
        loadOverviewChart();
        loadAverageTempChart();
        
        // Atualizar gráfico a cada 5 minutos
        setInterval(loadOverviewChart, 5 * 60 * 1000);
        setInterval(loadAverageTempChart, 5 * 60 * 1000);
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
