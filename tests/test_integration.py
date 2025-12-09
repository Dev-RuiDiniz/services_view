# tests/test_integration.py
import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import date, timedelta
from starlette import status

# Importações da aplicação
from main import app
from database.db_setup import get_db
from models.os_model import OrdemServico
from tests.test_os_service import async_session_in_memory, os_service, DATASET_KPI # Reutiliza fixtures!

# ----------------------------------------------------------------------
# FIXTURES DE TESTE DE INTEGRAÇÃO
# ----------------------------------------------------------------------

# 1. Fixture para injetar o DB em Memória na Aplicação FastAPI
# Esta é a função que substituirá o 'get_db' original durante o teste.
@pytest.fixture
def override_get_db(async_session_in_memory):
    """Sobrescreve a dependência get_db com a sessão de teste em memória."""
    async def _get_db_override():
        yield async_session_in_memory
    return _get_db_override

# 2. Fixture para popular e fornecer o Cliente de Teste Async
@pytest.fixture
async def client_with_data(app, override_get_db, populated_session):
    """
    Cliente de teste com a aplicação configurada para usar o DB em memória e populado.
    'populated_session' é usado apenas para garantir que a sessão esteja populada
    antes do cliente ser usado.
    """
    # 1. Sobrescreve a dependência do DB da aplicação
    app.dependency_overrides[get_db] = override_get_db
    
    # 2. Usa o AsyncClient (necessário para testes assíncronos)
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
        
    # 3. Limpa a sobrescrita após o teste
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# TESTES DE INTEGRAÇÃO
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_list_os_success_no_filter(client_with_data: AsyncClient):
    """
    Verifica se a rota GET /os/ retorna status 200 e renderiza a listagem
    sem filtros aplicados.
    """
    # ARRANGE: O DB já está populado com 8 OSs (do DATASET_KPI)
    
    # ACT: Faz a requisição para a rota principal
    response = await client_with_data.get("/os/")
    
    # ASSERT 1: Verifica o Status HTTP
    assert response.status_code == status.HTTP_200_OK, "A rota deve retornar 200 OK"
    
    # ASSERT 2: Verifica se o HTML esperado foi renderizado
    # Procuramos por um título de coluna da tabela (integração Template + Dados)
    assert "<th>Nº OS</th>" in response.text, "O HTML deve conter a estrutura da tabela (os_list.html)"
    
    # ASSERT 3: Verifica se todos os registros foram listados
    # Procuramos o número da OS de teste no HTML renderizado
    assert "OS-100" in response.text, "O HTML deve listar a OS-100."
    assert "OS-107" in response.text, "O HTML deve listar a OS-107."
    
    # ASSERT 4: Verifica se o status calculado está presente (integração Service -> Template)
    # OS-102 deve ser 'ATRASADO'
    assert 'status-atrasado' in response.text.lower(), "O HTML deve renderizar o status 'ATRASADO' calculado pelo Service."


@pytest.mark.asyncio
async def test_get_list_os_with_filter_by_status(client_with_data: AsyncClient):
    """
    Verifica se a rota GET /os/ com filtro (Query Param) retorna 200 e apenas
    os resultados filtrados.
    """
    # ARRANGE: Filtro para buscar apenas OSs com status 'Pendente'
    # Esperado: 2 registros (OS-100 e OS-105)
    
    # ACT: Faz a requisição com o Query Parameter
    response = await client_with_data.get("/os/", params={"status": "Pendente"})
    
    # ASSERT 1: Verifica o Status HTTP
    assert response.status_code == status.HTTP_200_OK
    
    # ASSERT 2: Verifica se os resultados corretos estão presentes
    assert "OS-100" in response.text
    assert "OS-105" in response.text
    
    # ASSERT 3: Verifica se os resultados incorretos estão ausentes
    # OS-102 (ATRASADO) NÃO deve estar na resposta
    assert "OS-102" not in response.text, "O filtro 'Pendente' não deve listar OS-102."


@pytest.mark.asyncio
async def test_get_list_os_with_no_results(client_with_data: AsyncClient):
    """
    Verifica a resposta para uma consulta que não retorna resultados.
    """
    # ARRANGE: Filtro muito específico
    non_existent_os_num = str(uuid4()) # Um número que certamente não existe
    
    # ACT: Faz a requisição com filtro inexistente
    response = await client_with_data.get("/os/", params={"os_num": non_existent_os_num})
    
    # ASSERT 1: Verifica o Status HTTP
    assert response.status_code == status.HTTP_200_OK
    
    # ASSERT 2: Verifica a mensagem de "Nenhum resultado"
    assert "Nenhuma Ordem de Serviço encontrada" in response.text, "Deve aparecer a mensagem de que não há resultados."