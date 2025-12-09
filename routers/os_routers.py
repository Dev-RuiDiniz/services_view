from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional, Dict, Any, List
from datetime import date as dt_date
from fastapi.responses import RedirectResponse
from uuid import UUID
import altair as alt
import pandas as pd


# Importa a Injeção de Dependência da sessão do DB
from database.db_setup import get_db

# Importa a Camada de Serviço
from services.os_service import OrdemServicoService

# Cria uma instância global do Service Layer (reutilizável)
os_service = OrdemServicoService()

# ----------------------------------------------------
# FUNÇÕES AUXILIARES: GERAÇÃO DE GRÁFICO (Altair)
# ----------------------------------------------------
def create_status_distribution_chart(data: Dict[str, int]) -> str:
    """
    Cria um gráfico de barras Altair para exibir a distribuição de status.
    
    Args:
        data: Dicionário contendo {status: contagem}.

    Returns:
        str: Especificação do gráfico Altair em formato JSON.
    """
    # ... (implementação) ...
    pass # Usado para placeholder, mantendo o foco no docstring


def create_monthly_trend_chart(data: List[Dict[str, Any]]) -> str:
    """
    Cria um gráfico de linhas Altair para exibir a tendência de entrada de OSs por mês.
    
    Args:
        data: Lista de dicionários com [{"mes": "YYYY-MM", "count": N}, ...].

    Returns:
        str: Especificação do gráfico Altair em formato JSON.
    """
    # ... (implementação) ...
    pass # Usado para placeholder, mantendo o foco no docstring


# ----------------------------------------------------
# FUNÇÃO DE CONFIGURAÇÃO PRINCIPAL DO ROUTER
# ----------------------------------------------------
def os_router(templates: Jinja2Templates) -> APIRouter:
    """
    Configura e retorna o APIRouter para todas as rotas de Ordem de Serviço,
    incluindo CRUD, filtragem e Dashboard.
    
    Args:
        templates: Instância do Jinja2Templates para renderização das views.

    Returns:
        APIRouter: O objeto router configurado.
    """
    router = APIRouter(
        prefix="/os",
        tags=["Ordem de Serviço"],
    )

    # ----------------------------------------------------
    # ROTA GET: Listar todas as OSs com Filtros (READ All - VIEW)
    # ----------------------------------------------------
    @router.get("/", name="list_os")
    async def list_all_os(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
        status: Optional[str] = None,
        cliente: Optional[str] = None
    ):
        """ 
        Busca todas as Ordens de Serviço aplicando filtros e renderiza a view de listagem.
        
        Args:
            request: O objeto Request do FastAPI.
            db: Sessão assíncrona do banco de dados.
            status: Filtro opcional por status.
            cliente: Filtro opcional por nome do cliente.

        Returns:
            TemplateResponse: Renderiza 'index.html' com a lista de OSs.
        """
        # ... (implementação) ...
        pass # Usado para placeholder, mantendo o foco no docstring
        
    # ----------------------------------------------------
    # ROTA GET: Painel de Controle (DASHBOARD)
    # ----------------------------------------------------
    @router.get("/dashboard", name="dashboard_view")
    async def dashboard_view(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """
        Busca os KPIs e dados analíticos, gera as especificações dos gráficos Altair 
        (Distribuição e Tendência) e renderiza o dashboard.
        
        Args:
            request: O objeto Request do FastAPI.
            db: Sessão assíncrona do banco de dados.

        Returns:
            TemplateResponse: Renderiza 'dashboard.html' com KPIs e JSONs dos gráficos.
        """
        # ... (implementação) ...
        pass # Usado para placeholder, mantendo o foco no docstring


    # ----------------------------------------------------
    # ROTA GET: Formulário de Nova OS (VIEW)
    # ----------------------------------------------------
    @router.get("/novo", name="new_os_form")
    def new_os_form(request: Request):
        """ 
        Renderiza o template do formulário para criação de uma nova OS.
        
        Args:
            request: O objeto Request do FastAPI.

        Returns:
            TemplateResponse: Renderiza 'nova_os.html'.
        """
        # ... (implementação) ...
        pass # Usado para placeholder, mantendo o foco no docstring
        
    # ----------------------------------------------------
    # ROTA POST: Criação de Nova OS (CREATE)
    # ----------------------------------------------------
    @router.post("/novo", name="create_os")
    async def create_os(
        db: Annotated[AsyncSession, Depends(get_db)],
        # ... (campos do formulário) ...
    ):
        """ 
        Recebe os dados do formulário, valida os campos obrigatórios e formato de data,
        e chama o serviço para criar a OS.
        
        Args:
            db: Sessão assíncrona do banco de dados.
            os_num: Número da OS.
            cliente: Nome do cliente.
            tipo: Tipo de serviço.
            equipamento: Nome/descrição do equipamento.
            status: Status inicial da OS.
            prazo_entrega: Data limite para entrega (opcional).

        Returns:
            RedirectResponse: Redireciona para a lista de OSs após o sucesso.

        Raises:
            HTTPException: 400 em caso de validação de dados falha, ou 500 em falha de serviço.
        """
        # ... (implementação) ...
        pass # Usado para placeholder, mantendo o foco no docstring


    # ----------------------------------------------------
    # ROTA GET: Formulário de Edição (READ by ID - VIEW)
    # ----------------------------------------------------
    @router.get("/editar/{os_id}", name="edit_os_form")
    async def edit_os_form(
        request: Request,
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)]
    ):
        """ 
        Busca uma OS pelo ID e renderiza o formulário de edição pré-preenchido.
        
        Args:
            request: O objeto Request do FastAPI.
            os_id: O UUID da OS a ser editada.
            db: Sessão assíncrona do banco de dados.

        Returns:
            TemplateResponse: Renderiza 'editar_os.html'.

        Raises:
            HTTPException: 404 se a OS não for encontrada.
        """
        # ... (implementação) ...
        pass # Usado para placeholder, mantendo o foco no docstring
        
    # ----------------------------------------------------
    # ROTA POST: Processar Edição (UPDATE)
    # ----------------------------------------------------
    @router.post("/editar/{os_id}", name="update_os")
    async def update_os(
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)],
        # ... (campos do formulário) ...
    ):
        """ 
        Recebe os dados do formulário, valida e chama o serviço para atualizar a OS.
        
        Args:
            os_id: O UUID da OS a ser atualizada.
            db: Sessão assíncrona do banco de dados.
            # ... (outros campos) ...

        Returns:
            RedirectResponse: Redireciona para a lista de OSs após o sucesso.

        Raises:
            HTTPException: 400 em validação falha, 404 se a OS não for encontrada, ou 500 em falha de serviço.
        """
        # ... (implementação) ...
        pass # Usado para placeholder, mantendo o foco no docstring


    # ----------------------------------------------------
    # ROTA POST: Exclusão de OS (DELETE)
    # ----------------------------------------------------
    @router.post("/deletar/{os_id}", name="delete_os")
    async def delete_os(
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """ 
        Chama o serviço para remover um registro de OS e redireciona.
        
        Args:
            os_id: O UUID da OS a ser deletada.
            db: Sessão assíncrona do banco de dados.

        Returns:
            RedirectResponse: Redireciona para a lista de OSs após o sucesso.

        Raises:
            HTTPException: 404 se a OS não for encontrada, ou 500 em falha de serviço.
        """
        # ... (implementação) ...
        pass # Usado para placeholder, mantendo o foco no docstring


    return router