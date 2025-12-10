from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional, Dict, Any, List
from datetime import date as dt_date
from fastapi.responses import RedirectResponse
from uuid import UUID
import altair as alt
import pandas as pd
from starlette import status as http_status 

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
    """ Cria o gráfico de distribuição de status (barras) usando Altair e retorna o JSON. """
    if not data:
        return "{}"
        
    df = pd.DataFrame(data.items(), columns=['status', 'count'])
    
    status_colors = {
        'Concluída': '#28a745', 
        'Cancelada': '#6c757d', 
        'ATRASADO': '#dc3545', 
        'PRÓXIMO DO PRAZO': '#ffc107',
        'Pendente': '#007bff',
        'Em Andamento': '#17a2b8',
        'Aguardando Peças': '#17a2b8' # Usando azul claro similar para andamento
    }
    
    color_scale = alt.Scale(domain=list(status_colors.keys()), range=list(status_colors.values()))
    
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('status:N', title='Status da Ordem'),
        y=alt.Y('count:Q', title='Número de OSs'),
        color=alt.Color('status:N', scale=color_scale, legend=alt.Legend(title="Status")),
        tooltip=['status', 'count']
    ).properties(
        title="Distribuição de Status de Ordens de Serviço"
    ).interactive()

    return chart.to_json()


def create_monthly_trend_chart(data: List[Dict[str, Any]]) -> str:
    """ Cria o gráfico de tendência mensal (linha) usando Altair e retorna o JSON. """
    if not data:
        return "{}"

    df = pd.DataFrame(data)
    # Converte 'YYYY-MM' para um tipo data para o gráfico de linha
    df['mes_dt'] = pd.to_datetime(df['mes'] + '-01')

    chart = alt.Chart(df).mark_line(point=True, color='#007bff').encode(
        x=alt.X(
            'mes_dt:T', 
            title='Mês de Entrada', 
            axis=alt.Axis(format='%Y-%m') # Formato de exibição no eixo
        ), 
        y=alt.Y('count:Q', title='Novas OSs Registradas'),
        tooltip=[alt.Tooltip('mes', title='Mês'), alt.Tooltip('count', title='Contagem')]
    ).properties(
        title="Tendência de Entrada de Ordens de Serviço (Mensal)"
    ).interactive() 

    return chart.to_json()


