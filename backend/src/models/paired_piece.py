from sqlalchemy import String,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from src.config.database import Base
class PairedPiece(Base):
 __tablename__='paired_pieces'
 __table_args__=(UniqueConstraint('study_id','code'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('paired_studies.id'))
 code:Mapped[str]=mapped_column(String(40))
 source:Mapped[str]=mapped_column(String(160),default='')
