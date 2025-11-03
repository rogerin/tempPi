// TempPi All Sensors - Visualização Consolidada de Todos os Sensores
if (window.__ALL_SENSORS_INIT__) {
  console.warn('AllSensors já inicializado');
} else {
  window.__ALL_SENSORS_INIT__ = true;

let allSensorsChart = null;
let autoRefreshInterval = null;
let currentPressureUnit = 'psi'; // 'psi' ou 'bar'
let currentFilters = {
    timeRange: '24',
    startTime: null,
    endTime: null,
    groupBy: 'none',
    selectedSensors: ['temp_forno', 'torre_nivel_1', 'torre_nivel_2', 'torre_nivel_3', 'temp_tanque', 'temp_gases', 'pressao_gases', 'velocity']
};

// Mapeamento de sensores para cores
const sensorColors = {
    'temp_forno': '#e74c3c',
    'torre_nivel_1': '#3498db',
    'torre_nivel_2': '#2ecc71',
    'torre_nivel_3': '#f39c12',
    'temp_tanque': '#9b59b6',
    'temp_gases': '#1abc9c',
    'pressao_gases': '#e67e22',
    'velocity': '#34495e'
};

// Mapeamento de nomes de sensores
const sensorNames = {
    'temp_forno': 'Temp Forno',
    'torre_nivel_1': 'Torre Nível 1',
    'torre_nivel_2': 'Torre Nível 2',
    'torre_nivel_3': 'Torre Nível 3',
    'temp_tanque': 'Temp Tanque',
    'temp_gases': 'Temp Gases',
    'pressao_gases': 'Pressão Gases',
    'velocity': 'Velocidade'
};

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadChart();
});

function initializeEventListeners() {
    // Período
    document.getElementById('time-range').addEventListener('change', function() {
        const isCustom = this.value === 'custom';
        document.getElementById('custom-period').style.display = isCustom ? 'block' : 'none';
        
        if (isCustom) {
            // Definir valores padrão para período customizado
            const now = new Date();
            const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
            
            document.getElementById('end-datetime').value = now.toISOString().slice(0, 16);
            document.getElementById('start-datetime').value = yesterday.toISOString().slice(0, 16);
        }
        
        updateFilters();
    });
    
    // Período customizado
    document.getElementById('start-datetime').addEventListener('change', updateFilters);
    document.getElementById('end-datetime').addEventListener('change', updateFilters);
    
    // Agrupamento
    document.getElementById('group-by').addEventListener('change', updateFilters);
    
    // Sensores
    document.querySelectorAll('.sensor-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateFilters);
    });
    
    // Unidade de pressão
    document.querySelectorAll('input[name="pressure-unit"]').forEach(radio => {
        radio.addEventListener('change', function() {
            currentPressureUnit = this.value;
            loadChart();
        });
    });
    
    // Botões
    document.getElementById('update-chart').addEventListener('click', loadChart);
    document.getElementById('auto-refresh').addEventListener('click', toggleAutoRefresh);
    document.getElementById('export-pdf').addEventListener('click', exportToPDF);
}

function updateFilters() {
    const timeRange = document.getElementById('time-range').value;
    const groupBy = document.getElementById('group-by').value;
    const selectedSensors = Array.from(document.querySelectorAll('.sensor-checkbox:checked')).map(cb => cb.value);
    
    currentFilters.timeRange = timeRange;
    currentFilters.groupBy = groupBy;
    currentFilters.selectedSensors = selectedSensors;
    
    if (timeRange === 'custom') {
        const startTime = document.getElementById('start-datetime').value;
        const endTime = document.getElementById('end-datetime').value;
        currentFilters.startTime = startTime;
        currentFilters.endTime = endTime;
    } else {
        currentFilters.startTime = null;
        currentFilters.endTime = null;
    }
}