# ----------------------------------------------------
# FUNÇÃO DE CONFIGURAÇÃO PRINCIPAL DO ROUTER
# ----------------------------------------------------
def os_router(templates: Jinja2Templates) -> APIRouter:
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
        status: Optional[str] = Query(None, alias="status"),
        cliente: Optional[str] = Query(None, alias="cliente")
    ):
        """ 
        Busca todas as Ordens de Serviço aplicando filtros e renderiza a view de listagem.
        """
        try:
            os_list = await os_service.get_all_os(db, status_filter=status, cliente=cliente)
            
            # Cria a lista de status únicos para o filtro do formulário (opcional)
            all_status = list(set([os['status'] for os in os_list]))
            
            context = {
                "request": request,
                "title": "Listagem de Ordens de Serviço",
                "os_list": os_list,
                # Usa uma lista fixa ou 'all_status' se preferir status dinâmicos
                "status_options": [
                    "Pendente", "Em Andamento", "Aguardando Peças", 
                    "Concluída", "Cancelada"
                ],
                "current_status": status if status else "",
                "current_cliente": cliente if cliente else ""
            }
            # O nome do template é "index.html" conforme o seu código
            return templates.TemplateResponse("index.html", context) 
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro inesperado ao listar OSs: {e}")
        
    # ----------------------------------------------------
    # ROTA GET: Painel de Controle (DASHBOARD)
    # ----------------------------------------------------
    @router.get("/dashboard", name="dashboard_view")
    async def dashboard_view(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """ Calcula e exibe KPIs e gráficos de análise. """
        try:
            kpis_data = await os_service.get_kpis(db) 
            
            status_distribution = await os_service.get_status_distribution(db)
            status_chart_spec_json = create_status_distribution_chart(status_distribution)
            
            os_by_month_data = await os_service.get_os_by_month(db)
            trend_chart_spec_json = create_monthly_trend_chart(os_by_month_data)
            
            context = {
                "request": request,
                "title": "Dashboard de Análise de OS",
                "kpis": kpis_data,
                "status_chart_spec": status_chart_spec_json,
                "trend_chart_spec": trend_chart_spec_json
            }

            return templates.TemplateResponse("dashboard.html", context)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro inesperado ao buscar dados do Dashboard: {e}")


    # ----------------------------------------------------
    # ROTA GET: Formulário de Nova OS (VIEW)
    # ----------------------------------------------------
    @router.get("/novo", name="new_os_form")
    def new_os_form(request: Request):
        """ Exibe o formulário para criação de uma nova OS. """
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
        """ Processa a criação da OS via formulário. """
        
        # 1. VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS
        required_fields = {
            "os_num": os_num,
            "cliente": cliente,
            "tipo": tipo,
            "equipamento": equipamento,
            "status": status,
        }
        
        missing_fields = [
            label for label, value in required_fields.items() 
            if not value or value.strip() == ""
        ]

        if missing_fields:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, 
                detail=f"Os seguintes campos são obrigatórios e não podem estar vazios: {', '.join(missing_fields).title()}"
            )
        
        # 2. VALIDAÇÃO DE DATA
        prazo_date: Optional[dt_date] = None
        if prazo_entrega:
            try:
                prazo_date = dt_date.fromisoformat(prazo_entrega)
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST, 
                    detail="Formato de data inválido para Prazo de Entrega. Use o formato YYYY-MM-DD."
                )

        os_data = {
            "os_num": os_num,
            "cliente": cliente,
            "tipo": tipo,
            "equipamento": equipamento,
            "status": status,
            "prazo_entrega": prazo_date
        }

        # 3. CHAMADA AO SERVICE LAYER
        try:
            await os_service.create_os(db, os_data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocorreu um erro interno ao criar OS: {e}") 

        # Redirecionamento Pós-POST
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=http_status.HTTP_303_SEE_OTHER 
        )


    # ----------------------------------------------------
    # ROTA GET: Formulário de Edição (READ by ID - VIEW)
    # ----------------------------------------------------
    @router.get("/editar/{os_id}", name="edit_os_form")
    async def edit_os_form(
        request: Request,
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)]
    ):
        """ Exibe o formulário pré-preenchido para edição de uma OS. """
        try:
            # os_data é o objeto ORM (os_service.get_os_by_id levanta 404 se não encontrado)
            os_data = await os_service.get_os_by_id(db, os_id)
            
            # Garante que o formato da data é ISO para preencher o campo de input HTML
            prazo_entrega_iso = os_data.prazo_entrega.isoformat() if os_data.prazo_entrega else ""
            
            context = {
                "request": request,
                "title": f"Editar OS #{os_data.os_num}",
                "os": os_data,
                "prazo_entrega_iso": prazo_entrega_iso
            }
            return templates.TemplateResponse("editar_os.html", context)
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro inesperado ao carregar dados de edição: {e}") 
        
    # ----------------------------------------------------
    # ROTA POST: Processar Edição (UPDATE)
    # ----------------------------------------------------
    @router.post("/editar/{os_id}", name="update_os")
    async def update_os(
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)],
        os_num: Annotated[str, Form()],
        cliente: Annotated[str, Form()],
        tipo: Annotated[str, Form()],
        equipamento: Annotated[str, Form()],
        status: Annotated[str, Form()],
        prazo_entrega: Annotated[Optional[str], Form()] = None
    ):
        """ Processa a atualização da OS via formulário. """
        
        # 1. VALIDAÇÃO DE CAMPOS OBRIGATÓRIOS
        required_fields = {"os_num": os_num, "cliente": cliente, "tipo": tipo, "equipamento": equipamento, "status": status}
        missing_fields = [label for label, value in required_fields.items() if not value or value.strip() == ""]
        if missing_fields:
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Campos obrigatórios ausentes: {', '.join(missing_fields).title()}")
        
        # 2. VALIDAÇÃO DE DATA
        prazo_date: Optional[dt_date] = None
        if prazo_entrega:
            try:
                prazo_date = dt_date.fromisoformat(prazo_entrega)
            except ValueError:
                raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="Formato de data inválido para Prazo de Entrega.")

        os_data = {
            "os_num": os_num, "cliente": cliente, "tipo": tipo, 
            "equipamento": equipamento, "status": status, "prazo_entrega": prazo_date
        }

        # 3. CHAMADA AO SERVICE LAYER
        try:
            await os_service.update_os(db, os_id, os_data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocorreu um erro interno ao atualizar OS: {e}")

        # Redirecionamento Pós-POST
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=http_status.HTTP_303_SEE_OTHER 
        )


    # ----------------------------------------------------
    # ROTA POST: Exclusão de OS (DELETE)
    # ----------------------------------------------------
    @router.post("/deletar/{os_id}", name="delete_os")
    async def delete_os(
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """ Processa a exclusão de uma OS. """
        try:
            await os_service.delete_os(db, os_id)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocorreu um erro interno ao deletar OS: {e}")

        # Redirecionamento Pós-POST
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=http_status.HTTP_303_SEE_OTHER
        )


    return router