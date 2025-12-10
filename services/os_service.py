from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
# Importações necessárias do SQLAlchemy para agregação
from sqlalchemy import select, and_, func, case, Date, cast, Integer, exc, desc
from uuid import UUID
import datetime
# Importações de FastAPI
from fastapi import HTTPException, status 

class OrdemServicoService:
    """
    Serviços de Ordem de Serviço. Contém a lógica de negócio e mapeamento CRUD assíncrono,
    incluindo enriquecimento de dados e tratamento de erros do banco de dados.
    """
    
    # ... [Métodos auxiliares e CRUD (CREATE, GET ALL, GET BY ID, UPDATE, DELETE) inalterados] ...

    def _calculate_status(self, os: OrdemServico) -> str:
# ... (conteúdo da função _calculate_status inalterado) ...
        # Se a OS já está concluída ou cancelada, não precisa calcular.
        if os.status in ["Concluída", "Cancelada"]:
            return os.status
        
        if os.prazo_entrega is not None:
            hoje = datetime.date.today()
            diferenca = (os.prazo_entrega - hoje).days

            if diferenca < 0:
                return "ATRASADO"
            elif diferenca <= 3:
                return "PRÓXIMO DO PRAZO"
        
        # Retorna o status original se não houver condição especial
        return os.status
    
    
    def _format_date(self, date_orm: Optional[datetime.date]) -> Optional[str]:
# ... (conteúdo da função _format_date inalterado) ...
        if date_orm:
            # Garante que funciona mesmo se for datetime (se data_entrada for datetime)
            if isinstance(date_orm, datetime.datetime):
                date_orm = date_orm.date()
            return date_orm.strftime('%d/%m/%Y')
        return None
    
    
    def _enrich_os_data(self, os_list: List[OrdemServico]) -> List[Dict[str, Any]]:
# ... (conteúdo da função _enrich_os_data inalterado) ...
        enriched_list = []
        for os in os_list:
            # Garante que dados ORM são acessados antes da sessão ser fechada
            os_dict = os.__dict__.copy()
            os_dict.pop('_sa_instance_state', None)
            
            # Garante que o UUID é serializável
            os_dict['id'] = str(os_dict['id'])
            
            # Enriquecimento
            os_dict['status_calculado'] = self._calculate_status(os)
            os_dict['data_entrada_formatada'] = self._format_date(os.data_entrada)
            os_dict['prazo_entrega_formatado'] = self._format_date(os.prazo_entrega)
            
            enriched_list.append(os_dict)
        return enriched_list
    
    
    # ----------------------------------------------------
    # MÉTODOS CRUD (Assíncronos)
    # ----------------------------------------------------
    async def create_os(self, db: AsyncSession, os_data: dict) -> OrdemServico:
# ... (conteúdo da função create_os inalterado) ...
        try:
            novo_os = OrdemServico(**os_data)
            db.add(novo_os)
            await db.commit()
            await db.refresh(novo_os) 
            return novo_os
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao criar OS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha no banco de dados ao criar a Ordem de Serviço."
            )

    async def get_all_os(
        self, 
        db: AsyncSession,
        status_filter: Optional[str] = None,
        cliente: Optional[str] = None
    ) -> List[Dict[str, Any]]:
# ... (conteúdo da função get_all_os inalterado) ...
        try:
            query = select(OrdemServico)
            conditions = []
            
            if status_filter:
                conditions.append(OrdemServico.status == status_filter)
            if cliente:
                conditions.append(OrdemServico.cliente.ilike(f'%{cliente}%'))
                
            if conditions:
                query = query.where(and_(*conditions))

            result = await db.execute(query.order_by(desc(OrdemServico.data_entrada)))
            os_list = result.scalars().all()
            
            # Aplica o enriquecimento de dados antes de retornar
            return self._enrich_os_data(os_list)
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar todas as OSs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados."
            )

    async def get_os_by_id(self, db: AsyncSession, os_id: UUID) -> Optional[OrdemServico]:
# ... (conteúdo da função get_os_by_id inalterado) ...
        try:
            query = select(OrdemServico).where(OrdemServico.id == os_id)
            result = await db.execute(query)
            
            os_obj = result.scalars().one_or_none()
            
            # Levanta 404 se não encontrado (Melhoria)
            if os_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Ordem de Serviço com ID '{os_id}' não encontrada."
                )
            
            return os_obj
        except HTTPException:
            raise
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar OS por ID: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados."
            )
        
    async def update_os(self, db: AsyncSession, os_id: UUID, os_data: Dict[str, Any]) -> OrdemServico:
# ... (conteúdo da função update_os inalterado) ...
        # get_os_by_id já levanta 404 se não encontrado
        os_existente = await self.get_os_by_id(db, os_id)
        
        try:
            for key, value in os_data.items():
                if key not in ['id', 'data_criacao', 'data_entrada'] and hasattr(os_existente, key):
                    setattr(os_existente, key, value)
                    
            await db.commit()
            await db.refresh(os_existente)
            
            return os_existente
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao atualizar OS {os_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha no banco de dados ao atualizar a Ordem de Serviço."
            )

    async def delete_os(self, db: AsyncSession, os_id: UUID) -> bool:
