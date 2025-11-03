// Configurações do Sistema TempPi

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('smtp-config-form');
    const testBtn = document.getElementById('test-smtp');
    const loadBtn = document.getElementById('load-config');
    const testModal = new bootstrap.Modal(document.getElementById('testModal'));
    const resetBtn = document.getElementById('btn-reset-sensor-data');
    const confirm1 = new bootstrap.Modal(document.getElementById('confirmReset1'));
    const confirm2 = new bootstrap.Modal(document.getElementById('confirmReset2'));

    // Carregar configurações existentes
    loadConfig();

    // Event listeners
    form.addEventListener('submit', saveConfig);
    testBtn.addEventListener('click', testSMTP);
    loadBtn.addEventListener('click', loadConfig);
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            confirm1.show();
        });
    }

    const goConfirm2Btn = document.getElementById('go-confirm-2');
    if (goConfirm2Btn) {
        goConfirm2Btn.addEventListener('click', () => {
            confirm1.hide();
            setTimeout(() => confirm2.show(), 200);
        });
    }

    const confirmFinalBtn = document.getElementById('confirm-reset-final');
    if (confirmFinalBtn) {
        confirmFinalBtn.addEventListener('click', async () => {
            try {
                const resp = await fetch('/api/admin/reset-sensor-data', { method: 'POST' });
                const result = await resp.json();
                if (resp.ok && result.success) {
                    showToast(`Dados de sensores apagados: ${result.deleted} registros.`, 'success');
                } else {
                    showToast(result.error || 'Falha ao resetar dados', 'danger');
                }
            } catch (e) {
                showToast('Erro de comunicação ao resetar dados', 'danger');
            } finally {
                confirm2.hide();
            }
        });
    }
    
    // Carregar informações de rede
    loadNetworkInfo();

    async function loadConfig() {
        try {
            const response = await fetch('/api/config/smtp');
            if (response.ok) {
                const config = await response.json();
                
                // Preencher formulário
                document.getElementById('smtp_host').value = config.smtp_host || '';
                document.getElementById('smtp_port').value = config.smtp_port || '';
                document.getElementById('smtp_user').value = config.smtp_user || '';
                document.getElementById('smtp_password').value = config.smtp_password || '';
                document.getElementById('sender_email').value = config.sender_email || '';
                document.getElementById('sender_name').value = config.sender_name || '';
                
                // Atualizar status
                updateStatus(config);
                showToast('Configurações carregadas', 'success');
            } else {
                console.log('Nenhuma configuração encontrada');
            }
        } catch (error) {
            console.error('Erro ao carregar configurações:', error);
            showToast('Erro ao carregar configurações', 'danger');
        }
    }

    async function saveConfig(e) {
        e.preventDefault();
        
        const formData = {
            smtp_host: document.getElementById('smtp_host').value,
            smtp_port: parseInt(document.getElementById('smtp_port').value) || 587,
            smtp_user: document.getElementById('smtp_user').value,
            smtp_password: document.getElementById('smtp_password').value,
            sender_email: document.getElementById('sender_email').value,
            sender_name: document.getElementById('sender_name').value
        };

        // Validação básica
        if (!formData.smtp_host || !formData.smtp_user || !formData.smtp_password) {
            showToast('Preencha pelo menos: Servidor, Usuário e Senha', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/config/smtp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                const result = await response.json();
                showToast('Configurações salvas com sucesso!', 'success');
                updateStatus(formData);
            } else {
                const error = await response.json();
                showToast(`Erro ao salvar: ${error.error}`, 'danger');
            }
        } catch (error) {
            console.error('Erro ao salvar configurações:', error);
            showToast('Erro ao salvar configurações', 'danger');
        }
    }

    async function testSMTP() {
        const formData = {
            smtp_host: document.getElementById('smtp_host').value,
            smtp_port: parseInt(document.getElementById('smtp_port').value) || 587,
            smtp_user: document.getElementById('smtp_user').value,
            smtp_password: document.getElementById('smtp_password').value,
            sender_email: document.getElementById('sender_email').value,
            sender_name: document.getElementById('sender_name').value
        };

        if (!formData.smtp_host || !formData.smtp_user || !formData.smtp_password) {
            showToast('Preencha os campos obrigatórios antes de testar', 'warning');
            return;
        }

        // Mostrar modal de teste
        testModal.show();
        
        // Limpar resultado anterior
        document.getElementById('test-result').innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Testando...</span>
                </div>
                <p class="mt-2">Testando conexão SMTP...</p>
            </div>
        `;

        try {
            const response = await fetch('/api/config/test-smtp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            
            if (response.ok && result.success) {
                document.getElementById('test-result').innerHTML = `
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle"></i>
                        <strong>Sucesso!</strong> Conexão SMTP funcionando corretamente.
                        <br><small>${result.message}</small>
                    </div>
                `;
                updateStatus(formData, true);
            } else {
                document.getElementById('test-result').innerHTML = `
                    <div class="alert alert-danger">
                        <i class="fas fa-times-circle"></i>
                        <strong>Falha!</strong> ${result.error || 'Erro desconhecido'}
                        <br><small>Verifique as configurações e tente novamente.</small>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Erro no teste SMTP:', error);
            document.getElementById('test-result').innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-times-circle"></i>
                    <strong>Erro!</strong> Falha na comunicação com o servidor.
                </div>
            `;
        }
    }

    function updateStatus(config, tested = false) {
        const hasConfig = config.smtp_host && config.smtp_user && config.smtp_password;
        const statusBadge = document.getElementById('smtp-status');
        const lastTest = document.getElementById('last-test');
        
        if (hasConfig) {
            statusBadge.textContent = 'Configurado';
            statusBadge.className = 'badge bg-success ms-2';
        } else {
            statusBadge.textContent = 'Não configurado';
            statusBadge.className = 'badge bg-secondary ms-2';
        }
        
        if (tested) {
            lastTest.textContent = new Date().toLocaleString('pt-BR');
        }
    }

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
}

async function loadNetworkInfo() {
    try {
        const response = await fetch('/api/system/network-info');
        if (response.ok) {
            const info = await response.json();
            
            document.getElementById('server-ip').textContent = info.local_ip;
            document.getElementById('server-url').value = info.url;
        } else {
            document.getElementById('server-ip').textContent = 'Erro ao carregar';
            document.getElementById('server-url').value = 'Erro ao carregar';
        }
    } catch (error) {
        console.error('Erro ao carregar informações de rede:', error);
        document.getElementById('server-ip').textContent = 'Erro ao carregar';
        document.getElementById('server-url').value = 'Erro ao carregar';
    }
}

// Copiar URL para clipboard
document.getElementById('copy-url').addEventListener('click', function() {
    const urlInput = document.getElementById('server-url');
    urlInput.select();
    document.execCommand('copy');
    showToast('URL copiada para a área de transferência!', 'success');
});
