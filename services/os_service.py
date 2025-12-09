from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
# Importante: func, case, Date, cast, Integer, exc, desc são necessários
from sqlalchemy import select, and_, func, case, Date, cast, Integer, exc, desc 
from uuid import UUID
import datetime
# Importar HTTPException e status de fastapi é crucial para o raise 404
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

    # ----------------------------------------------------
    # MÉTODOS CRUD (Assíncronos)
    # ----------------------------------------------------
    
    async def create_os(self, db: AsyncSession, os_data: Dict[str, Any]) -> OrdemServico:
        """Cria uma nova Ordem de Serviço e persiste no DB."""
        # 1. Cria a instância do modelo
        new_os = OrdemServico(**os_data)
        
        # 2. Adiciona à sessão e comita
        try:
            db.add(new_os)
            await db.commit()
            await db.refresh(new_os)
            return new_os
        except exc.IntegrityError:
            # Captura erro de chave duplicada (os_num, por exemplo)
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Ordem de Serviço com o número '{os_data.get('os_num')}' já existe."
            )
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao criar OS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro no banco de dados ao criar OS."
            )

    async def get_os_by_id(self, db: AsyncSession, os_id: UUID) -> OrdemServico:
        """Busca uma Ordem de Serviço pelo ID."""
        try:
            query = select(OrdemServico).where(OrdemServico.id == os_id)
            result = await db.execute(query)
            os_obj = result.scalar_one_or_none()

            # CORREÇÃO para test_get_os_by_id_not_found: Levantar 404 se não encontrado
            if os_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Ordem de Serviço com ID '{os_id}' não encontrada."
                )
            
            # Enriquecimento de dados (aplica o status calculado)
            os_obj.status_calculado = self._calculate_status(os_obj)
            
            # Formatação da data para o HTML
            os_obj.prazo_entrega_formatado = os_obj.prazo_entrega.strftime('%d/%m/%Y') if os_obj.prazo_entrega else None
            
            return os_obj
        except exc.SQLAlchemyError as e:
            if isinstance(e, HTTPException):
                raise
            print(f"Erro no banco de dados ao buscar OS por ID: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro no banco de dados ao buscar OS por ID."
            )


    async def get_list_os(
        self, 
        db: AsyncSession, 
        status_filter: Optional[str] = None, 
        os_num: Optional[str] = None # Parâmetro de filtro adicionado
    ) -> List[OrdemServico]:
        """Retorna todas as ordens de serviço, opcionalmente filtradas por status e/ou número da OS."""
        try:
            # 1. Monta a query base
            query = select(OrdemServico).order_by(desc(OrdemServico.data_criacao))
            
            # 2. Aplica Filtro de Status
            if status_filter:
                query = query.where(OrdemServico.status == status_filter)
                
            # 3. CORREÇÃO para test_get_list_os_with_no_results: Aplica Filtro de Número da OS
            if os_num:
                # Usando ilike para permitir busca parcial (mais robusto)
                # O teste deve passar ao buscar por um UUID que não existirá em 'os_num'
                query = query.where(OrdemServico.os_num.ilike(f'%{os_num}%')) 
            
            result = await db.execute(query)
            os_list = result.scalars().all()

            # Enriquecimento de dados (status_calculado e data formatada)
            for os_obj in os_list:
                os_obj.status_calculado = self._calculate_status(os_obj)
                os_obj.prazo_entrega_formatado = os_obj.prazo_entrega.strftime('%d/%m/%Y') if os_obj.prazo_entrega else None

            return os_list

        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao listar OSs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro no banco de dados ao listar OSs."
            )

    async def update_os(self, db: AsyncSession, os_id: UUID, os_data: Dict[str, Any]) -> OrdemServico:
        """Atualiza os dados de uma Ordem de Serviço existente."""
        
        # 1. Busca a OS (irá levantar 404 se não existir)
        existing_os = await self.get_os_by_id(db, os_id)
        
        # 2. Atualiza os campos
        for key, value in os_data.items():
            setattr(existing_os, key, value)
            
        # 3. Comita a transação
        try:
            await db.commit()
            await db.refresh(existing_os)
            return existing_os
        except exc.IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail=f"Ordem de Serviço com o número '{os_data.get('os_num')}' já existe."
            )
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao atualizar OS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro no banco de dados ao atualizar OS."
            )

    async def delete_os(self, db: AsyncSession, os_id: UUID) -> None:
        """Deleta uma Ordem de Serviço pelo ID."""
        
        # 1. Busca a OS (irá levantar 404 se não existir)
        os_to_delete = await self.get_os_by_id(db, os_id)
        
        # 2. Deleta e comita
        try:
            await db.delete(os_to_delete)
            await db.commit()
        except exc.SQLAlchemyError as e:
            await db.rollback()
            print(f"Erro no banco de dados ao deletar OS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro no banco de dados ao deletar OS."
            )

    # ----------------------------------------------------
    # MÉTODOS DE RELATÓRIO E AGGREGAÇÃO
    # ----------------------------------------------------

    async def get_kpis(self, db: AsyncSession) -> Dict[str, int]:
        """
        Calcula os KPIs: total de OSs, atrasadas, concluídas e em andamento.
        """
        hoje = datetime.date.today()

        # Definição dos cases para contagem agregada
        count_case = func.count(OrdemServico.id)
        
        # 1. Total de OSs
        total_os_agg = count_case.label('total_os')
        
        # 2. CORREÇÃO para test_get_kpis_aggregation: Garantir o label 'total_concluidas'
        concluidas_agg = func.sum(
            case(
                (OrdemServico.status.in_(["Concluída", "Cancelada"]), 1),
                else_=0
            )
        ).label('total_concluidas') 
        
        # 3. OSs Atrasadas (prazo_entrega < hoje E status não fixo)
        atrasadas_agg = func.sum(
            case(
                (
                    and_(
                        OrdemServico.prazo_entrega != None,
                        OrdemServico.prazo_entrega < hoje,
                        OrdemServico.status.notin_(["Concluída", "Cancelada"])
                    ), 
                    1
                ),
                else_=0
            )
        ).label('total_atrasadas')
        
        # 4. OSs Em Andamento (Pendente, Em Andamento, Aguardando Peças)
        em_andamento_status_agg = func.sum(
            case(
                (
                    OrdemServico.status.in_(["Pendente", "Em Andamento", "Aguardando Peças"]),
                    1
                ), 
                else_=0
            )
        ).label('total_em_andamento')


        try:
            # Cria a query de agregação
            kpi_query = select(
                total_os_agg,
                concluidas_agg,
                atrasadas_agg,
                em_andamento_status_agg
            )
            
            result = await db.execute(kpi_query)
            result_row = result.one()
            
            # Mapeamento do resultado para o dicionário (agora com o nome correto)
            kpis = {
                "total_os": result_row.total_os if result_row.total_os is not None else 0,
                "total_concluidas": result_row.total_concluidas if result_row.total_concluidas is not None else 0,
                "total_atrasadas": result_row.total_atrasadas if result_row.total_atrasadas is not None else 0,
                "total_em_andamento": result_row.total_em_andamento if result_row.total_em_andamento is not None else 0,
            }
            
            return kpis
            
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao calcular KPIs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro no banco de dados ao calcular KPIs."
            )

    async def get_status_distribution(self, db: AsyncSession) -> Dict[str, int]:
        # ... (implementação original)
        distribution_query = select(
            OrdemServico.status,
            func.count().label('count')
        ).group_by(OrdemServico.status)
        
        result = await db.execute(distribution_query)
        
        raw_data = {row.status: row.count for row in result}
        
        # Aplica o cálculo de status ('ATRASADO', 'PRÓXIMO DO PRAZO') na lista completa
        # É ineficiente, mas necessário se a lógica de _calculate_status for complexa
        full_list = await self.get_list_os(db) 
        
        # Dicionário final com status calculado
        final_distribution = {}
        for os_obj in full_list:
            calculated_status = self._calculate_status(os_obj)
            final_distribution[calculated_status] = final_distribution.get(calculated_status, 0) + 1
            
        return final_distribution
        
    async def get_os_by_month(self, db: AsyncSession) -> List[Dict[str, Any]]:
        # ... (implementação original)
        try:
            # 1. Extrair o mês e ano da data_entrada. O SQLite usa strftime.
            # %Y-%m produz uma string como '2023-11'
            month_year_format = func.strftime('%Y-%m', OrdemServico.data_entrada).label('mes')
            
            # 2. Consulta de Agregação
            trend_query = select(
                month_year_format,
                func.count().label('count')
            ).group_by(month_year_format).order_by(month_year_format) # Ordena cronologicamente
            
            result = await db.execute(trend_query)
            
            # Retorna o resultado como uma lista de dicionários [{\"mes\": \"YYYY-MM\", \"count\": N}, ...]
            return [
                {"mes": row.mes, "count": row.count} 
                for row in result
            ]
            
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar tendência mensal: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Erro no banco de dados ao buscar tendência mensal."
            )