# ... (conteúdo da função delete_os inalterado) ...
        # get_os_by_id já levanta 404 se não encontrado
        os_existente = await self.get_os_by_id(db, os_id)
            
        try:
            await db.delete(os_existente)
            await db.commit()
            
            return True
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao deletar OS {os_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha no banco de dados ao deletar a Ordem de Serviço."
            )
    
    # ----------------------------------------------------
    # MÉTODOS DE ANÁLISE (DASHBOARD)
    # ----------------------------------------------------
    
    async def get_kpis(self, db: AsyncSession) -> Dict[str, int]:
        """
        Calcula os Key Performance Indicators (KPIs) principais: 
        Total, Concluídas, Atrasadas e Em Andamento.
        """
        hoje = datetime.date.today()

        # 1. Definição dos Cases para Agregação
        
        # Total Concluídas/Canceladas (Status Fixo)
        case_concluidas = case(
            (OrdemServico.status.in_(['Concluída', 'Cancelada']), 1),
            else_=0
        )
        
        # Total Atrasadas (Calculado: Prazo < Hoje E Status NÃO é final)
        case_atrasadas = case(
            (
                and_(
                    OrdemServico.prazo_entrega < hoje,
                    OrdemServico.status.notin_(['Concluída', 'Cancelada'])
                ),
                1
            ),
            else_=0
        )
        
        # 2. Consulta de Agregação
        # Inclui o cálculo de total_atrasadas
        query = select(
            func.count(OrdemServico.id).label('total_os'),
            func.sum(case_concluidas).label('total_concluidas'),
            func.sum(case_atrasadas).label('total_atrasadas'), 
        )
        
        try:
            result = await db.execute(query)
            row = result.one()
            
            # 3. Mapeamento para o dicionário de resultado
            kpis = {
                "total_os": row.total_os if row.total_os is not None else 0,
                "total_concluidas": row.total_concluidas if row.total_concluidas is not None else 0,
                "total_atrasadas": row.total_atrasadas if row.total_atrasadas is not None else 0,
            }
            
            # 4. Cálculo do KPI Em Andamento
            kpis["total_em_andamento"] = kpis["total_os"] - kpis["total_concluidas"] - kpis["total_atrasadas"]
            
            return kpis
            
        except Exception as e:
            # Tratamento de erro (retorna 0s para evitar falha do servidor)
            print(f"Erro no banco de dados ao buscar KPIs: {e}")
            return {
                "total_os": 0,
                "total_concluidas": 0,
                "total_atrasadas": 0,
                "total_em_andamento": 0,
            }
        
    async def get_status_distribution(self, db: AsyncSession) -> Dict[str, int]:
# ... (conteúdo da função get_status_distribution inalterado) ...
        try:
            hoje = datetime.date.today()
            
            # Lógica para Atrasado/Próximo do Prazo/Status Original
            status_calculado_sql = case(
                # Caso 1: Atrasado
                (
                    and_(
                        OrdemServico.prazo_entrega != None,
                        OrdemServico.prazo_entrega < hoje,
                        OrdemServico.status.notin_(["Concluída", "Cancelada"])
                    ), 
                    "ATRASADO"
                ),
                # Caso 2: Próximo do Prazo (Hoje até +3 dias)
                (
                    and_(
                        OrdemServico.prazo_entrega != None,
                        OrdemServico.prazo_entrega >= hoje,
                        # Adicionando 3 dias à data de hoje
                        OrdemServico.prazo_entrega <= hoje + datetime.timedelta(days=3),
                        OrdemServico.status.notin_(["Concluída", "Cancelada"])
                    ), 
                    "PRÓXIMO DO PRAZO"
                ),
                # Caso 3: Status Original (Padrão)
                else_=OrdemServico.status
            ).label('status_agregado')
            
            # Consulta de Agregação
            distribution_query = select(
                status_calculado_sql,
                func.count().label('count')
            ).group_by(status_calculado_sql)
            
            result = await db.execute(distribution_query)
            
            return {row.status_agregado: row.count for row in result}
            
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar distribuição de status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na agregação de dados do banco de dados para Distribuição de Status."
            )
        
    async def get_os_by_month(self, db: AsyncSession) -> List[Dict[str, Any]]:
# ... (conteúdo da função get_os_by_month inalterado) ...
        try:
            # Extrai o mês e ano.
            month_year_format = func.strftime('%Y-%m', OrdemServico.data_entrada).label('mes')
            
            # Consulta de Agregação
            trend_query = select(
                month_year_format,
                func.count().label('count')
            ).group_by(month_year_format).order_by(month_year_format)
            
            result = await db.execute(trend_query)
            
            return [
                {"mes": row.mes, "count": row.count} 
                for row in result
            ]
            
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar tendência mensal: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na agregação de dados do banco de dados para Tendência Mensal."
            )