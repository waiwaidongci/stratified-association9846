from sqlalchemy import String,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from src.config.database import Base
class PairedCell(Base):
 """逐片×逐层×两种封装的成败冻结明细（0/1），保留片内跨层关联的最小单元。"""
 __tablename__='paired_cells'
 __table_args__=(UniqueConstraint('piece_id','layer_id'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 piece_id:Mapped[int]=mapped_column(ForeignKey('paired_pieces.id'))
 layer_id:Mapped[int]=mapped_column(ForeignKey('paired_layers.id'))
 a_success:Mapped[int]=mapped_column()
 a_failure:Mapped[int]=mapped_column()
 b_success:Mapped[int]=mapped_column()
 b_failure:Mapped[int]=mapped_column()