// Carregar dados de todos os sensores
async function loadAllSensorsData() {
    try {
        let url = '/api/all-sensors/data?';
        
        if (currentFilters.timeRange === 'custom') {
            url += `start_time=${currentFilters.startTime}&end_time=${currentFilters.endTime}`;
        } else {
            url += `hours=${currentFilters.timeRange}`;
        }
        
        if (currentFilters.groupBy !== 'none') {
            url += `&group_by=${currentFilters.groupBy}`;
        }
        
        const response = await fetch(url);
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

    // Configurar datasets baseado nos sensores selecionados
    const datasets = [];
    
    // Temperaturas (Eixo Y Esquerdo)
    const tempSensors = ['temp_forno', 'torre_nivel_1', 'torre_nivel_2', 'torre_nivel_3', 'temp_tanque', 'temp_gases'];
    tempSensors.forEach(sensor => {
        if (currentFilters.selectedSensors.includes(sensor)) {
            datasets.push({
                label: sensorNames[sensor],
                data: chartData.map(d => ({ x: d.x, y: d[sensor] })).filter(d => d.y !== null),
                borderColor: sensorColors[sensor],
                backgroundColor: sensorColors[sensor] + '20',
                fill: false,
                tension: 0.1,
                yAxisID: 'y'
            });
        }
    });

    // Pressão (Eixo Y Direito)
    if (currentFilters.selectedSensors.includes('pressao_gases')) {
        datasets.push({
            label: 'Pressão Gases',
            data: chartData.map(d => ({ 
                x: d.x, 
                y: currentPressureUnit === 'bar' ? (d.pressao_gases * 0.0689476) : d.pressao_gases 
            })).filter(d => d.y !== null),
            borderColor: sensorColors.pressao_gases,
            backgroundColor: sensorColors.pressao_gases + '20',
            fill: false,
            tension: 0.1,
            yAxisID: 'y1'
        });
    }

    // Velocidade (Eixo Y Esquerdo)
    if (currentFilters.selectedSensors.includes('velocity')) {
        datasets.push({
            label: 'Velocidade',
            data: chartData.map(d => ({ x: d.x, y: d.velocity })).filter(d => d.y !== null),
            borderColor: sensorColors.velocity,
            backgroundColor: sensorColors.velocity + '20',
            fill: false,
            tension: 0.1,
            yAxisID: 'y'
        });
    }

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
                        displayFormats: {
                            hour: 'HH:mm',
                            day: 'DD/MM'
                        }
                    },
                    title: {
                        display: true,
                        text: 'Tempo'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: 'Temperatura (°C) / Velocidade'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: `Pressão (${currentPressureUnit.toUpperCase()})`
                    },
                    grid: {
                        drawOnChartArea: false,
                    },
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return new Date(context[0].parsed.x).toLocaleString('pt-BR');
                        },
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                if (context.dataset.label === 'Pressão Gases') {
                                    label += context.parsed.y.toFixed(2) + ' ' + currentPressureUnit.toUpperCase();
                                } else if (context.dataset.label === 'Velocidade') {
                                    label += context.parsed.y.toFixed(2);
                                } else {
                                    label += context.parsed.y.toFixed(1) + '°C';
                                }
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}

// Carregar gráfico
async function loadChart() {
    try {
        showLoading(true);
        const data = await loadAllSensorsData();
        renderAllSensorsChart(data);
        updateLastUpdateTime();
        showLoading(false);
    } catch (error) {
        console.error('Erro ao carregar gráfico:', error);
        showLoading(false);
    }
}

// Toggle auto-refresh
function toggleAutoRefresh() {
    const button = document.getElementById('auto-refresh');
    const isActive = button.dataset.active === 'true';
    
    if (isActive) {
        clearInterval(autoRefreshInterval);
        button.dataset.active = 'false';
        button.innerHTML = '<i class="fas fa-play"></i> Auto-refresh';
        button.className = 'btn btn-success';
    } else {
        autoRefreshInterval = setInterval(loadChart, 30000); // 30 segundos
        button.dataset.active = 'true';
        button.innerHTML = '<i class="fas fa-pause"></i> Auto-refresh';
        button.className = 'btn btn-warning';
    }
}

// Exportar para PDF
async function exportToPDF() {
    try {
        showLoading(true);
        
        // Preparar dados do filtro
        const filterData = {
            timeRange: currentFilters.timeRange,
            startTime: currentFilters.startTime,
            endTime: currentFilters.endTime,
            groupBy: currentFilters.groupBy,
            selectedSensors: currentFilters.selectedSensors,
            pressureUnit: currentPressureUnit
        };
        
        const response = await fetch('/api/reports/generate-pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filterData)
        });
        
        if (!response.ok) {
            throw new Error('Falha ao gerar PDF');
        }
        
        // Download do PDF
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `relatorio_sensores_${new Date().toISOString().slice(0, 10)}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showToast('PDF gerado com sucesso!', 'success');
        showLoading(false);
        
    } catch (error) {
        console.error('Erro ao exportar PDF:', error);
        showToast(`Erro ao exportar PDF: ${error.message}`, 'danger');
        showLoading(false);
    }
}

// Mostrar/ocultar loading
function showLoading(show) {
    const button = document.getElementById('update-chart');
    if (show) {
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Carregando...';
    } else {
        button.disabled = false;
        button.innerHTML = '<i class="fas fa-sync-alt"></i> Atualizar';
    }
}

// Atualizar timestamp da última atualização
function updateLastUpdateTime() {
    const element = document.getElementById('last-update');
    if (element) {
        element.textContent = new Date().toLocaleString('pt-BR');
    }
}

// Função de toast (se não existir)
function showToast(message, type = 'info') {
    // Usar toast do Bootstrap se disponível
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

} // fim do guard __ALL_SENSORS_INIT__