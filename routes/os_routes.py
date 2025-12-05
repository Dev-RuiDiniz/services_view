from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Type

# Importa a Injeção de Dependência da sessão do DB
from database.db_setup import get_db

# Importa a Camada de Serviço
from services.os_service import OrdemServicoService

# Criamos uma instância do Service Layer (não é ideal, mas funciona para este momento)
# Idealmente, o serviço seria injetado, mas por simplicidade, criamos uma instância.
os_service = OrdemServicoService()


def os_router(templates: Jinja2Templates) -> APIRouter:
    """
    Configura e retorna o APIRouter para as rotas de Ordem de Serviço.
    
    Args:
        templates (Jinja2Templates): O motor de templates global.
        
    Returns:
        APIRouter: O router configurado com as rotas do CRUD.
    """
    router = APIRouter(
        prefix="/os",
        tags=["Ordem de Serviço"],
        # Aqui você pode adicionar dependências comuns a todas as rotas
    )

    # ----------------------------------------------------
    # ROTA DE LEITURA (HTML e API) - Listar todas as OSs
    # ----------------------------------------------------
    @router.get("/", name="list_os")
    async def list_all_os(
        request: Request,
        db: AsyncSession = Depends(get_db) # Injeta a sessão do DB
    ):
        """
        Retorna a página HTML com a lista de Ordens de Serviço (view).
        """
        
        # 1. Chamar a Camada de Serviço para buscar os dados enriquecidos
        ordens_servico_enriched = await os_service.get_all_os(db)
        
        # 2. Renderizar o template Jinja2
        return templates.TemplateResponse(
            "os_list.html", # Você precisará criar este template em templates/
            {
                "request": request,
                "os_list": ordens_servico_enriched,
                "title": "Lista de Ordens de Serviço"
            }
        )

    return router