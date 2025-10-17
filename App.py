# ============================================================================
# SISTEMA COMPLETO DE UPLOAD PARA YOUTUBE COM AGENDAMENTO E IA
# ============================================================================

# ----------------------------------------------------------------------------
# 1. INSTALAÇÃO DAS DEPENDÊNCIAS (rodar no terminal):
# ----------------------------------------------------------------------------
# pip install flask flask-cors google-api-python-client google-auth-oauthlib google-auth-httplib2 SQLAlchemy pyodbc google-generativeai python-dotenv
# Se você desinstalou psycopg2-binary antes, não precisa reinstalar.

# ----------------------------------------------------------------------------
# 2. CONFIGURAÇÃO DO GOOGLE CLOUD (ANTES DE RODAR O CÓDIGO):
# ----------------------------------------------------------------------------
# 1. Acesse: https://console.cloud.google.com/
# 2. Crie um novo projeto
# 3. Ative a "YouTube Data API v3"
# 4. Vá em "Credenciais" > "Criar credenciais" > "ID do cliente OAuth 2.0"
# 5. Tipo: "Aplicativo para computador"
# 6. Baixe o arquivo JSON e renomeie para "client_secret.json"
# 7. Coloque o arquivo na mesma pasta deste código

# ----------------------------------------------------------------------------
# 3. CONFIGURAÇÃO DO SQL SERVER (ANTES DE RODAR O CÓDIGO):
# ----------------------------------------------------------------------------
# 1. Instale SQL Server Express e SQL Server Management Studio (SSMS).
# 2. Instale o Microsoft ODBC Driver para SQL Server.
# 3. No SSMS, crie um banco de dados chamado 'PostadorYoutubeDB'.
# 4. Execute o script SQL abaixo no SSMS para criar a tabela 'agendamentos':
#    CREATE TABLE agendamentos (
#        id INT PRIMARY KEY IDENTITY(1,1),
#        plataforma NVARCHAR(50) NOT NULL,
#        caminho_video NVARCHAR(MAX) NOT NULL,
#        titulo NVARCHAR(255) NOT NULL,
#        descricao NVARCHAR(MAX),
#        hashtags NVARCHAR(MAX),
#        data_agendamento DATETIME2 NOT NULL,
#        status NVARCHAR(50) NOT NULL DEFAULT 'agendado',
#        id_video_postado NVARCHAR(100),
#        mensagem_erro NVARCHAR(MAX)
#    );
# 5. ATENÇÃO: Substitua 'NOME_DO_SEU_PC\\SQLEXPRESS' na connection_string abaixo pelo nome da sua instância SQL Server.

# ----------------------------------------------------------------------------
# 4. CONFIGURAÇÃO DO GOOGLE GEMINI API (ANTES DE RODAR O CÓDIGO):
# ----------------------------------------------------------------------------
# 1. Acesse: https://aistudio.google.com/ e obtenha sua API Key.
# 2. Na pasta do projeto, crie um arquivo chamado '.env' (com o ponto na frente).
# 3. Dentro do '.env', adicione a linha: GEMINI_API_KEY="SUA_CHAVE_DA_API_AQUI"
#    Substitua SUA_CHAVE_DA_API_AQUI pela chave que você copiou.

# ----------------------------------------------------------------------------
# 5. CÓDIGO DO SERVIDOR (app.py):
# ----------------------------------------------------------------------------

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import pickle
import datetime
import json # Importado para parsear a resposta da IA

