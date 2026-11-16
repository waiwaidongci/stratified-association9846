from sqlalchemy import String,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from src.config.database import Base
class PairedLayer(Base):
 __tablename__='paired_layers'
 __table_args__=(UniqueConstraint('study_id','code'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('paired_studies.id'))
 code:Mapped[str]=mapped_column(String(40))
 name:Mapped[str]=mapped_column(String(120))
 sequence:Mapped[int]=mapped_column()
 description:Mapped[str]=mapped_column(String(1200),default='')
