// ============================================================================
// SCRIPT.JS - LÓGICA DO FRONTEND PARA O DASHBOARD DE CONTEÚDO
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // --- SELETORES DE ELEMENTOS ---
    // Encontra todos os elementos importantes na página e os armazena em variáveis.
    const authIndicator = document.getElementById('auth-indicator');
    const authText = document.getElementById('auth-text');
    const authButton = document.getElementById('auth-button');
    const submitButton = document.getElementById('submit-button');
    const uploadForm = document.getElementById('upload-form');
    const notificationArea = document.getElementById('notification-area');
    const generateAiButton = document.getElementById('generate-ai-button');
    const agendamentosTableBody = document.querySelector('#agendamentos-table tbody');
    
    // URL base do nosso servidor backend (app.py)
    const API_URL = 'http://localhost:5000';

    // --- FUNÇÕES AUXILIARES ---

    /**
     * Mostra uma notificação temporária na tela.
     * @param {string} message - A mensagem a ser exibida.
     * @param {string} type - O tipo de notificação ('success' ou 'error').
     */
    function showNotification(message, type = 'success') {
        notificationArea.textContent = message;
        notificationArea.className = `notification ${type} show`;
        // Esconde a notificação após 5 segundos
        setTimeout(() => {
            notificationArea.className = 'notification';
        }, 5000);
    }

    // --- FUNÇÕES PRINCIPAIS ---

    /**
     * Função de inicialização: Verifica o status da autenticação e carrega os agendamentos.
     */
    async function initializePage() {
        try {
            const response = await fetch(`${API_URL}/api/auth/status`);
            const data = await response.json();
            if (data.authenticated) {
                authIndicator.className = 'status-indicator connected';
                authText.textContent = 'Conectado';
                authButton.style.display = 'none';
                submitButton.disabled = false;
                loadAgendamentos(); // Carrega a lista de agendamentos se autenticado
            } else {
                authIndicator.className = 'status-indicator disconnected';
                authText.textContent = 'Desconectado';
                authButton.style.display = 'inline-block';
                submitButton.disabled = true;
            }
        } catch (error) {
            authText.textContent = 'Servidor Offline';
            showNotification('Erro ao conectar com o servidor. Verifique se o app.py está rodando.', 'error');
        }
    }

    /**
     * Carrega a lista de agendamentos do backend e preenche a tabela.
     */
    async function loadAgendamentos() {
        try {
            const response = await fetch(`${API_URL}/api/agendamentos`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Erro desconhecido do servidor.');
            }

            agendamentosTableBody.innerHTML = ''; // Limpa a tabela antes de preencher
            if (data.agendamentos.length === 0) {
                agendamentosTableBody.innerHTML = `<tr><td colspan="4" style="text-align: center;">Nenhum vídeo agendado.</td></tr>`;
            } else {
                data.agendamentos.forEach(item => {
                    const row = `
                        <tr>
                            <td>${item.id}</td>
                            <td>${item.titulo}</td>
                            <td>${new Date(item.data_agendamento).toLocaleString('pt-BR')}</td>
                            <td><span class="status-badge status-${item.status}">${item.status}</span></td>
                        </tr>
                    `;
                    agendamentosTableBody.innerHTML += row;
                });
            }
        } catch (error) {
            const friendlyErrorMessage = `<tr><td colspan="4" style="color: red; text-align: center;">Falha ao carregar agendamentos. Verifique a conexão com o banco de dados.</td></tr>`;
            agendamentosTableBody.innerHTML = friendlyErrorMessage;
            console.error("Erro detalhado ao carregar agendamentos:", error);
        }
    }

    // --- EVENT LISTENERS (OUVINTES DE EVENTOS) ---
    // Aqui definimos o que acontece quando o usuário clica nos botões.

    // Evento para o botão de autenticar
    authButton.addEventListener('click', async () => {
        authText.textContent = 'Autenticando...';
        try {
            const response = await fetch(`${API_URL}/api/auth`);
            if (!response.ok) throw new Error((await response.json()).error);
            alert('Autenticação concluída! A página será atualizada.');
            location.reload();
        } catch (error) {
            alert(`Erro na autenticação: ${error.message}`);
            initializePage();
        }
    });

    // Evento para o botão da IA
    generateAiButton.addEventListener('click', async () => {
        const summary = document.getElementById('video-summary').value;
        if (!summary.trim()) {
            showNotification('Por favor, insira um resumo para a IA.', 'error');
            return;
        }
        generateAiButton.disabled = true;
        generateAiButton.textContent = 'Pensando...';
        try {
            const response = await fetch(`${API_URL}/api/generate-content`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ summary }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            document.getElementById('title').value = data.title;
            document.getElementById('description').value = data.description;
            document.getElementById('tags').value = data.tags;
            showNotification('Conteúdo gerado pela IA!', 'success');
        } catch (error) {
            showNotification(`Erro da IA: ${error.message}`, 'error');
        } finally {
            generateAiButton.disabled = false;
            generateAiButton.textContent = '✨ Gerar com IA';
        }
    });
    
    // Evento para o formulário de agendamento
    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // Impede o recarregamento padrão da página
        submitButton.disabled = true;
        submitButton.textContent = 'Agendando...';
        try {
            const response = await fetch(`${API_URL}/api/schedule/youtube`, {
                method: 'POST',
                body: new FormData(uploadForm),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            showNotification(`Vídeo agendado com sucesso! (ID: ${data.id_agendamento})`, 'success');
            uploadForm.reset(); // Limpa o formulário após o sucesso
            loadAgendamentos(); // Atualiza a lista de agendamentos na tela
        } catch (error) {
            showNotification(`Erro ao agendar: ${error.message}`, 'error');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Agendar Vídeo';
        }
    });

    // --- INICIALIZAÇÃO ---
    // Inicia a página e configura uma atualização automática da lista de agendamentos
    initializePage();
    setInterval(loadAgendamentos, 30000); // Atualiza a lista a cada 30 segundos
});