# Importações do Google YouTube API
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Importações do Banco de Dados (SQLAlchemy)
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# Importações para IA do Gemini e gerenciamento de segredos
import google.generativeai as genai
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (como a chave da API Gemini) do arquivo .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÕES GERAIS ---
UPLOAD_FOLDER = 'uploads'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.pickle'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- CONFIGURAÇÃO DA API GEMINI ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("AVISO: Chave da API Gemini não encontrada no .env. A funcionalidade de IA estará desabilitada.")

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SQL SERVER) ---
# **MUITO IMPORTANTE:** Substitua 'NOME_DO_SEU_PC\\SQLEXPRESS' pela sua instância real!
# Ex: se o nome do seu computador é 'MEULAPTOP' e a instância é 'SQLEXPRESS', use 'MEULAPTOP\\SQLEXPRESS'
# Se você instalou a instância padrão e não nomeou, pode ser apenas o nome do seu PC.
SERVER_NAME = 'DESKTOP-R2P10R7\\SQLEXPRESS'  # <--- Altere esta linha para o seu servidor!
DATABASE_NAME = 'PostadorYoutubeDB'
# Esta string usa Autenticação do Windows. Garanta que o "ODBC Driver 17 for SQL Server" está instalado.
CONNECTION_STRING = f"mssql+pyodbc://@{SERVER_NAME}/{DATABASE_NAME}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"

engine = create_engine(CONNECTION_STRING)
Session = sessionmaker(bind=engine)
Base = declarative_base() # Base para os modelos de ORM

# Define o modelo da tabela 'agendamentos' usando SQLAlchemy ORM
class Agendamento(Base):
    __tablename__ = 'agendamentos'
    id = Column(Integer, primary_key=True)
    plataforma = Column(String(50), nullable=False)
    caminho_video = Column(String, nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(String)
    hashtags = Column(String) # Guardaremos tags como uma string separada por vírgulas
    data_agendamento = Column(DateTime, nullable=False)
    status = Column(String(50), nullable=False, default='agendado')
    id_video_postado = Column(String(100))
    mensagem_erro = Column(String)

# Cria as tabelas no banco se elas ainda não existirem (apenas se for usar ORM para criar)
# Base.metadata.create_all(engine) # Comentado, pois você já criou via SSMS, mas útil para o futuro.

# --- FUNÇÃO DE IA PARA GERAR CONTEÚDO ---
def generate_ai_content(summary: str):
    """
    Usa a API Gemini para gerar título, descrição e tags a partir de um resumo.
    """
    if not GEMINI_API_KEY:
        raise Exception("A chave da API Gemini não foi configurada no servidor. Verifique o arquivo .env.")

    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Você é um especialista em marketing de conteúdo para o YouTube. Sua tarefa é criar metadados otimizados para um vídeo, com base em um resumo fornecido.
    Responda APENAS com um objeto JSON válido, sem nenhum texto ou formatação adicional antes ou depois.

    O JSON deve ter as seguintes chaves: "title", "description", "tags".

    - "title": Crie um título magnético e otimizado para SEO, com no máximo 70 caracteres.
    - "description": Crie uma descrição de 3 parágrafos. O primeiro resume o vídeo. O segundo detalha os pontos principais. O terceiro é uma chamada para ação (call-to-action) para se inscrever no canal e seguir nas redes sociais.
    - "tags": Crie uma única string contendo 10 a 15 hashtags relevantes, separadas por vírgulas.

    Resumo do vídeo:
    ---
    {summary}
    ---
    """
    
    response = model.generate_content(prompt)
    
    # Limpa a resposta para garantir que é um JSON válido
    cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
    
    return json.loads(cleaned_response)

# ----------------------------------------------------------------------------
# FUNÇÃO DE AUTENTICAÇÃO DO YOUTUBE
# ----------------------------------------------------------------------------
def get_authenticated_service():
    """Autentica e retorna o serviço do YouTube"""
    credentials = None
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            credentials = pickle.load(token)
    
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                return None, "Arquivo client_secret.json não encontrado!"
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=8080)
        
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
    
    return build('youtube', 'v3', credentials=credentials), None

# ----------------------------------------------------------------------------
# ROTA: AUTENTICAÇÃO
# ----------------------------------------------------------------------------
@app.route('/api/auth', methods=['GET'])
def authenticate():
    """Inicia o processo de autenticação"""
    try:
        service, error = get_authenticated_service()
        if error:
            return jsonify({"error": error}), 400
        return jsonify({"message": "Autenticação realizada com sucesso!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------------------------
# ROTA: VERIFICAR STATUS DA AUTENTICAÇÃO
# ----------------------------------------------------------------------------
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Verifica se está autenticado"""
    if os.path.exists(TOKEN_FILE):
        return jsonify({"authenticated": True}), 200
    return jsonify({"authenticated": False}), 200

# ----------------------------------------------------------------------------
# ROTA: AGENDAR UPLOAD PARA O YOUTUBE (MODIFICADA)
# ----------------------------------------------------------------------------
@app.route('/api/schedule/youtube', methods=['POST'])
def schedule_youtube_post():
    """Salva o vídeo e seus metadados para agendamento futuro no YouTube"""
    temp_path = None
    try:
        if 'video' not in request.files:
            return jsonify({"error": "Nenhum arquivo de vídeo foi enviado"}), 400
        
        video_file = request.files['video']
        title = request.form.get('title', 'Vídeo sem título')
        description = request.form.get('description', '')
        privacy = request.form.get('privacy', 'private')
        category = request.form.get('category', '22')
        tags = request.form.get('tags', '') # Guarda como string separada por vírgulas
        scheduled_time_str = request.form.get('scheduled_time')

        if video_file.filename == '':
            return jsonify({"error": "Arquivo inválido"}), 400
        if not scheduled_time_str:
            return jsonify({"error": "Data e hora de agendamento são obrigatórias"}), 400

        scheduled_time = datetime.datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))

        temp_path = os.path.join(UPLOAD_FOLDER, video_file.filename)
        video_file.save(temp_path)
        
        print(f"📹 Arquivo salvo temporariamente para agendamento: {temp_path}")
        print(f"📝 Título: {title}")
        print(f"⏰ Agendado para: {scheduled_time}")

        session = Session()
        try:
            new_agendamento = Agendamento(
                plataforma='youtube',
                caminho_video=temp_path,
                titulo=title,
                descricao=description,
                hashtags=tags,
                data_agendamento=scheduled_time,
                status='agendado'
            )
            session.add(new_agendamento)
            session.commit()
            return jsonify({"message": "Vídeo agendado com sucesso!", "id_agendamento": new_agendamento.id}), 201
        except Exception as db_e:
            session.rollback()
            return jsonify({"error": f"Erro ao salvar agendamento no banco de dados: {str(db_e)}"}), 500
        finally:
            session.close()

    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": str(e)}), 500

