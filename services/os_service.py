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
    
    # ----------------------------------------------------
    # MÉTODOS AUXILIARES DE ENRIQUECIMENTO DE DADOS (Síncronos)
    # ----------------------------------------------------
    
    def _calculate_status(self, os: OrdemServico) -> str:
        """
        Calcula um status customizado (ex: 'ATRASADO') baseado na data de prazo
        e no status atual da OS.
        """
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
        """
        Formata um objeto datetime.date/datetime.datetime em uma string 'dd/mm/YYYY'.
        """
        if date_orm:
            # Garante que funciona mesmo se for datetime (se data_entrada for datetime)
            if isinstance(date_orm, datetime.datetime):
                date_orm = date_orm.date()
            return date_orm.strftime('%d/%m/%Y')
        return None
    
    
    def _enrich_os_data(self, os_list: List[OrdemServico]) -> List[Dict[str, Any]]:
        """
        Transforma a lista de objetos ORM em uma lista de dicionários enriquecidos
        com status calculado e datas formatadas para a view.
        """
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
        """ Cria e persiste uma nova Ordem de Serviço. """
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
        """ Busca todas as Ordens de Serviço, aplicando filtros opcionais. """
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
        """ Busca uma única Ordem de Serviço pelo seu UUID. """
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
        """ Atualiza os atributos de uma Ordem de Serviço existente e persiste. """
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
        """ Remove um registro de Ordem de Serviço pelo ID. """
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
    
    async def get_kpis(self, db: AsyncSession) -> Dict[str, Any]:
        """ 
        Calcula os Key Performance Indicators (KPIs) agregados: total, atrasadas, 
        e média de prazo.
        """
        try:
            # 1. Expressão para calcular a diferença de dias (SQLite usa julianday para datas)
            dias_prazo = func.julianday(OrdemServico.prazo_entrega) - func.julianday(OrdemServico.data_entrada)
            
            # 2. Lógica de OS Atrasada em SQL
            hoje = datetime.date.today()
            
            os_atrasadas_case = case(
                (
                    and_(
                        # Prazo não nulo
                        OrdemServico.prazo_entrega != None,
                        # Prazo é anterior a hoje
                        OrdemServico.prazo_entrega < hoje,
                        # Status ainda está em aberto
                        OrdemServico.status.notin_(["Concluída", "Cancelada"])
                    ), 
                    1
                ), 
                else_=0
            )

            # 3. Consulta principal
            kpis_query = select(
                func.count(OrdemServico.id).label('total_os'),
                func.sum(os_atrasadas_case).label('atrasadas_count'),
                func.avg(dias_prazo).label('media_prazo_dias')
            )
            
            result = await db.execute(kpis_query)
            kpis_row = result.first()
            
            if not kpis_row:
                 kpis_data = {"total_os": 0, "atrasadas_count": 0, "media_prazo_dias": None}
            else:
                 kpis_dict = kpis_row._asdict()
                 
                 # Mapeamento e tratamento de NULL/None
                 kpis_data = {
                     "total_os": int(kpis_dict.get('total_os', 0) or 0),
                     "atrasadas_count": int(kpis_dict.get('atrasadas_count', 0) or 0),
                     "media_prazo_dias": round(float(kpis_dict.get('media_prazo_dias')), 2) 
                                         if kpis_dict.get('media_prazo_dias') is not None else None
                 }
            
            return kpis_data
            
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao calcular KPIs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura e agregação de dados do banco de dados para KPIs."
            )
        
    async def get_status_distribution(self, db: AsyncSession) -> Dict[str, int]:
        """ 
        Calcula a contagem de Ordens de Serviço agrupadas pelo status (incluindo o status calculado em SQL).
        """
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
        """ 
        Calcula a contagem de Ordens de Serviço agrupadas pelo mês de entrada ('YYYY-MM').
        """
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