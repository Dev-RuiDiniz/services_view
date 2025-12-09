from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional, Dict, Any, List
from datetime import date as dt_date
# Importar RedirectResponse é essencial para o sucesso do POST
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
    # ... (código para gerar o gráfico de distribuição, mantido inalterado) ...
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
        'Aguardando Peças': '#ff8c00', 
    }
    
    # Mapeamento para garantir que as cores do status calculado estejam corretas
    color_scale = alt.Scale(
        domain=list(status_colors.keys()), 
        range=list(status_colors.values())
    )

    chart = alt.Chart(df).mark_arc(outerRadius=120).encode(
        theta=alt.Theta("count", stack=True),
        color=alt.Color("status", scale=color_scale),
        order=alt.Order("count", sort="descending"),
        tooltip=["status", "count"]
    ).properties(
        title="Distribuição de Ordens de Serviço por Status"
    ).to_json()
    
    return chart

def create_monthly_trend_chart(data: List[Dict[str, Any]]) -> str:
    # ... (código para gerar o gráfico de tendência, mantido inalterado) ...
    if not data:
        return "{}"
        
    df = pd.DataFrame(data)
    
    # Converte 'mes' (string 'YYYY-MM') para data para ordenação correta no gráfico
    df['date'] = pd.to_datetime(df['mes'])
    
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X('date', axis=alt.Axis(title='Mês de Entrada', format='%Y-%m')),
        y=alt.Y('count', title='Nº de OSs Criadas'),
        tooltip=['mes', 'count']
    ).properties(
        title='Tendência de Abertura de OSs (Mensal)'
    ).to_json()
    
    return chart


