# worker.py

import time
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from apscheduler.schedulers.blocking import BlockingScheduler

# Importa as configurações e a função de upload do nosso app.py
from App import Agendamento, perform_youtube_upload, SERVER_NAME, DATABASE_NAME, CONNECTION_STRING

print("🤖 INICIANDO O WORKER DE AGENDAMENTO...")
print("="*40)

# Configura a conexão com o banco de dados (exatamente como no app.py)
engine = create_engine(CONNECTION_STRING)
Session = sessionmaker(bind=engine)

def check_and_post_videos():
    """
    Esta é a tarefa que o worker vai executar repetidamente.
    """
    print(f"[{datetime.datetime.now()}] 🔍 Verificando agendamentos...")
    
    session = Session()
    try:
        # Busca por agendamentos que estão na hora e com status 'agendado'
        now = datetime.datetime.now()
        agendamentos_para_postar = session.query(Agendamento).filter(
            Agendamento.status == 'agendado',
            Agendamento.data_agendamento <= now
        ).all()

        if not agendamentos_para_postar:
            print("✨ Nenhum vídeo para postar no momento.")
            return

        for agendamento in agendamentos_para_postar:
            print(f"Found post! Starting to work on Post #{agendamento.id}")
            print(f"▶️ Encontrado agendamento ID: {agendamento.id} - Título: {agendamento.titulo}")
            
            # Muda o status para 'processando' para evitar que seja pego de novo
            agendamento.status = 'processando'
            session.commit()
            
            try:
                # Chama a função principal de upload
                perform_youtube_upload(agendamento.id)
            except Exception as e:
                # Em caso de erro na função de upload, registra no log
                print(f"❌ Erro inesperado ao processar o upload para o agendamento {agendamento.id}: {e}")
                agendamento.status = 'erro'
                agendamento.mensagem_erro = f"Erro no worker: {str(e)}"
                session.commit()

    except Exception as e:
        print(f"❌ Erro ao verificar o banco de dados: {e}")
        session.rollback()
    finally:
        session.close()


# --- Configuração do Agendador (Scheduler) ---
# Instale com: pip install APScheduler
scheduler = BlockingScheduler()

# Agenda a tarefa 'check_and_post_videos' para rodar a cada 60 segundos
scheduler.add_job(check_and_post_videos, 'interval', seconds=60)

try:
    print("🚀 Worker iniciado. Verificando a cada 60 segundos. Pressione Ctrl+C para sair.")
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    pass