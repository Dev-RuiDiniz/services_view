from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated # Para a sintaxe moderna de Dependência

# Importa a Injeção de Dependência da sessão do DB
from database.db_setup import get_db

# Importa a Camada de Serviço
from services.os_service import OrdemServicoService

# Cria uma instância do Service Layer
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
        # Injeção Assíncrona do DB usando Annotated
        db: Annotated[AsyncSession, Depends(get_db)]
    ):
        """
        Busca todas as Ordens de Serviço, aplica enriquecimento e renderiza a view.
        """
        
        # 1. Chamar a Camada de Serviço para buscar os dados enriquecidos
        # O Service Layer executa o mapeamento READ e a lógica de enriquecimento.
        ordens_servico_enriched = await os_service.get_all_os(db)
        
        # 2. Utiliza templates.TemplateResponse para renderizar a View
        return templates.TemplateResponse(
            # Renderiza o template de listagem
            "os_list.html", 
            {
                "request": request,
                "os_list": ordens_servico_enriched,
                "title": "Lista de Ordens de Serviço"
            }
        )

    return router