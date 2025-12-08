from sqlalchemy import Column, String, Date, DateTime, func, UUID, Index # <-- Index importado
from sqlalchemy.orm import relationship
import uuid
import datetime

# Importa a Base Declarativa do nosso setup de banco de dados
from database.db_setup import Base

class OrdemServico(Base):
    # Nome da tabela no banco de dados
    __tablename__ = "ordens_servico"

    # Campos obrigatórios e de controle
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Campo de negócio (indexado diretamente no Column)
    os_num = Column(String, unique=True, index=True, nullable=False)
    
    # Campos de descrição da Ordem de Serviço
    tipo = Column(String, nullable=False) 
    cliente = Column(String, nullable=False) # Coluna que precisa de index
    equipamento = Column(String, nullable=False)
    
    # Campos de Data
    data_entrada = Column(Date, default=datetime.date.today, nullable=False)
    prazo_entrega = Column(Date) # Coluna que precisa de index
    
    # Campos de Status
    status = Column(String, default="Pendente", nullable=False) # Coluna que precisa de index
    
    # Metadados de registro
    data_criacao = Column(DateTime, default=func.now())
    
    
    # ----------------------------------------------------
    # OTIMIZAÇÃO: Argumentos de Tabela para Indexação
    # ----------------------------------------------------
    __table_args__ = (
        # Índice para buscas por Cliente (usado no filtro ILIKE)
        Index('idx_cliente', cliente), 
        
        # Índice para filtros de Status
        Index('idx_status', status),
        
        # Índice para buscas ou ordenação por Prazo de Entrega
        Index('idx_prazo_entrega', prazo_entrega),
    )
    
    def __repr__(self):
        """Representação amigável do objeto para debug."""
        return f"<OrdemServico(OS={self.os_num}, Cliente='{self.cliente}', Status='{self.status}')>"