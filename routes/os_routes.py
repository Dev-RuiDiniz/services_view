from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated # <-- Importação necessária para a sintaxe moderna

# Importa a Injeção de Dependência da sessão do DB
from database.db_setup import get_db

# Importa a Camada de Serviço
from services.os_service import OrdemServicoService

# Criamos uma instância do Service Layer
os_service = OrdemServicoService()


def os_router(templates: Jinja2Templates) -> APIRouter:
    """
    Configura e retorna o APIRouter para as rotas de Ordem de Serviço.
    """
    router = APIRouter(
        prefix="/os",
        tags=["Ordem de Serviço"],
    )

    # ----------------------------------------------------
    # ROTA DE LEITURA (GET /os/) - Listar todas as OSs
    # ----------------------------------------------------
    @router.get("/", name="list_os")
    async def list_all_os(
        request: Request,
        # INJEÇÃO ATUALIZADA: Usando Annotated para tipagem clara e Depends
        db: Annotated[AsyncSession, Depends(get_db)]
    ):
        """
        Busca e retorna a página HTML com a lista de Ordens de Serviço.
        """
        
        # 1. Chamar a Camada de Serviço para buscar os dados enriquecidos
        ordens_servico_enriched = await os_service.get_all_os(db)
        
        # 2. Renderizar o template Jinja2
        # É obrigatório passar o objeto request para Jinja2Templates
        return templates.TemplateResponse(
            "os_list.html", 
            {
                "request": request,
                "os_list": ordens_servico_enriched,
                "title": "Lista de Ordens de Serviço"
            }
        )

    return router