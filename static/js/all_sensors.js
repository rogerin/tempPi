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

    // Paginação
    let allData = [];
    let currentPage = 1;
    const itemsPerPage = 50;

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

    // Intervalos de atualização
    let currentValuesInterval = null;
    let recentDataInterval = null;

    // Inicialização
    document.addEventListener('DOMContentLoaded', function () {
        initializeEventListeners();
        loadChart();
        loadCurrentValues();
        // loadRecentData(); // Substituído por renderPaginatedTable dentro de loadChart

        // Atualizar valores atuais a cada 5 segundos
        currentValuesInterval = setInterval(loadCurrentValues, 5000);

        // Auto-refresh removido por padrão (controlado pelo botão)
    });

    function initializeEventListeners() {
        // Período
        document.getElementById('time-range').addEventListener('change', function () {
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
            radio.addEventListener('change', function () {
                currentPressureUnit = this.value;
                updateFilters(); // Atualizar filtros
                loadChart();
            });
        });

        // Botões
        document.getElementById('update-chart').addEventListener('click', loadChart);
        document.getElementById('auto-refresh').addEventListener('click', toggleAutoRefresh);

        // Dropdown de relatório
        const downloadBtn = document.getElementById('export-pdf-download');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', function (e) {
                e.preventDefault();
                openReportModal('download');
            });
        }

        const emailBtn = document.getElementById('export-pdf-email');
        if (emailBtn) {
            emailBtn.addEventListener('click', function (e) {
                e.preventDefault();
                openReportModal('email');
            });
        }

        // Botões dentro do Modal
        const btnDownloadPdf = document.getElementById('btn-download-pdf');
        if (btnDownloadPdf) {
            btnDownloadPdf.addEventListener('click', exportToPDF);
        }

        const btnSendEmail = document.getElementById('btn-send-email');
        if (btnSendEmail) {
            btnSendEmail.addEventListener('click', sendEmailReport);
        }



        // Paginação
        document.getElementById('prev-page').addEventListener('click', (e) => {
            e.preventDefault();
            if (currentPage > 1) {
                renderPaginatedTable(currentPage - 1);
            }
        });

        document.getElementById('next-page').addEventListener('click', (e) => {
            e.preventDefault();
            const totalPages = Math.ceil(allData.length / itemsPerPage);
            if (currentPage < totalPages) {
                renderPaginatedTable(currentPage + 1);
            }
        });

        // Excel/CSV
        const exportExcelBtn = document.getElementById('export-excel');
        if (exportExcelBtn) {
            exportExcelBtn.addEventListener('click', function (e) {
                e.preventDefault();
                let url = '/api/readings/export?';

                if (currentFilters.timeRange === 'custom') {
                    url += `start=${currentFilters.startTime}&end=${currentFilters.endTime}`;
                } else {
                    const hours = parseInt(currentFilters.timeRange || 24);
                    const end = new Date();
                    const start = new Date(end.getTime() - (hours * 60 * 60 * 1000));

                    const formatDate = (date) => {
                        const pad = (n) => n < 10 ? '0' + n : n;
                        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
                    };

                    url += `start=${formatDate(start)}&end=${formatDate(end)}`;
                }
                window.location.href = url;
            });
        }
    }

    function updateFilters() {
        const timeRange = document.getElementById('time-range').value;
        const groupBy = document.getElementById('group-by').value;
        const selectedSensors = Array.from(document.querySelectorAll('.sensor-checkbox:checked')).map(cb => cb.value);

        const pressureUnit = document.querySelector('input[name="pressure-unit"]:checked').value;

        currentFilters.timeRange = timeRange;
        currentFilters.groupBy = groupBy;
        currentFilters.selectedSensors = selectedSensors;
        currentFilters.pressureUnit = pressureUnit;

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

        // Limitar aos últimos 10000 registros para evitar travamento, mas mostrar histórico suficiente
        // Se o usuário pedir agrupamento de 2s em 2 dias, ainda será cortado, mas 100 era muito pouco.
        // O ideal seria downsampling no front, mas vamos aumentar o limite primeiro.
        const limitedData = chartData.slice(-10000);

        if (allSensorsChart) allSensorsChart.destroy();

        // Configurar datasets baseado nos sensores selecionados
        const datasets = [];

        // Temperaturas (Eixo Y Esquerdo)
        const tempSensors = ['temp_forno', 'torre_nivel_1', 'torre_nivel_2', 'torre_nivel_3', 'temp_tanque', 'temp_gases'];
        tempSensors.forEach(sensor => {
            if (currentFilters.selectedSensors.includes(sensor)) {
                datasets.push({
                    label: sensorNames[sensor],
                    data: limitedData.map(d => ({ x: d.x, y: d[sensor] })).filter(d => d.y !== null),
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
                data: limitedData.map(d => ({
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
                data: limitedData.map(d => ({ x: d.x, y: d.velocity })).filter(d => d.y !== null),
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
                            title: function (context) {
                                return new Date(context[0].parsed.x).toLocaleString('pt-BR');
                            },
                            label: function (context) {
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

            // Armazenar e renderizar tabela (ordem decrescente)
            allData = [...data].reverse();
            renderPaginatedTable(1);

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
            updateFilters(); // Garantir filtros atualizados
            const btn = document.getElementById('btn-download-pdf');
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Gerando...';

            // Preparar dados com metadados
            const payload = getReportPayload();

            const response = await fetch('/api/reports/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error('Falha ao gerar PDF');
            }

            // Download do PDF
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `relatorio_${getReportSlug()}_${new Date().toISOString().slice(0, 10)}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            showToast('PDF gerado com sucesso!', 'success');

            // Fechar modal após sucesso
            const reportModal = bootstrap.Modal.getInstance(document.getElementById('reportModal'));
            if (reportModal) reportModal.hide();

        } catch (error) {
            console.error('Erro ao exportar PDF:', error);
            showToast(`Erro ao exportar PDF: ${error.message}`, 'danger');
        } finally {
            const btn = document.getElementById('btn-download-pdf');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
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

    // Carregar valores atuais
    async function loadCurrentValues() {
        try {
            const response = await fetch('/api/all-sensors/latest');
            if (!response.ok) throw new Error('Falha ao carregar valores atuais');

            const data = await response.json();

            // Atualizar valores de temperatura
            updateElement('temp-forno-current', data.temp_forno, '°C');
            updateElement('torre-1-current', data.torre_nivel_1, '°C');
            updateElement('torre-2-current', data.torre_nivel_2, '°C');
            updateElement('torre-3-current', data.torre_nivel_3, '°C');
            updateElement('temp-tanque-current', data.temp_tanque, '°C');
            updateElement('temp-gases-current', data.temp_gases, '°C');

            // Atualizar pressão (com conversão de unidade se necessário)
            if (data.pressao_gases !== null) {
                const pressao = currentPressureUnit === 'bar'
                    ? (data.pressao_gases * 0.0689476).toFixed(2)
                    : data.pressao_gases.toFixed(2);
                document.getElementById('pressao-current').textContent =
                    `${pressao} ${currentPressureUnit.toUpperCase()}`;
            } else {
                document.getElementById('pressao-current').textContent = '- PSI';
            }

            // Atualizar velocidade
            updateElement('velocity-current', data.velocity, ' rpm');

            // Atualizar modo
            const modeElement = document.getElementById('mode-current');
            if (modeElement) {
                modeElement.textContent = data.mode === 1 ? 'Manual' : 'Automático';
            }

        } catch (error) {
            console.error('Erro ao carregar valores atuais:', error);
        }
    }

    // Helper para atualizar elementos
    function updateElement(id, value, unit = '') {
        const element = document.getElementById(id);
        if (element) {
            if (value !== null && value !== undefined) {
                element.textContent = `${value}${unit}`;
            } else {
                element.textContent = `-${unit}`;
            }
        }
    }

    // Carregar dados recentes
    // Renderizar Tabela Paginada
    function renderPaginatedTable(page) {
        currentPage = page;
        const tbody = document.getElementById('sensors-data-table-body');
        const start = (page - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const paginatedData = allData.slice(start, end);

        if (!tbody) return;

        if (paginatedData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center">Nenhum dado disponível</td></tr>';
            updatePaginationInfo(0);
            return;
        }

        tbody.innerHTML = paginatedData.map(row => {
            const timestamp = new Date(row.timestamp).toLocaleString('pt-BR');
            // Pressão
            let pressaoVal = row.pressao_gases;
            let pressaoUnit = ' PSI';
            if (currentPressureUnit === 'bar' && pressaoVal !== null) {
                pressaoVal = pressaoVal * 0.0689476;
                pressaoUnit = ' BAR';
            }

            return `
            <tr>
                <td>${timestamp}</td>
                <td>${formatValue(row.temp_forno, '°C')}</td>
                <td>${formatValue(row.torre_nivel_1, '°C')}</td>
                <td>${formatValue(row.torre_nivel_2, '°C')}</td>
                <td>${formatValue(row.torre_nivel_3, '°C')}</td>
                <td>${formatValue(row.temp_tanque, '°C')}</td>
                <td>${formatValue(row.temp_gases, '°C')}</td>
                <td>${formatValue(pressaoVal, pressaoUnit, 2)}</td>
                <td>${formatValue(row.velocity, ' rpm', 0)}</td>
            </tr>
        `;
        }).join('');

        updatePaginationInfo(allData.length);
    }

    function updatePaginationInfo(totalItems) {
        const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
        const display = document.getElementById('current-page-display');
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');

        if (display) {
            display.innerHTML = `Página ${currentPage} de ${totalPages} <span class="text-muted small ms-1">(${totalItems} registros)</span>`;
        }

        if (prevBtn) {
            if (currentPage <= 1) prevBtn.parentElement.classList.add('disabled');
            else prevBtn.parentElement.classList.remove('disabled');
        }

        if (nextBtn) {
            if (currentPage >= totalPages) nextBtn.parentElement.classList.add('disabled');
            else nextBtn.parentElement.classList.remove('disabled');
        }
    }
    // formatValue helper atualizado
    function formatValue(value, unit = '', decimals = 1) {
        if (value === null || value === undefined) {
            return '-';
        }
        try {
            if (typeof value === 'number') {
                return `${value.toFixed(decimals)}${unit}`;
            }
            return `${value}${unit}`;
        } catch (e) {
            return `${value}${unit}`;
        }
    }

    // Helper para formatar valores
    function formatValue(value, unit = '') {
        if (value === null || value === undefined) {
            return '-';
        }
        return `${value}${unit}`;
    }

    // Abrir modal de relatório
    function openReportModal(tab = 'download') {
        const reportModalEl = document.getElementById('reportModal');
        const reportModal = new bootstrap.Modal(reportModalEl);

        // Ativar a tab correta
        const triggerEl = document.querySelector(`#reportTabs button[data-bs-target="#${tab}-content"]`);
        bootstrap.Tab.getInstance(triggerEl) || new bootstrap.Tab(triggerEl).show();

        reportModal.show();
    }

    // Obter payload unificado
    function getReportPayload() {
        return {
            ...currentFilters,
            operation_name: document.getElementById('report-operation-name').value.trim(),
            comments: document.getElementById('report-comments').value.trim(),
            pressureUnit: currentPressureUnit
        };
    }

    // Helper para slug do arquivo
    function getReportSlug() {
        const opName = document.getElementById('report-operation-name').value.trim();
        if (opName) return opName.toLowerCase().replace(/[^a-z0-9]+/g, '_');
        return 'sensores';
    }

    // Enviar relatório por email
    async function sendEmailReport() {
        const recipient = document.getElementById('email-recipient').value.trim();

        if (!recipient) {
            showToast('Informe o email do destinatário', 'warning');
            return;
        }

        // Validação básica de email
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(recipient)) {
            showToast('Email inválido', 'warning');
            return;
        }

        updateFilters();

        const payload = {
            ...getReportPayload(),
            recipient_email: recipient,
            recipient_name: document.getElementById('email-recipient-name').value.trim(),
            // message já está incluso se usarmos os campos do modal, mas o backend espera 'message' no corpo do email?
            // O backend usa 'message' para o corpo do email. Vamos usar o campo 'Comentários' como message ou adicionar um campo específico?
            // O usuário pediu "comentarios" no PDF.
            // Vou manter a estrutura atual do backend que espera 'message' para o corpo.
            // Mas o modal tem "Comentários" para o PDF.
            // O ideal seria usar o comentário no PDF E no corpo do email? 
            // Vamos usar o campo 'Comentários' para o PDF (metadado) e se quiser mensagem no corpo, pode ser o mesmo ou nada.
            // O layout do backend usa 'message' para o corpo. 
            // Vamos usar os comentários como mensagem também se não houver um campo "Mensagem" separado.
            // No HTML removi "Mensagem Adicional" e deixei "Comentários".
            message: document.getElementById('report-comments').value.trim()
        };

        const sendBtn = document.getElementById('btn-send-email');
        const originalText = sendBtn.innerHTML;
        sendBtn.disabled = true;
        sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';

        try {
            const response = await fetch('/api/reports/send-consolidated-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showToast(result.message || 'Email enviado com sucesso!', 'success');
                const reportModal = bootstrap.Modal.getInstance(document.getElementById('reportModal'));
                if (reportModal) reportModal.hide();
            } else {
                showToast(result.error || 'Erro ao enviar email', 'danger');
            }
        } catch (error) {
            console.error('Erro ao enviar email:', error);
            showToast('Erro ao enviar email.', 'danger');
        } finally {
            sendBtn.disabled = false;
            sendBtn.innerHTML = originalText;
        }
    }

    // Função de toast (se não existir)
    // Evita recursão quando existir showToast global
    function showToast(message, type = 'info') {
        if (typeof window.showToast === 'function' && window.showToast !== showToast) {
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
        setTimeout(() => { if (toast.parentNode) toast.remove(); }, 5000);
    }

} // fim do guard __ALL_SENSORS_INIT__