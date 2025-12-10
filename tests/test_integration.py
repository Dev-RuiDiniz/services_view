import pytest
from uuid import uuid4
from starlette import status
from fastapi.testclient import TestClient # <--- MUDANÇA: Importa TestClient

# Importações da aplicação
from main import app
from database.db_setup import get_db

# Reutiliza fixtures do test_os_service.py
from tests.test_os_service import async_session_in_memory, populated_session 


# ----------------------------------------------------------------------
# FIXTURES DE TESTE DE INTEGRAÇÃO
# ----------------------------------------------------------------------

# 1. Fixture para injetar o DB em Memória na Aplicação FastAPI (Inalterada)
@pytest.fixture
def override_get_db(async_session_in_memory):
    """Sobrescreve a dependência get_db com a sessão de teste em memória."""
    async def _get_db_override():
        yield async_session_in_memory
    return _get_db_override

# 2. Fixture para popular e fornecer o Cliente de Teste (AGORA SÍNCRONO)
@pytest.fixture
def client_with_data(override_get_db, populated_session): # <--- MUDANÇA: 'async' removido
    """
    Cliente de teste com a aplicação configurada para usar o DB em memória e populado.
    """
    # 1. Sobrescreve a dependência do DB da aplicação
    app.dependency_overrides[get_db] = override_get_db
    
    # 2. Usa o TestClient (SÍNCRONO)
    with TestClient(app) as client: # <--- MUDANÇA: Usa TestClient
        yield client
        
    # 3. Limpa a sobrescrita após o teste
    app.dependency_overrides.clear()


# ----------------------------------------------------------------------
# TESTES DE INTEGRAÇÃO: ROTAS GET (Listagem/Filtros)
# ----------------------------------------------------------------------

# pytest.mark.asyncio removido
def test_get_list_os_success_no_filter(client_with_data: TestClient): # <--- MUDANÇA: Tipo de cliente
    """
    Verifica se a rota GET /os/ retorna status 200 e renderiza a listagem
    sem filtros aplicados.
    """
    # ACT: Faz a requisição para a rota principal (sem 'await')
    response = client_with_data.get("/os/")

    assert response.status_code == status.HTTP_200_OK
        # Correção: Usar um cabeçalho mais robusto
    assert "<th>Cliente</th>" in response.text, "O HTML deve conter a estrutura da tabela (pelo menos o cabeçalho Cliente)"


# pytest.mark.asyncio removido
def test_get_list_os_with_filter_by_status(client_with_data: TestClient):
    """
    Verifica se a rota GET /os/ com filtro retorna 200 e apenas os resultados filtrados.
    """
    response = client_with_data.get("/os/", params={"status": "Pendente"})
    
    assert response.status_code == status.HTTP_200_OK
    assert "OS-100" in response.text
    assert "OS-105" in response.text
    assert "OS-102" not in response.text, "O filtro 'Pendente' não deve listar OS-102 (ATRASADO)."


# pytest.mark.asyncio removido
def test_get_list_os_with_no_results(client_with_data: TestClient):
        """
        Verifica a resposta para uma consulta que não retorna resultados.
        """
        # Correção: Usar um parâmetro de filtro aceito (cliente) com valor inexistente
        response = client_with_data.get("/os/", params={"cliente": "ClienteInexistenteXZY"})

        assert response.status_code == status.HTTP_200_OK
        # Corrigido: O template index.html tem "Nenhuma Ordem de Serviço encontrada"
        assert "Nenhuma Ordem de Serviço encontrada" in response.text, "Deve aparecer a mensagem de que não há resultados."


# ----------------------------------------------------------------------
# TESTES DE INTEGRAÇÃO: ROTAS POST (Criação)
# ----------------------------------------------------------------------

# pytest.mark.asyncio removido
def test_post_create_os_success(client_with_data: TestClient):
    # CORREÇÃO: Indentação do valid_data (era a causa do NameError)
    valid_data = {
        "os_num": f"OS-TESTE-POST-{uuid4()}", # Usa UUID para garantir unicidade
        "cliente": "Cliente Teste Integracao",
        "tipo": "Manutenção",
        "equipamento": "Notebook X",
        "status": "Pendente",
        "prazo_entrega": "2026-06-01",
    }
        
    response = client_with_data.post(
        "/os/novo",
        data=valid_data,
        # Correção: Desabilita o redirecionamento automático
        follow_redirects=False 
    )

    assert response.status_code == status.HTTP_303_SEE_OTHER, "Deve retornar 303 SEE OTHER após criação bem-sucedida."


# pytest.mark.asyncio removido
def test_post_create_os_invalid_data(client_with_data: TestClient):
    """
    Simula a submissão de um formulário POST com dados inválidos (campo 'cliente' faltando).
    Espera um status de erro (400 Bad Request ou 422 Unprocessable Entity).
    """
    invalid_data = {
        "os_num": "OS-INVALIDA",
        "tipo": "Manutenção",
        "equipamento": "Servidor",
        "status": "Pendente",
        "prazo_entrega": "2026-06-01",
    }
    
    response = client_with_data.post(
        "/os/novo", 
        data=invalid_data
    )

    # Verifica o Status de Erro
    assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST], \
        f"A submissão com dados inválidos deve retornar 400 ou 422. Recebido: {response.status_code}"

    # Verifica a ausência no DB
    list_response = client_with_data.get("/os/")
    assert "OS-INVALIDA" not in list_response.text, "A OS com dados inválidos não deve ser criada e aparecer na listagem."