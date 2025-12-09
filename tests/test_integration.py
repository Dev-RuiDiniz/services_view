import pytest
from httpx import AsyncClient
from uuid import uuid4
from starlette import status

# Importações da aplicação
from main import app
from database.db_setup import get_db

# Importa o Service Layer para type hinting (não essencial, mas boa prática)
from services.os_service import OrdemServicoService 

# Reutiliza fixtures do test_os_service.py:
# async_session_in_memory: a sessão do DB em memória.
# populated_session: a fixture que insere o DATASET_KPI no DB.
from tests.test_os_service import async_session_in_memory, populated_session 


# ----------------------------------------------------------------------
# FIXTURES DE TESTE DE INTEGRAÇÃO
# ----------------------------------------------------------------------

# 1. Fixture para injetar o DB em Memória na Aplicação FastAPI
@pytest.fixture
def override_get_db(async_session_in_memory):
    """Sobrescreve a dependência get_db com a sessão de teste em memória."""
    async def _get_db_override():
        yield async_session_in_memory
    return _get_db_override

# 2. Fixture para popular e fornecer o Cliente de Teste Async
@pytest.fixture
async def client_with_data(override_get_db, populated_session):
    """
    Cliente de teste com a aplicação configurada para usar o DB em memória e populado.
    """
    # 1. Sobrescreve a dependência do DB da aplicação
    app.dependency_overrides[get_db] = override_get_db
    
    # 2. Usa o AsyncClient (necessário para testes assíncronos)
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
        
    # 3. Limpa a sobrescrita após o teste
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# TESTES DE INTEGRAÇÃO: ROTAS GET (Listagem/Filtros)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_list_os_success_no_filter(client_with_data: AsyncClient):
    """
    Verifica se a rota GET /os/ retorna status 200 e renderiza a listagem
    sem filtros aplicados.
    """
    # ACT: Faz a requisição para a rota principal
    response = await client_with_data.get("/os/")
    
    # ASSERT 1: Verifica o Status HTTP
    assert response.status_code == status.HTTP_200_OK, "A rota deve retornar 200 OK"
    
    # ASSERT 2: Verifica se o HTML esperado foi renderizado
    assert "<th>Nº OS</th>" in response.text, "O HTML deve conter a estrutura da tabela (os_list.html)"
    
    # ASSERT 3: Verifica se registros conhecidos foram listados
    assert "OS-100" in response.text, "O HTML deve listar a OS-100."
    assert "OS-107" in response.text, "O HTML deve listar a OS-107."
    
    # ASSERT 4: Verifica se o status calculado está presente (ATRASADO)
    assert 'status-atrasado' in response.text.lower(), "O HTML deve renderizar o status 'ATRASADO' calculado pelo Service."


@pytest.mark.asyncio
async def test_get_list_os_with_filter_by_status(client_with_data: AsyncClient):
    """
    Verifica se a rota GET /os/ com filtro retorna 200 e apenas os resultados filtrados.
    """
    # ACT: Faz a requisição com o Query Parameter para 'Pendente' (2 registros esperados)
    response = await client_with_data.get("/os/", params={"status": "Pendente"})
    
    # ASSERT 1: Verifica o Status HTTP
    assert response.status_code == status.HTTP_200_OK
    
    # ASSERT 2: Verifica se os resultados corretos estão presentes
    assert "OS-100" in response.text
    assert "OS-105" in response.text
    
    # ASSERT 3: Verifica se os resultados incorretos estão ausentes
    assert "OS-102" not in response.text, "O filtro 'Pendente' não deve listar OS-102 (ATRASADO)."


@pytest.mark.asyncio
async def test_get_list_os_with_no_results(client_with_data: AsyncClient):
    """
    Verifica a resposta para uma consulta que não retorna resultados.
    """
    # ARRANGE: Filtro com um ID que certamente não existe
    non_existent_os_num = str(uuid4())
    
    # ACT: Faz a requisição com filtro inexistente
    response = await client_with_data.get("/os/", params={"os_num": non_existent_os_num})
    
    # ASSERT 1: Verifica o Status HTTP
    assert response.status_code == status.HTTP_200_OK
    
    # ASSERT 2: Verifica a mensagem de "Nenhum resultado" no template
    assert "Nenhuma Ordem de Serviço encontrada" in response.text, "Deve aparecer a mensagem de que não há resultados."


# ----------------------------------------------------------------------
# TESTES DE INTEGRAÇÃO: ROTAS POST (Criação)
# ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_create_os_success(client_with_data: AsyncClient):
    """
    Simula a submissão de um formulário POST válido para criar uma nova OS.
    Espera status 303 (Redirect).
    """
    valid_data = {
        "os_num": "OS-NOVA-VALIDA",
        "cliente": "Cliente Novo Teste",
        "tipo": "Manutenção",
        "equipamento": "Desktop",
        "status": "Pendente",
        "prazo_entrega": "2026-06-01", 
    }
    
    # ACT: Simula a submissão do formulário POST
    response = await client_with_data.post(
        "/os/novo", # Rota POST que recebe o formulário
        data=valid_data # Dados do formulário
    )
    
    # ASSERT 1: Verifica o Status de Redirecionamento
    assert response.status_code == status.HTTP_303_SEE_OTHER, "Deve retornar 303 SEE OTHER após criação bem-sucedida."

    # ASSERT 2: Verifica a criação no Banco de Dados
    # Requer o acesso à listagem para confirmar a persistência.
    list_response = await client_with_data.get("/os/")
    assert "OS-NOVA-VALIDA" in list_response.text, "A nova OS deve estar visível na listagem após o redirect."


@pytest.mark.asyncio
async def test_post_create_os_invalid_data(client_with_data: AsyncClient):
    """
    Simula a submissão de um formulário POST com dados inválidos (campo 'cliente' faltando).
    Espera um status de erro (400 Bad Request ou 422 Unprocessable Entity).
    """
    # ARRANGE: Dados inválidos (campo 'cliente' obrigatório faltando)
    invalid_data = {
        "os_num": "OS-INVALIDA",
        "tipo": "Manutenção",
        "equipamento": "Servidor",
        "status": "Pendente",
        "prazo_entrega": "2026-06-01",
    }
    
    # ACT: Simula a submissão do formulário POST
    response = await client_with_data.post(
        "/os/novo", 
        data=invalid_data
    )

    # ASSERT 1: Verifica o Status de Erro
    # Se um campo Form() obrigatório está ausente, o FastAPI/Pydantic retorna 422 (Unprocessable Entity).
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST], \
        f"A submissão com dados inválidos deve retornar 400 ou 422. Recebido: {response.status_code}"

    # ASSERT 2: Verifica a ausência no DB
    list_response = await client_with_data.get("/os/")
    assert "OS-INVALIDA" not in list_response.text, "A OS com dados inválidos não deve ser criada e aparecer na listagem."