from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from fastapi.templating import Jinja2Templates 
from routers.os_routers import os_router

# Importar a função de setup do banco de dados
from database.db_setup import create_all_tables
# Lembrete: Importe seus modelos para que Base.metadata.create_all os reconheça
from models import os_model # Garante que a classe OrdemServico seja registrada no SQLAlchemy

# --- Context Manager de Inicialização ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Função de inicialização e desligamento (startup e shutdown) da aplicação.
    Responsável por garantir que as tabelas sejam criadas.
    """
    print("Iniciando a aplicação...")
    # 1. Chamada à função de criação de tabelas
    await create_all_tables() 
    
    yield # A aplicação está pronta para receber requisições
    
    # Código de desligamento (se necessário, ex: fechar conexões)
    print("Desligando a aplicação...")


# 2. Inicialização do FastAPI
app = FastAPI(
    title="Sistema de Ordens de Serviço (OS)",
    description="API e Frontend para gerenciamento de ordens de serviço.",
    version="0.1.0",
    lifespan=lifespan # Conecta o context manager ao ciclo de vida
)

# Configuração do motor de templates para a pasta 'templates'
templates = Jinja2Templates(directory="templates")

# 3. Montagem de Arquivos Estáticos
# Permite acessar arquivos em static/ via URL /static/...
app.mount("/static", StaticFiles(directory="static"), name="static")


# 4. Inclusão das Rotas
# Injeta a instância 'templates' no router e o monta na aplicação
app.include_router(os_router(templates))


# --- Exemplo de Rota Raiz (apenas para teste inicial) ---
@app.get("/")
def read_root():
    return {"message": "Bem-vindo ao Sistema de Ordens de Serviço! Core Operacional."}

# --- Para rodar localmente, use o comando: uvicorn main:app --reload ---
# Este bloco é opcional, mas útil para rodar o arquivo diretamente
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)