# ----------------------------------------------------------------------------
# ROTA: LISTAR AGENDAMENTOS
# ----------------------------------------------------------------------------
@app.route('/api/agendamentos', methods=['GET'])
def list_agendamentos():
    """Lista todos os agendamentos no banco de dados"""
    session = Session()
    try:
        agendamentos = session.query(Agendamento).order_by(Agendamento.data_agendamento.asc()).all()
        agendamentos_list = []
        for agendamento in agendamentos:
            agendamentos_list.append({
                'id': agendamento.id,
                'plataforma': agendamento.plataforma,
                'titulo': agendamento.titulo,
                'data_agendamento': agendamento.data_agendamento.isoformat(),
                'status': agendamento.status,
                'id_video_postado': agendamento.id_video_postado,
                'mensagem_erro': agendamento.mensagem_erro
            })
        return jsonify({"agendamentos": agendamentos_list}), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar agendamentos: {str(e)}"}), 500
    finally:
        session.close()

# ----------------------------------------------------------------------------
# ROTA: SERVIR O FRONTEND
# ----------------------------------------------------------------------------
@app.route('/')
def index():
    """Serve a página HTML"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    return send_from_directory('.', 'index.html')

# --- NOVA ROTA PARA A IA ---
@app.route('/api/generate-content', methods=['POST'])
def handle_generate_content():
    try:
        data = request.get_json()
        if not data or 'summary' not in data:
            return jsonify({"error": "O resumo (summary) é obrigatório."}), 400
        
        summary = data['summary']
        ai_content = generate_ai_content(summary)
        
        return jsonify(ai_content), 200

    except Exception as e:
        return jsonify({"error": f"Erro ao gerar conteúdo com IA: {str(e)}"}), 500

# ----------------------------------------------------------------------------
# FUNÇÃO PARA REALIZAR O UPLOAD NO YOUTUBE (Será chamada pelo Worker)
# ----------------------------------------------------------------------------
def perform_youtube_upload(agendamento_id):
    """
    Função que executa o upload de um vídeo agendado para o YouTube.
    Esta função será chamada por um 'worker' em segundo plano, não por uma rota direta.
    """
    session = Session()
    agendamento = session.query(Agendamento).filter_by(id=agendamento_id).first()

    if not agendamento:
        print(f"Worker: Agendamento ID {agendamento_id} não encontrado.")
        session.close()
        return

    if agendamento.status != 'agendado':
        print(f"Worker: Agendamento ID {agendamento_id} não está no status 'agendado'. Status atual: {agendamento.status}")
        session.close()
        return

    print(f"Worker: Iniciando upload para agendamento ID {agendamento.id} - Título: {agendamento.titulo}")

    try:
        youtube, error = get_authenticated_service()
        if error:
            raise Exception(f"Erro de autenticação: {error}")

        body = {
            'snippet': {
                'title': agendamento.titulo,
                'description': agendamento.descricao,
                'tags': [tag.strip() for tag in agendamento.hashtags.split(',') if tag.strip()] if agendamento.hashtags else [],
                'categoryId': '22' # Manter fixo ou adicionar campo no DB
            },
            'status': {
                'privacyStatus': 'private', # Manter como private ou adicionar campo no DB
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(agendamento.caminho_video, chunksize=-1, resumable=True)
        
        request_upload = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        response = request_upload.execute()
        
        agendamento.id_video_postado = response['id']
        agendamento.status = 'postado'
        agendamento.mensagem_erro = None
        session.commit()
        
        if os.path.exists(agendamento.caminho_video):
            os.remove(agendamento.caminho_video)

        print(f"Worker: ✅ Upload concluído para ID {agendamento.id}! URL: https://www.youtube.com/watch?v={response['id']}")

    except HttpError as e:
        agendamento.status = 'erro'
        agendamento.mensagem_erro = f"Erro da API do YouTube: {e.resp.status} - {e.content}"
        session.commit()
        print(f"Worker: ❌ Erro HttpError no upload para ID {agendamento.id}: {e}")
    except Exception as e:
        agendamento.status = 'erro'
        agendamento.mensagem_erro = str(e)
        session.commit()
        print(f"Worker: ❌ Erro geral no upload para ID {agendamento.id}: {e}")
    finally:
        session.close()


# ----------------------------------------------------------------------------
# INICIAR O SERVIDOR
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 70)
    print("🚀 SERVIDOR DE AGENDAMENTO E UPLOAD PARA YOUTUBE")
    print("=" * 70)
    print("📍 URL: http://localhost:5000")
    print("🔧 Para acessar de outros dispositivos na rede: http://SEU_IP:5000")
    print("=" * 70)
    print("\n⚠  ANTES DE USAR:")
    print("1. Instale as dependências (veja o topo do arquivo)")
    print("2. Configure o Google Cloud e baixe client_secret.json")
    print("3. Configure e crie o banco de dados SQL Server (veja o topo do arquivo)")
    print("4. Configure o Google Gemini API e crie o arquivo .env (veja o topo do arquivo)")
    print("5. Acesse http://localhost:5000/api/auth para autenticar o YouTube UMA VEZ")
    print("6. Para o agendamento funcionar, você precisará de um SCRIPT DE WORKER separado (próximo passo!).")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=5000, debug=True)