# ----------------------------------------------------
# FUNÇÃO PRINCIPAL: CRIAÇÃO DO ROUTER
# ----------------------------------------------------
def os_router(templates: Jinja2Templates) -> APIRouter:
    # Configura o prefixo e as tags
    router = APIRouter(prefix="/os", tags=["Ordens de Serviço"])

    # ----------------------------------------------------
    # ROTA GET: Listagem de OSs (list_os)
    # ----------------------------------------------------
    @router.get("/", name="list_os")
    async def list_os(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
        status_filter: Optional[str] = Query(None, alias="status"),
        # CORREÇÃO: Adicionar o parâmetro os_num para filtragem
        os_num_filter: Optional[str] = Query(None, alias="os_num"),
    ):
        """ Retorna a listagem HTML de Ordens de Serviço com filtros opcionais. """
        
        # 1. Chama a camada de serviço com os filtros
        os_list = await os_service.get_list_os(
            db, 
            status_filter=status_filter,
            os_num=os_num_filter # Passando o novo filtro
        )
        
        # 2. Renderiza o template
        return templates.TemplateResponse(
            "os_list.html",
            {
                "request": request,
                "title": "Listagem de Ordens de Serviço",
                "os_list": os_list,
                "selected_status": status_filter,
                "selected_os_num": os_num_filter, # Passando o filtro de volta para o template
                "status_options": [
                    "Pendente", "Em Andamento", "Aguardando Peças", 
                    "Concluída", "Cancelada"
                ]
            }
        )
        
    # ----------------------------------------------------
    # ROTA GET: Formulário de Criação (new_os_form)
    # ----------------------------------------------------
    @router.get("/novo", name="new_os_form")
    async def new_os_form(request: Request):
        """ Retorna o formulário HTML para criar uma nova OS. """
        return templates.TemplateResponse(
            "nova_os.html", 
            {"request": request, "title": "Criar Nova OS"}
        )

    # ----------------------------------------------------
    # ROTA POST: Criação de Nova OS (POST)
    # ----------------------------------------------------
    @router.post("/novo", name="create_os")
    async def create_os(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
        os_num: str = Form(...),
        cliente: str = Form(...),
        tipo: str = Form(...),
        equipamento: str = Form(...),
        status: str = Form(...),
        prazo_entrega: Optional[str] = Form(None), 
    ):
        """ Processa a submissão do formulário para criar uma nova OS. """
        
        # 1. Validação e conversão (Prazo)
        try:
            prazo_date = dt_date.fromisoformat(prazo_entrega) if prazo_entrega else None
        except ValueError:
            # Retorna o formulário com erro se a data for inválida
            return templates.TemplateResponse(
                "nova_os.html", 
                {
                    "request": request, 
                    "title": "Criar Nova OS",
                    "error_message": "O formato do Prazo de Entrega é inválido.",
                    "os_data": {
                        "os_num": os_num, 
                        "cliente": cliente, 
                        "tipo": tipo, 
                        "equipamento": equipamento, 
                        "status": status,
                        "prazo_entrega": prazo_entrega
                    }
                }
            )

        os_data = {
            "os_num": os_num,
            "cliente": cliente,
            "tipo": tipo,
            "equipamento": equipamento,
            "status": status,
            "prazo_entrega": prazo_date,
        }

        # 2. Chamada ao Service Layer
        try:
            await os_service.create_os(db, os_data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ocorreu um erro interno: {e}")

        # 3. CORREÇÃO para test_post_create_os_success: Redirecionamento Pós-POST (303 SEE OTHER)
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=http_status.HTTP_303_SEE_OTHER 
        )

    # ----------------------------------------------------
    # ROTA GET: Formulário de Edição (edit_os_form)
    # ----------------------------------------------------
    @router.get("/editar/{os_id}", name="edit_os_form")
    async def edit_os_form(
        request: Request,
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """ Retorna o formulário HTML pré-preenchido para edição de uma OS. """
        os_obj = await os_service.get_os_by_id(db, os_id)
        
        return templates.TemplateResponse(
            "editar_os.html", 
            {
                "request": request, 
                "title": f"Editar OS {os_obj.os_num}",
                "os": os_obj
            }
        )

    # ----------------------------------------------------
    # ROTA POST: Atualização de OS (PUT/PATCH via POST)
    # ----------------------------------------------------
    @router.post("/editar/{os_id}", name="update_os")
    async def update_os(
        request: Request,
        os_id: UUID,
        db: Annotated[AsyncSession, Depends(get_db)],
        os_num: str = Form(...),
        cliente: str = Form(...),
        tipo: str = Form(...),
        equipamento: str = Form(...),
        status: str = Form(...),
        prazo_entrega: Optional[str] = Form(None),
    ):
        """ Processa a submissão do formulário para atualizar uma OS existente. """
        
        # 1. Validação e conversão (Prazo)
        try:
            prazo_date = dt_date.fromisoformat(prazo_entrega) if prazo_entrega else None
        except ValueError:
            # Se a data for inválida, retorna o formulário com erro
            os_obj = await os_service.get_os_by_id(db, os_id) # Busca para obter o objeto completo
            return templates.TemplateResponse(
                "editar_os.html", 
                {
                    "request": request, 
                    "title": f"Editar OS {os_obj.os_num}",
                    "os": os_obj,
                    "error_message": "O formato do Prazo de Entrega é inválido."
                }
            )
            
        # 2. Prepara os dados
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
            
        # Redireciona para a listagem após a exclusão
        return RedirectResponse(
            url=router.url_path_for("list_os"), 
            status_code=http_status.HTTP_303_SEE_OTHER 
        )

    # ----------------------------------------------------
    # ROTA GET: Dashboard
    # ----------------------------------------------------
    @router.get("/dashboard", name="dashboard_view")
    async def dashboard_view(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
    ):
        """ Retorna a página de dashboard com gráficos e KPIs. """
        
        # 1. Busca os dados brutos
        kpis = await os_service.get_kpis(db)
        distribution_data = await os_service.get_status_distribution(db)
        trend_data = await os_service.get_os_by_month(db)
        
        # 2. Gera as especificações dos gráficos Altair/Vega-Lite (JSON)
        status_chart_spec = create_status_distribution_chart(distribution_data)
        trend_chart_spec = create_monthly_trend_chart(trend_data)
        
        # 3. Renderiza o template
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "title": "Dashboard de Ordens de Serviço",
                "kpis": kpis,
                "status_chart_spec": status_chart_spec,
                "trend_chart_spec": trend_chart_spec,
            }
        )

    return router