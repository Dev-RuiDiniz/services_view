# tests/test_os_service.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from uuid import uuid4
from datetime import date, timedelta
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
        # Corrigido: Usar uma substring que exista na mensagem real
        assert "não encontrada" in excinfo.value.detail

# ----------------------------------------------------------------------    
    # DADOS E FIXTURES DE TESTE PARA AGGREGAÇÃO (KPIs)
# ----------------------------------------------------------------------

# Definição do Dataset de Teste
# A data de referência é HOJE (datetime.date.today()) para cálculos de prazo.
HOJE = date.today() 

DATASET_KPI = [
    # 1. OS Pendente (No Prazo - Longe)
    {"os_num": "OS-100", "cliente": "A", "tipo": "Manutenção", "equipamento": "E1", "status": "Pendente", "prazo_entrega": HOJE + timedelta(days=10)},
    
    # 2. OS Próximo do Prazo (Calculado: 3 dias)
    {"os_num": "OS-101", "cliente": "B", "tipo": "Instalação", "equipamento": "E2", "status": "Em Andamento", "prazo_entrega": HOJE + timedelta(days=2)},
    
    # 3. OS Atrasada (Calculado: -1 dia)
    {"os_num": "OS-102", "cliente": "C", "tipo": "Manutenção", "equipamento": "E3", "status": "Em Andamento", "prazo_entrega": HOJE - timedelta(days=1)},
    
    # 4. OS Concluída (Não entra no cálculo de Atraso/Próximo)
    {"os_num": "OS-103", "cliente": "D", "tipo": "Orçamento", "equipamento": "E4", "status": "Concluída", "prazo_entrega": HOJE - timedelta(days=5)},
    
    # 5. Outra OS Em Andamento (Próximo do Prazo)
    {"os_num": "OS-104", "cliente": "E", "tipo": "Manutenção", "equipamento": "E5", "status": "Em Andamento", "prazo_entrega": HOJE + timedelta(days=3)},
    
    # 6. Outra OS Pendente (No Prazo - Longe)
    {"os_num": "OS-105", "cliente": "F", "tipo": "Instalação", "equipamento": "E6", "status": "Pendente", "prazo_entrega": HOJE + timedelta(days=15)},
    
    # 7. OS Aguardando Peças (Status customizado)
    {"os_num": "OS-106", "cliente": "G", "tipo": "Manutenção", "equipamento": "E7", "status": "Aguardando Peças", "prazo_entrega": HOJE + timedelta(days=5)},
    
    # 8. OS Concluída (Outro mês para teste de tendência mensal, se necessário)
    {"os_num": "OS-107", "cliente": "H", "tipo": "Orçamento", "equipamento": "E8", "status": "Concluída", "data_entrada": HOJE - timedelta(days=60), "prazo_entrega": HOJE - timedelta(days=55)},
]

@pytest.fixture
async def populated_session(async_session_in_memory: AsyncSession):
    """Popula a sessão do DB em memória com dados de teste fixos."""
    from models.os_model import OrdemServico # Importa dentro para evitar circular dependência
    
    # 1. Insere cada item do dataset
    for data in DATASET_KPI:
        # Usa o método do service para garantir que a lógica de criação é testada
        # Ou cria diretamente o objeto model, para isolar a criação do service dos testes de agregação
        os_obj = OrdemServico(**data)
        async_session_in_memory.add(os_obj)
        
    # 2. Persiste os dados (commit)
    await async_session_in_memory.commit()
    
    # 3. Retorna a sessão populada
    yield async_session_in_memory


# ----------------------------------------------------------------------
# TESTES UNITÁRIOS: AGREGAÇÃO DE DADOS (KPIs)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_kpis_aggregation(os_service: OrdemServicoService, populated_session: AsyncSession):
    """
    Verifica se o cálculo de KPIs (total, atrasadas, em andamento, concluídas)
    retorna os valores esperados para o dataset fixo.
    """
    # ARRANGE: Total de OSs no dataset: 8
    # Total de Concluídas/Canceladas (Status Fixo): 2 (OS-103, OS-107)
    # Total de Atrasadas (Calculado): 1 (OS-102)
    # Total Em Andamento (Status Pendente, Em Andamento, Aguardando Peças): 5
    
    # ACT: Chama a função de KPIs
    kpis = await os_service.get_kpis(populated_session)
    
    # ASSERT: Verifica os valores
    assert kpis["total_os"] == 8, "O KPI 'total_os' deve ser 8."
    assert kpis["total_concluidas"] == 2, "O KPI 'total_concluidas' deve ser 2."
    assert kpis["total_atrasadas"] == 1, "O KPI 'total_atrasadas' deve ser 1 (OS-102)."
    assert kpis["total_em_andamento"] == 5, "O KPI 'total_em_andamento' deve ser 5 (Pendente, Em Andamento, Aguardando Peças, excluindo Concluídas/Canceladas)."


@pytest.mark.asyncio
async def test_get_status_distribution_calculation(os_service: OrdemServicoService, populated_session: AsyncSession):
    """
    Verifica se a distribuição de status (incluindo status calculados)
    retorna as contagens corretas.
    """
    # ARRANGE (Valores esperados com base no DATASET_KPI):
    # - Concluída: 2 (OS-103, OS-107)
    # - ATRASADO: 1 (OS-102)
    # - PRÓXIMO DO PRAZO: 2 (OS-101, OS-104)
    # - Pendente: 2 (OS-100, OS-105)
    # - Aguardando Peças: 1 (OS-106)
    
    # ACT: Chama a função de distribuição de status
    distribution = await os_service.get_status_distribution(populated_session)
    
    # ASSERT: Verifica as contagens no dicionário resultante
    assert distribution.get("Concluída") == 2
    assert distribution.get("ATRASADO") == 1
    assert distribution.get("PRÓXIMO DO PRAZO") == 2
    assert distribution.get("Pendente") == 2
    assert distribution.get("Aguardando Peças") == 1
    
    # Garante que não há outros status
    assert len(distribution) == 5