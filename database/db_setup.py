from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Configuração da URL de Conexão (Dialeto + Driver + Caminho)
# O "sqlite+aiosqlite" é o dialeto para SQLite com o driver assíncrono.
# O "///./db.sqlite" significa que o arquivo 'db.sqlite' será criado
# na raiz do projeto, se não existir.
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./db.sqlite"

# 2. Criação da Engine Assíncrona
# A 'connect_args' é necessária para o SQLite, permitindo múltiplos acessos
# sem problemas de concorrência que normalmente ocorrem em ambiente multithreaded.
# O 'echo=False' pode ser setado para True para ver as queries SQL no console.
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=False,
    connect_args={"check_same_thread": False} 
)

# 3. Criação da Session Factory
# O AsyncSessionLocal será usado para criar novas sessões que interagem com o DB.
# O autocommit e autoflush são setados como False para controle manual das transações.
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession, # Define que a sessão deve ser assíncrona
    expire_on_commit=False # Para permitir acesso a objetos após o commit
)

# 4. Base Declarativa
Base = declarative_base()


# Função utilitária para obter a sessão do banco de dados (FastAPI Dependency)
async def get_db():
    """
    Função geradora para fornecer uma sessão de banco de dados por requisição.
    """
    async with AsyncSessionLocal() as session:
        yield session


# 5. Função para criar todas as tabelas no startup
async def create_all_tables():
    """
    Cria todas as tabelas no banco de dados, se não existirem, usando a engine assíncrona.
    
    NOTA: Esta função é assíncrona.
    """
    # Abre uma conexão assíncrona de "begin" (transação)
    async with engine.begin() as conn:
        # Executa a operação Base.metadata.create_all, que é síncrona,
        # de forma segura em um pool de threads, liberando o event loop.
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Tabelas inicializadas no banco de dados (db.sqlite).")