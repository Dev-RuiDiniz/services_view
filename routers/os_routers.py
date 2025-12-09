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
# FUNÇÃO AUXILIAR: GERAÇÃO DE GRÁFICO (Altair)
# ----------------------------------------------------
def create_status_distribution_chart(data: Dict[str, int]) -> str:
    """
    Cria um gráfico de barras Altair a partir da distribuição de status.
    Retorna a especificação do gráfico em formato JSON.
    """
    if not data:
        return "{}"

    # 1. Converter dicionário para DataFrame do Pandas (necessário para Altair)
    df = pd.DataFrame(data.items(), columns=['Status', 'Contagem'])
    
    # 2. Definir uma ordem de status e escala de cores
    status_order = ['ATRASADO', 'Pendente', 'Em Andamento', 'Aguardando Peça', 'Concluída', 'Cancelada']
    color_range = ['#d9534f', '#f0ad4e', '#5bc0de', '#5cb85c', '#28a745', '#777777'] 
    
    color_scale = alt.Scale(domain=status_order, range=color_range)

    # 3. Criar o Gráfico de Barras
    chart = alt.Chart(df).mark_bar().encode(
        # X: Status (Nominal, ordenado pela contagem decrescente)
        x=alt.X('Status:N', sort=status_order, title='Status da OS'), 
        # Y: Contagem (Quantitativo)
        y=alt.Y('Contagem:Q', title='Quantidade de OSs'),
        # Cor: Pelo Status
        color=alt.Color('Status:N', scale=color_scale),
        tooltip=['Status', 'Contagem']
    ).properties(
        title="Distribuição de Ordens de Serviço por Status"
    ).interactive() # Permite zoom e pan

    # Retorna a especificação do gráfico em JSON
    return chart.to_json()


# ----------------------------------------------------
# FUNÇÃO DE CONFIGURAÇÃO PRINCIPAL DO ROUTER
# ----------------------------------------------------
def os_router(templates: Jinja2Templates) -> APIRouter:
    """
    Configura e retorna o APIRouter para as rotas de Ordem de Serviço,
    incluindo CRUD, filtragem e Dashboard.
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
        Busca todas as Ordens de Serviço, aplicando filtros recebidos via URL, 
        e renderiza a view index.html. 
        """
        
        # Chama a Camada de Serviço, passando os filtros
        ordens_servico_enriched = await os_service.get_all_os(
            db, 
            status=status, 
            cliente=cliente
        )
        
        # Renderiza o template de listagem
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request,
                "os_list": ordens_servico_enriched,
                "title": "Lista de Ordens de Serviço",
                "current_status_filter": status or "", # Adiciona filtros para persistência na view
                "current_cliente_filter": cliente or ""
            }
        )
        
    # ----------------------------------------------------
    # ROTA GET: Painel de Controle (DASHBOARD)
    # ----------------------------------------------------
    @router.get("/dashboard", name="dashboard_view")
    async def dashboard_view(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """
        Busca os KPIs e dados analíticos, gera os gráficos e renderiza o dashboard.
        """
        # 1. Obter os dados de KPIs (Total, Atrasados, Média)
        kpis_data = await os_service.get_kpis(db) 
        
        # 2. Obter a distribuição de status para o gráfico
        status_distribution = await os_service.get_status_distribution(db)
        
        # 3. Gerar o JSON do gráfico de distribuição
        status_chart_spec_json = create_status_distribution_chart(status_distribution)
        
        # 4. Obter a tendência por mês (próxima tarefa)
        os_by_month_data = await os_service.get_os_by_month(db)
        
        # 5. Preparar o contexto para o template
        context = {
            "request": request,
            "title": "Dashboard de Análise de OS",
            "kpis": kpis_data, # Dicionário completo de KPIs
            "status_chart_spec": status_chart_spec_json, # JSON do gráfico de distribuição
            "os_by_month_data": os_by_month_data # Dados para o gráfico de tendência
        }

        # 6. Renderizar o template
        return templates.TemplateResponse("dashboard.html", context)


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
        """ Busca uma OS pelo ID e renderiza o formulário de edição pré-preenchido. """
        
        os_obj = await os_service.get_os_by_id(db, os_id)
        
        if os_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ordem de Serviço com ID '{os_id}' não encontrada."
            )
            
        return templates.TemplateResponse(
            "editar_os.html", 
            {
                "request": request,
                "os": os_obj, # Passa o objeto ORM para pré-preencher
                "title": f"Editar OS {os_obj.os_num}"
            }
        )
        
    # ----------------------------------------------------
    # ROTA POST: Processar Edição (UPDATE)
    # ----------------------------------------------------
    @router.post("/editar/{os_id}", name="update_os")
    async def update_os(
        os_id: UUID, # ID da OS a ser atualizada
        db: Annotated[AsyncSession, Depends(get_db)],
        # Captura todos os campos do formulário
        os_num: Annotated[str, Form()],
        cliente: Annotated[str, Form()],
        tipo: Annotated[str, Form()],
        equipamento: Annotated[str, Form()],
        status: Annotated[str, Form()],
        prazo_entrega: Annotated[Optional[str], Form()] = None
    ):
        """ Recebe os dados do formulário de edição e atualiza o registro no DB. """
        
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
            await os_service.update_os(db, os_id, os_data)
        except HTTPException as e:
            # Re-lança 404
            raise e 
        except Exception as e:
            print(f"Erro interno ao atualizar OS {os_id}: {e}")
            raise HTTPException(status_code=500, detail="Falha ao atualizar a Ordem de Serviço.")

        # Redireciona para a lista
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=status.HTTP_303_SEE_OTHER
        )

    # ----------------------------------------------------
    # ROTA POST: Exclusão de OS (DELETE)
    # ----------------------------------------------------
    @router.post("/deletar/{os_id}", name="delete_os")
    async def delete_os(
        os_id: UUID, # ID da OS a ser deletada
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """ Remove um registro do banco de dados e redireciona. """
        
        try:
            await os_service.delete_os(db, os_id)
        except HTTPException as e:
            # Re-lança 404
            raise e
        except Exception as e:
            print(f"Erro interno ao deletar OS {os_id}: {e}")
            raise HTTPException(status_code=500, detail="Falha ao remover a Ordem de Serviço.")

        # Redirecionamento Pós-DELETE
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=status.HTTP_303_SEE_OTHER
        )

    return router # RETORNO FINAL DO ROUTER