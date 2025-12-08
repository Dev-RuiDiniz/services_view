from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional
from datetime import date as dt_date # Importa date como dt_date para evitar conflito com 'date' do Python

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
        
        # 1. Busca os dados enriquecidos (Service Layer)
        ordens_servico_enriched = await os_service.get_all_os(db)
        
        # 2. Renderiza o template de listagem
        return templates.TemplateResponse(
            "index.html", # Template principal
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
        # Rota síncrona, pois não toca no DB.
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
        request: Request, # Necessário para redirecionamento ou mensagem de erro
        # Utiliza Form() para injetar dados do formulário HTML
        os_num: Annotated[str, Form()],
        cliente: Annotated[str, Form()],
        tipo: Annotated[str, Form()],
        equipamento: Annotated[str, Form()],
        status: Annotated[str, Form()],
        # Prazo é opcional e vem como string, pode ser None se o campo estiver vazio
        prazo_entrega: Annotated[Optional[str], Form()] = None
    ):
        """
        Recebe os dados do formulário, valida e cria um novo registro no DB.
        """
        
        # 1. Pré-processamento e Validação de Dados
        
        # Converte a string de data para objeto datetime.date (ou None)
        prazo_date: Optional[dt_date] = None
        if prazo_entrega:
            try:
                # O input type="date" envia a string no formato 'YYYY-MM-DD'
                prazo_date = dt_date.fromisoformat(prazo_entrega)
            except ValueError:
                # Em um cenário real, você renderizaria o template com uma mensagem de erro
                raise HTTPException(status_code=400, detail="Formato de data inválido para Prazo de Entrega.")

        # 2. Prepara o dicionário de dados para o Service Layer
        os_data = {
            "os_num": os_num,
            "cliente": cliente,
            "tipo": tipo,
            "equipamento": equipamento,
            "status": status,
            "prazo_entrega": prazo_date
        }

        # 3. Chama a Camada de Serviço para Persistência
        try:
            await os_service.create_os(db, os_data)
        except Exception as e:
            # Em caso de falha no DB (ex: violação de unicidade), loga e retorna um erro
            print(f"Erro ao criar OS: {e}")
            raise HTTPException(status_code=500, detail="Falha ao registrar a Ordem de Serviço no banco de dados.")

        # 4. Redireciona o usuário de volta para a lista após o sucesso
        # Retorna o status 303 See Other (padrão após POST bem-sucedido)
        return templates.TemplateResponse(
            "redirect.html", 
            {
                "request": request,
                "redirect_url": router.url_path_for("list_os"),
                "message": "Ordem de Serviço criada com sucesso!"
            },
            status_code=status.HTTP_303_SEE_OTHER
        )

    # TODO: Implementar Rota GET /os/{os_id} (READ by ID)
    # TODO: Implementar Rota POST/PUT /os/editar/{os_id} (UPDATE)
    # TODO: Implementar Rota DELETE /os/remover/{os_id} (DELETE)

    return router