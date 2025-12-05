from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, func
from sqlalchemy.dialects.sqlite import UUID as SQLiteUUID
from sqlalchemy.orm import relationship
import uuid
import datetime

# Importa a Base Declarativa do nosso setup de banco de dados
from database.db_setup import Base

class OrdemServico(Base):
    # Nome da tabela no banco de dados
    __tablename__ = "ordens_servico"

    # Campos obrigatórios e de controle
    # ID: Chave primária, gerada automaticamente pelo banco (UUID é recomendado para sistemas distribuídos)
    # Usamos SQLiteUUID para compatibilidade com SQLAlchemy e SQLite
    id = Column(SQLiteUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Campo de negócio
    os_num = Column(String, unique=True, index=True, nullable=False)
    
    # Campos de descrição da Ordem de Serviço
    tipo = Column(String, nullable=False)        # Ex: "Manutenção Corretiva", "Instalação"
    cliente = Column(String, nullable=False)     # Nome do cliente
    equipamento = Column(String, nullable=False) # Nome ou descrição do equipamento
    
    # Campos de Data
    data_entrada = Column(Date, default=datetime.date.today, nullable=False) # Data em que a OS foi aberta
    prazo_entrega = Column(Date) # Prazo acordado para conclusão
    
    # Campos de Status
    # Status: Ex: "Pendente", "Em Andamento", "Concluída", "Cancelada"
    status = Column(String, default="Pendente", nullable=False) 
    
    # Metadados de registro
    # Garante que o registro da OS seja mantido com timestamp
    data_criacao = Column(DateTime, default=func.now())
    
    
    def __repr__(self):
        """Representação amigável do objeto para debug."""
        return f"<OrdemServico(OS={self.os_num}, Cliente='{self.cliente}', Status='{self.status}')>"