from sqlalchemy.ext.asyncio import AsyncSession
from models.os_model import OrdemServico 
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, func, case, Date, cast, Integer, exc # Importar exc para exceções do SQLAlchemy
from uuid import UUID
import datetime
from fastapi import HTTPException, status # Importar status para códigos HTTP

class OrdemServicoService:
    # ... (métodos auxiliares _calculate_status, _format_date, _enrich_os_data) ...

    # ----------------------------------------------------
    # Mapeamento CREATE
    # ----------------------------------------------------
    async def create_os(self, db: AsyncSession, os_data: dict) -> OrdemServico:
        """ Cria uma nova Ordem de Serviço, com tratamento de erro. """
        try:
            novo_os = OrdemServico(**os_data)
            db.add(novo_os)
            await db.commit()
            await db.refresh(novo_os) 
            return novo_os
        except exc.SQLAlchemyError as e:
            await db.rollback() # Garante que a sessão volte a um estado consistente
            print(f"Erro no banco de dados ao criar OS: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha no banco de dados ao criar a Ordem de Serviço."
            )

    # ----------------------------------------------------
    # Mapeamento READ All com Filtros
    # ----------------------------------------------------
    async def get_all_os(
        self, 
        db: AsyncSession,
        status: Optional[str] = None, 
        cliente: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """ 
        Busca todas as Ordens de Serviço, com tratamento de erro na execução da query.
        """
        try:
            query = select(OrdemServico)
            conditions = []
            
            if status:
                conditions.append(OrdemServico.status == status)
            if cliente:
                conditions.append(OrdemServico.cliente.ilike(f'%{cliente}%'))
                
            if conditions:
                query = query.where(and_(*conditions))

            result = await db.execute(query)
            os_list = result.scalars().all()
            
            return self._enrich_os_data(os_list)
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar todas as OSs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados."
            )

    # ----------------------------------------------------
    # Mapeamento READ by ID
    # ----------------------------------------------------
    async def get_os_by_id(self, db: AsyncSession, os_id: UUID) -> Optional[OrdemServico]:
        """ Busca uma única Ordem de Serviço pelo seu ID, com tratamento de erro. """
        try:
            query = select(OrdemServico).where(OrdemServico.id == os_id)
            result = await db.execute(query)
            return result.scalars().one_or_none()
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao buscar OS por ID: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados."
            )
        
    # ----------------------------------------------------
    # Mapeamento UPDATE
    # ----------------------------------------------------
    async def update_os(self, db: AsyncSession, os_id: UUID, os_data: Dict[str, Any]) -> OrdemServico:
        """ Busca a OS, atualiza seus atributos e persiste, com tratamento de erro. """
        os_existente = await self.get_os_by_id(db, os_id)
        
        if not os_existente:
            # Reutiliza o tratamento de 404 da rota (HTTPException)
            raise HTTPException(status_code=404, detail=f"Ordem de Serviço com ID '{os_id}' não encontrada.")
            
        try:
            for key, value in os_data.items():
                if key not in ['id', 'data_criacao'] and hasattr(os_existente, key):
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

    # ----------------------------------------------------
    # Mapeamento DELETE
    # ----------------------------------------------------
    async def delete_os(self, db: AsyncSession, os_id: UUID) -> bool:
        """ Remove um registro, com tratamento de erro. """
        os_existente = await self.get_os_by_id(db, os_id)
        
        if not os_existente:
            # Reutiliza o tratamento de 404 da rota
            raise HTTPException(status_code=404, detail=f"Ordem de Serviço com ID '{os_id}' não encontrada.")
            
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
    # Mapeamento de Análise (KPIs)
    # ----------------------------------------------------
    async def get_kpis(self, db: AsyncSession) -> Dict[str, Any]:
        """ Calcula os KPIs agregados, com tratamento de erro. """
        try:
            # ... (cálculos de total_os, atrasadas_count, media_prazo_dias) ...
            total_os = func.count(OrdemServico.id).label('total_os')
            atrasadas_count = func.sum(
                case(
                    (
                        and_(
                            OrdemServico.prazo_entrega < datetime.date.today(),
                            OrdemServico.status.notin_(['Concluída', 'Cancelada'])
                        ),
                        1
                    ),
                    else_=0
                )
            ).label('atrasadas_count')
            media_prazo_dias = func.avg(
                cast(OrdemServico.prazo_entrega - OrdemServico.data_entrada, Integer) 
            ).label('media_prazo_dias')

            query = select(total_os, atrasadas_count, media_prazo_dias)
            
            result = await db.execute(query)
            kpis_row = result.first() 

            # ... (formatação dos resultados) ...
            if kpis_row is None:
                return {"total_os": 0, "atrasadas_count": 0, "media_prazo_dias": None}

            kpis_dict = kpis_row._asdict()

            kpis = {
                "total_os": int(kpis_dict.get('total_os', 0) or 0),
                "atrasadas_count": int(kpis_dict.get('atrasadas_count', 0) or 0),
                "media_prazo_dias": round(float(kpis_dict.get('media_prazo_dias')), 2) 
                                      if kpis_dict.get('media_prazo_dias') is not None else None
            }
            
            return kpis
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao calcular KPIs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura e agregação de dados do banco de dados para KPIs."
            )
    
    # ----------------------------------------------------
    # Mapeamento de Análise - Distribuição de Status
    # ----------------------------------------------------
    async def get_status_distribution(self, db: AsyncSession) -> Dict[str, int]:
        """ Retorna a contagem de Ordens de Serviço agrupadas pelo status, com tratamento de erro. """
        try:
            query = select(
                OrdemServico.status,
                func.count(OrdemServico.id).label('count')
            ).group_by(OrdemServico.status)

            result = await db.execute(query)
            
            status_distribution = {
                row.status: row.count for row in result.all()
            }
            
            return status_distribution
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao obter distribuição de status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados para distribuição de status."
            )
    
    # ----------------------------------------------------
    # Mapeamento de Análise - Tendência Mensal
    # ----------------------------------------------------
    async def get_os_by_month(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """ Retorna a contagem de OSs por mês, com tratamento de erro. """
        try:
            month_label = func.strftime('%Y-%m', OrdemServico.data_entrada).label('mes')
            
            query = select(
                month_label,
                func.count(OrdemServico.id).label('count')
            ).group_by(month_label).order_by(month_label)

            result = await db.execute(query)
            
            os_by_month = [
                {"mes": row.mes, "count": row.count} 
                for row in result.all()
            ]
            
            return os_by_month
        except exc.SQLAlchemyError as e:
            print(f"Erro no banco de dados ao obter tendência mensal: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Falha na leitura de dados do banco de dados para tendência mensal."
            )