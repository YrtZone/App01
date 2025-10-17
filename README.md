# Postador Automático para YouTube com IA

Este projeto é uma aplicação web completa desenvolvida para automatizar e otimizar o processo de publicação de vídeos no YouTube. A ferramenta permite que o usuário faça o upload de vídeos, agende a postagem para uma data e hora futuras, e utilize a inteligência artificial do Google Gemini para gerar automaticamente títulos, descrições e hashtags otimizadas.

## Funcionalidades Principais

-   **Painel de Controle Intuitivo:** Uma interface web limpa para gerenciar todo o processo de upload e agendamento.
-   **Geração de Conteúdo com IA:** Integração com a API do Google Gemini para criar metadados de vídeo (títulos, descrições, tags) a partir de um simples resumo.
-   **Agendamento de Vídeos:** Permite programar os uploads para qualquer data e hora, automatizando a consistência de postagem no canal.
-   **Processamento em Segundo Plano:** Utiliza um "worker" separado que roda de forma contínua para verificar a fila e postar os vídeos na hora certa, sem a necessidade de intervenção manual.
-   **Integração Segura com a API do YouTube:** Autenticação via OAuth 2.0 para garantir um acesso seguro à conta do usuário para realizar os uploads.

Tecnologias Utilizadas

-   **Backend:**
    -   Python 3
    -   Flask (para o servidor web e a API)
    -   SQLAlchemy (para comunicação com o banco de dados)
    -   APScheduler (para o robô agendador do worker)
-   **Frontend:**
    -   HTML5
    -   CSS3
    -   JavaScript (Vanilla)
-   **Banco de Dados:**
    -   Microsoft SQL Server
-   **APIs & Serviços:**
    -   YouTube Data API v3
    -   Google Gemini API

Configuração e Instalação

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local.

### 1. Pré-requisitos

-   Python 3.8 ou superior
-   Git
-   Microsoft SQL Server (Express Edition é suficiente)
-   SQL Server Management Studio (SSMS)
