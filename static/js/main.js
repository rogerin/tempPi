// TempPi Dashboard - JavaScript Principal

// Configurações globais
const API_BASE = '';
let currentPage = 1;
let currentFilters = {};

// Utilitários
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('pt-BR');
}

function formatValue(value, unit = '') {
    if (value === null || value === undefined) return '-';
    return `${parseFloat(value).toFixed(2)}${unit}`;
}

function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showToast(message, type = 'info') {
    // Criar toast dinâmico
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remover após 5 segundos
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 5000);
}

// API Calls
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}/api/${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showToast(`Erro na API: ${error.message}`, 'danger');
        throw error;
    }
}

// Carregar lista de sensores no dropdown
async function loadSensorsDropdown() {
    try {
        const sensors = await fetchAPI('sensors');
        const dropdown = document.getElementById('sensors-dropdown');
        
        if (dropdown) {
            dropdown.innerHTML = '';
            sensors.forEach(sensor => {
                const li = document.createElement('li');
                li.innerHTML = `
                    <a class="dropdown-item" href="/sensor/${encodeURIComponent(sensor)}">
                        <i class="fas fa-thermometer-half"></i> ${sensor}
                    </a>
                `;
                dropdown.appendChild(li);
            });
        }
    } catch (error) {
        console.error('Erro ao carregar sensores:', error);
    }
}

// Carregar dados com filtros e paginação
async function loadData(page = 1, filters = {}) {
    showLoading();
    
    try {
        // Construir query string
        const params = new URLSearchParams({
            page: page,
            per_page: 50,
            ...filters
        });
        
        const data = await fetchAPI(`data?${params}`);
        
        // Atualizar tabela
        updateDataTable(data.data);
        
        // Atualizar paginação
        updatePagination(data.page, data.total_pages, data.total);
        
        currentPage = page;
        currentFilters = filters;
        
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        document.getElementById('data-table').innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle"></i> 
                    Erro ao carregar dados: ${error.message}
                </td>
            </tr>
        `;
    } finally {
        hideLoading();
    }
}

// Atualizar tabela de dados
function updateDataTable(data) {
    const tbody = document.getElementById('data-table');
    
    if (!data || data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    <i class="fas fa-info-circle"></i> 
                    Nenhum dado encontrado
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = data.map(row => `
        <tr>
            <td>
                <small>${formatDateTime(row.timestamp)}</small>
            </td>
            <td>
                <a href="/sensor/${encodeURIComponent(row.sensor_name)}" class="text-decoration-none">
                    <strong>${row.sensor_name}</strong>
                </a>
            </td>
            <td>
                ${row.temperature ? `<span class="badge bg-danger">${formatValue(row.temperature, '°C')}</span>` : '-'}
            </td>
            <td>
                ${row.pressure ? `<span class="badge bg-primary">${formatValue(row.pressure, ' bar')}</span>` : '-'}
            </td>
            <td>
                ${row.velocity ? `<span class="badge bg-success">${formatValue(row.velocity, ' rpm')}</span>` : '-'}
            </td>
            <td>
                <span class="badge bg-secondary">${row.sensor_type}</span>
            </td>
            <td>
                <span class="badge ${row.mode === 'rpi' ? 'bg-success' : 'bg-warning'}">
                    ${row.mode === 'rpi' ? 'Hardware' : 'Simulação'}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-info" onclick="showRowDetails(${row.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Atualizar paginação
function updatePagination(currentPage, totalPages, totalItems) {
    const pagination = document.getElementById('pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    let paginationHTML = '';
    
    // Botão Anterior
    if (currentPage > 1) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadData(${currentPage - 1}, currentFilters)">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
    }
    
    // Páginas
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadData(1, currentFilters)">1</a>
            </li>
        `;
        if (startPage > 2) {
            paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="loadData(${i}, currentFilters)">${i}</a>
            </li>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadData(${totalPages}, currentFilters)">${totalPages}</a>
            </li>
        `;
    }
    
    // Botão Próximo
    if (currentPage < totalPages) {
        paginationHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadData(${currentPage + 1}, currentFilters)">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
    }
    
    pagination.innerHTML = paginationHTML;
    
    // Mostrar informações
    const info = document.createElement('small');
    info.className = 'text-muted d-block text-center mt-2';
    info.textContent = `Mostrando página ${currentPage} de ${totalPages} (${totalItems} registros total)`;
    pagination.parentNode.appendChild(info);
}

// Mostrar detalhes de uma linha
function showRowDetails(id) {
    showToast(`Detalhes do registro ${id} (funcionalidade em desenvolvimento)`, 'info');
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Carregar dropdown de sensores
    loadSensorsDropdown();
    
    // Carregar dados iniciais
    if (document.getElementById('data-table')) {
        loadData();
    }
    
    // Filtros
    const filterForm = document.getElementById('filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const filters = {};
            const sensor = document.getElementById('sensor-filter').value;
            const startDate = document.getElementById('start-date').value;
            const endDate = document.getElementById('end-date').value;
            
            if (sensor) filters.sensor = sensor;
            if (startDate) filters.start_date = startDate;
            if (endDate) filters.end_date = endDate;
            
            loadData(1, filters);
        });
    }
    
    // Limpar filtros
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            document.getElementById('sensor-filter').value = '';
            document.getElementById('start-date').value = '';
            document.getElementById('end-date').value = '';
            loadData(1, {});
        });
    }
    
    // Atualizar dados
    const refreshBtn = document.getElementById('refresh-data');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadData(currentPage, currentFilters);
            showToast('Dados atualizados!', 'success');
        });
    }
    
    // Exportar dados (placeholder)
    const exportBtn = document.getElementById('export-data');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            showToast('Funcionalidade de exportação em desenvolvimento', 'info');
        });
    }
});

// Atualização automática a cada 30 segundos
setInterval(() => {
    if (document.getElementById('data-table')) {
        loadData(currentPage, currentFilters);
    }
}, 30000);
