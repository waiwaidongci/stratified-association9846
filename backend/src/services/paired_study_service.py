from sqlalchemy import select
from fastapi import HTTPException
from src.models import (PairedStudy,PairedLayer,PairedPiece,PairedCell,PairedRun)
from src.utils.serializers import serialize
from src.utils.audit import record

def listing(db):
 return [serialize(x) for x in db.scalars(select(PairedStudy).order_by(PairedStudy.id))]

def _load_cells(db,study_id):
 layers=db.scalars(select(PairedLayer).where(PairedLayer.study_id==study_id).order_by(PairedLayer.sequence,PairedLayer.code)).all()
 pieces=db.scalars(select(PairedPiece).where(PairedPiece.study_id==study_id).order_by(PairedPiece.id)).all()
 cell_rows=db.scalars(select(PairedCell).join(PairedPiece,PairedPiece.id==PairedCell.piece_id).where(PairedPiece.study_id==study_id)).all()
 index={(c.piece_id,c.layer_id):c for c in cell_rows}
 out_pieces=[]
 for p in pieces:
  cells=[]
  for ly in layers:
   c=index.get((p.id,ly.id))
   if not c:raise HTTPException(500,'配对底稿缺少逐片逐层明细，数据不完整')
   cells.append({'layer_code':ly.code,**{k:getattr(c,k) for k in ['a_success','a_failure','b_success','b_failure']}})
  out_pieces.append({'code':p.code,'source':p.source,'cells':cells})
 return layers,out_pieces

def snapshot(db,study_id):
 study=db.get(PairedStudy,study_id)
 if not study:raise HTTPException(404,'配对研究不存在')
 layers,pieces=_load_cells(db,study_id)
 if not 2<=len(layers)<=8:raise HTTPException(422,'需要2..8个湿度层')
 if not 1<=len(pieces)<=60:raise HTTPException(422,'需要1..60片试片')
 return {'study':serialize(study),
         'layers':[{'code':l.code,'name':l.name,'sequence':l.sequence,'description':l.description} for l in layers],
         'pieces':pieces}

def replace_content(db,data,user):
 study=db.scalar(select(PairedStudy).where(PairedStudy.code==data.study.code))
 if study is None:
  study=PairedStudy(**data.study.model_dump());db.add(study);db.flush()
  action='paired_study.created'
 else:
  if db.scalar(select(PairedRun).where(PairedRun.study_id==study.id)):
   raise HTTPException(409,'该配对研究已有冻结计算，逐片明细不可改写；请另建研究编号')
  # 清掉旧明细后整体重写，保证“逐片明细冻结前可修订、冻结后不可变”。
  old_layers=db.scalars(select(PairedLayer).where(PairedLayer.study_id==study.id)).all()
  old_pieces=db.scalars(select(PairedPiece).where(PairedPiece.study_id==study.id)).all()
  old_cells=db.scalars(select(PairedCell).join(PairedPiece,PairedPiece.id==PairedCell.piece_id).where(PairedPiece.study_id==study.id)).all()
  for c in old_cells:db.delete(c)
  for p in old_pieces:db.delete(p)
  for ly in old_layers:db.delete(ly)
  db.flush()  # 先落库删除，避免同唯一键的新增在同一事务内冲突
  for k,v in data.study.model_dump().items():setattr(study,k,v)
  action='paired_study.revised'
 layer_map={}
 for ly in data.layers:
  row=PairedLayer(study_id=study.id,**ly.model_dump());db.add(row);db.flush();layer_map[ly.code]=row.id
 for piece in data.pieces:
  prow=PairedPiece(study_id=study.id,code=piece.code,source=piece.source);db.add(prow);db.flush()
  ordered={c.layer_code:c for c in piece.cells}
  for ly in data.layers:
   cell=ordered[ly.code]
   db.add(PairedCell(piece_id=prow.id,layer_id=layer_map[ly.code],
                     a_success=cell.a_success,a_failure=cell.a_failure,
                     b_success=cell.b_success,b_failure=cell.b_failure))
 db.flush();record(db,user,action,study.id);db.commit()
 return snapshot(db,study.id)
