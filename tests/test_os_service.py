# tests/test_os_service.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import date
from fastapi import HTTPException
from starlette import status

# Importações dos módulos do seu projeto
from models.os_model import OrdemServico
from database.db_setup import Base
from services.os_service import OrdemServicoService

# ----------------------------------------------------------------------
# FIXTURES (Configurações de Teste)
# ----------------------------------------------------------------------

# 1. Configuração do Banco de Dados em Memória (Fixture de Sessão)
@pytest.fixture
async def async_session_in_memory():
    """Cria uma Engine e Sessão AsyncSession para um DB SQLite em memória."""
    
    # 1. Cria a engine de DB em memória para testes
    # O ':memory:' garante que o DB será limpo ao final da execução.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # 2. Cria todas as tabelas (OrdemServico)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 3. Session Factory de Teste
    AsyncSessionTesting = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    # 4. Geração de sessão para o teste
    async with AsyncSessionTesting() as session:
        yield session

    # 5. Cleanup: Dropar todas as tabelas após o uso
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose() # Fecha a conexão com a engine

# 2. Fixture do Service (opcional, mas facilita)
@pytest.fixture
def os_service():
    """Fornece uma instância do Service Layer."""
    return OrdemServicoService()

# ----------------------------------------------------------------------
# DADOS DE TESTE
# ----------------------------------------------------------------------

os_data = {
    "os_num": "OS-TEST-123",
    "cliente": "Cliente Teste",
    "tipo": "Manutenção",
    "equipamento": "Servidor XYZ",
    "status": "Pendente",
    "prazo_entrega": date(2025, 12, 31),
}


# ----------------------------------------------------------------------
# TESTES UNITÁRIOS: CAMADA DE SERVIÇO (CRUD BÁSICO)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_os_success(os_service: OrdemServicoService, async_session_in_memory: AsyncSession):
    """Verifica se a criação de uma OS funciona corretamente."""
    
    # ACT: Cria a OS no banco de dados
    new_os = await os_service.create_os(async_session_in_memory, os_data)
    
    # ASSERT 1: Verifica se o objeto retornado é uma instância do modelo
    assert isinstance(new_os, OrdemServico)
    
    # ASSERT 2: Verifica se os dados foram persistidos corretamente
    assert new_os.os_num == os_data["os_num"]
    assert new_os.cliente == os_data["cliente"]
    assert new_os.status == os_data["status"]
    
    # ASSERT 3: Verifica se o ID foi gerado (UUID)
    assert new_os.id is not None


@pytest.mark.asyncio
async def test_get_os_by_id_success(os_service: OrdemServicoService, async_session_in_memory: AsyncSession):
    """Verifica se a busca por ID funciona para um registro existente."""
    
    # ARRANGE: Cria uma OS primeiro para ter um ID válido
    created_os = await os_service.create_os(async_session_in_memory, os_data)
    os_id = created_os.id
    
    # ACT: Busca a OS pelo ID
    found_os = await os_service.get_os_by_id(async_session_in_memory, os_id)
    
    # ASSERT: Verifica se a OS encontrada corresponde à criada
    assert found_os.id == os_id
    assert found_os.os_num == os_data["os_num"]


@pytest.mark.asyncio
async def test_get_os_by_id_not_found(os_service: OrdemServicoService, async_session_in_memory: AsyncSession):
    """Verifica se uma HTTPException 404 é levantada para um ID inexistente."""
    
    # ARRANGE: Cria um ID inexistente (um UUID aleatório)
    non_existent_id = uuid4()
    
    # ACT & ASSERT: Espera que uma HTTPException seja levantada
    with pytest.raises(HTTPException) as excinfo:
        await os_service.get_os_by_id(async_session_in_memory, non_existent_id)
        
    # ASSERT: Verifica se o status code da exceção é 404
    assert excinfo.value.status_code == status.HTTP_404_NOT_FOUND
    assert "OS não encontrada" in excinfo.value.detail # A mensagem deve ser clara