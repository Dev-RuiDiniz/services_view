from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional
from datetime import date as dt_date
from fastapi.responses import RedirectResponse
from uuid import UUID

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
    # ROTA GET: Listar todas as OSs (READ All - VIEW)
    # ----------------------------------------------------
    @router.get("/", name="list_os")
    async def list_all_os(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)]
    ):
        """ Busca todas as Ordens de Serviço, aplica enriquecimento e renderiza a view index.html. """
        
        ordens_servico_enriched = await os_service.get_all_os(db)
        
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "os_list": ordens_servico_enriched,
                "title": "Lista de Ordens de Serviço"
            }
        )

    # ----------------------------------------------------
    # ROTA GET: Formulário de Nova OS (VIEW)
    # ----------------------------------------------------
    @router.get("/novo", name="new_os_form")
    def new_os_form(request: Request):
        """ Renderiza o template nova_os.html contendo o formulário de entrada de dados. """
        
        return templates.TemplateResponse(
            "nova_os.html", 
            {
                "request": request,
                "title": "Criar Nova Ordem de Serviço"
            }
        )
        
    # ----------------------------------------------------
    # ROTA POST: Criação de Nova OS (CREATE)
    # ----------------------------------------------------
    @router.post("/novo", name="create_os")
    async def create_os(
        db: Annotated[AsyncSession, Depends(get_db)],
        os_num: Annotated[str, Form()],
        cliente: Annotated[str, Form()],
        tipo: Annotated[str, Form()],
        equipamento: Annotated[str, Form()],
        status: Annotated[str, Form()],
        prazo_entrega: Annotated[Optional[str], Form()] = None
    ):
        """ Recebe os dados do formulário e cria um novo registro no DB. """
        
        prazo_date: Optional[dt_date] = None
        if prazo_entrega:
            try:
                prazo_date = dt_date.fromisoformat(prazo_entrega)
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de data inválido para Prazo de Entrega.")

        os_data = {
            "os_num": os_num,
            "cliente": cliente,
            "tipo": tipo,
            "equipamento": equipamento,
            "status": status,
            "prazo_entrega": prazo_date
        }

        try:
            await os_service.create_os(db, os_data)
        except Exception as e:
            print(f"Erro ao criar OS: {e}")
            raise HTTPException(status_code=500, detail="Falha ao registrar a Ordem de Serviço no banco de dados.")

        # Redirecionamento Pós-POST
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=status.HTTP_303_SEE_OTHER
        )


    # ----------------------------------------------------
    # ROTA GET: Formulário de Edição (READ by ID - VIEW)
    # ----------------------------------------------------
    @router.get("/editar/{os_id}", name="edit_os_form")
    async def edit_os_form(
        request: Request,
        os_id: UUID, # Captura o ID da URL
        db: Annotated[AsyncSession, Depends(get_db)]
    ):
        """
        Busca uma OS pelo ID e renderiza o formulário de edição pré-preenchido.
        """
        
        # 1. Busca o objeto ORM puro
        os_obj = await os_service.get_os_by_id(db, os_id)
        
        # 2. Verifica se a OS existe
        if os_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ordem de Serviço com ID '{os_id}' não encontrada."
            )
            
        # 3. Renderiza o template, passando o objeto OS puro
        return templates.TemplateResponse(
            "editar_os.html", 
            {
                "request": request,
                "os": os_obj, # Passa o objeto ORM para pré-preencher o formulário
                "title": f"Editar OS {os_obj.os_num}"
            }
        )

    # TODO: Implementar Rota POST/PUT /os/editar/{os_id} (UPDATE - Processamento do Formulário)
    # TODO: Implementar Rota DELETE /os/remover/{os_id} (DELETE)

    return router