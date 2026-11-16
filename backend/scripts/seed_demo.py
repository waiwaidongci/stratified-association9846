from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import (User,AssociationStudy,ExposureStratum,TableCount,AssociationRun,VerificationNote,
 PairedStudy,PairedLayer,PairedPiece,PairedCell,PairedRun,PairedVerificationNote)
from src.utils.security import hash_password
from src.services.run_service import snapshot
from src.services.analysis_algorithm import analyze
from src.services.paired_analysis_algorithm import analyze_paired

LAYER_DEFS=[('H%d'%(i+1),'湿度层%d'%(i+1),i) for i in range(8)]

def _cell(delta):
 # delta = a_success - b_success ∈ {-1,0,1}
 if delta==1:return dict(a_success=1,a_failure=0,b_success=0,b_failure=1)
 if delta==-1:return dict(a_success=0,a_failure=1,b_success=1,b_failure=0)
 return dict(a_success=1,a_failure=0,b_success=1,b_failure=0)

def seed_paired_study(db,code,name,deltas_by_piece,description):
 study=db.scalar(select(PairedStudy).where(PairedStudy.code==code))
 if study:return study
 study=PairedStudy(code=code,name=name,period='2026-11 配对复测试验',description=description)
 db.add(study);db.flush()
 layer_ids={}
 for lc,ln,seq in LAYER_DEFS:
  row=PairedLayer(study_id=study.id,code=lc,name=ln,sequence=seq,description='同一试片预先声明的复测湿度层；封装标签按整片共同交换。')
  db.add(row);db.flush();layer_ids[lc]=row.id
 for idx,deltas in enumerate(deltas_by_piece):
  prow=PairedPiece(study_id=study.id,code='P%02d'%(idx+1),source='CN_20261113_配对复测逐片明细.csv')
  db.add(prow);db.flush()
  for j,(lc,_,_) in enumerate(LAYER_DEFS):
   cell=_cell(deltas[j])
   db.add(PairedCell(piece_id=prow.id,layer_id=layer_ids[lc],**cell))
 return study

def seed_paired(db,user):
 # 样例一：六十片八层同向（每片每层 A 均优于 B）。
 same=[[1]*8 for _ in range(60)]
 study_same=seed_paired_study(db,'CN-PAIR-SAME','同片多层复测 · 封装同向差异',same,
  '六十片试片各在八个湿度层复测，逐片记录两种封装成败；所有层 A 均优于 B，用于核对整片交换精确双侧。')
 # 样例二：六十片八层正反相抵（30 片全 +1、30 片全 -1，观察每层率差为 0）。
 cancel=[[1]*8 for _ in range(30)]+[[-1]*8 for _ in range(30)]
 seed_paired_study(db,'CN-PAIR-CANCEL','同片多层复测 · 正反相抵',cancel,
  '六十片试片各在八个湿度层复测，正反片型各半，各层观察配对率差为 0；精确双侧应得到 p=1，全部配置入尾。')
 db.commit()
 run=db.scalar(select(PairedRun).where(PairedRun.name=='配对复测 · 同向六十片八层'))
 if not run:
  snap=_paired_snapshot(db,study_same.id)
  run=PairedRun(name='配对复测 · 同向六十片八层',study_id=study_same.id,alpha=.05,created_by=user.id,
   input_snapshot=snap,result=analyze_paired(snap,.05),status='completed')
  db.add(run);db.flush()
 if not db.scalar(select(PairedVerificationNote).where(PairedVerificationNote.title=='同片多湿层，关联不拆层')):
  db.add(PairedVerificationNote(title='同片多湿层，关联不拆层',run_id=run.id,
   interpretation='整片在八个湿度层共同交换封装标签，精确双侧保留片内跨层关联与等距并列；同向样例仅全同向两个配置入尾。',
   action='维持同片多湿度层配对复测设计，逐格冻结两种封装成败，并按预先方案独立复验。',
   status='approved',approved_by='admin@cenan.demo',
   review_comment='尾部/内部/总组合数恒等与逐片明细已核对，批准独立复验记录。',created_by=user.id))
 db.commit()

def _paired_snapshot(db,study_id):
 study=db.get(PairedStudy,study_id)
 layers=db.scalars(select(PairedLayer).where(PairedLayer.study_id==study_id).order_by(PairedLayer.sequence)).all()
 pieces=db.scalars(select(PairedPiece).where(PairedPiece.study_id==study_id).order_by(PairedPiece.id)).all()
 cells=db.scalars(select(PairedCell).join(PairedPiece,PairedPiece.id==PairedCell.piece_id).where(PairedPiece.study_id==study_id)).all()
 index={(c.piece_id,c.layer_id):c for c in cells}
 out=[]
 for p in pieces:
  out.append({'code':p.code,'source':p.source,'cells':[
   {'layer_code':l.code,**{k:getattr(index[(p.id,l.id)],k) for k in ['a_success','a_failure','b_success','b_failure']}} for l in layers]})
 return {'study':{'id':study.id,'code':study.code,'name':study.name,'period':study.period,'description':study.description},
  'layers':[{'code':l.code,'name':l.name,'sequence':l.sequence,'description':l.description} for l in layers],'pieces':out}

def seed():
 Base.metadata.create_all(engine)
 with SessionLocal() as db:
  for role,name in [('admin','岑禾'),('analyst','岸栩'),('viewer','林澄')]:
   email=role+'@cenan.demo'
   if not db.scalar(select(User).where(User.email==email)):db.add(User(email=email,name=name,role=role,password_hash=hash_password('Cenan2026!')))
  db.flush()
  fixtures=[('CN-REV','湿度构成不同 · 总体率反转',[(18,2,80,20),(20,80,2,18)]),('CN-SPARSE','稀疏层 · 条件分布对照',[(4,1,1,4),(1,4,4,1),(0,6,2,4),(3,3,3,3)]),('CN-NULL','同率与无信息层',[(5,5,10,10),(12,12,8,8),(0,0,6,4)])]
  for code,name,tables in fixtures:
   study=db.scalar(select(AssociationStudy).where(AssociationStudy.code==code))
   if not study:study=AssociationStudy(code=code,name=name,period='2026-11 封装浸湿试验',description='匿名独立封装试片；a/b为A成功/失败，c/d为B成功/失败。湿度层在试验前声明，不依据结果切层。');db.add(study);db.flush()
   for i,values in enumerate(tables):
    sid=code+'-'+str(i+1);s=db.scalar(select(ExposureStratum).where(ExposureStratum.study_id==study.id,ExposureStratum.code==sid))
    if not s:s=ExposureStratum(study_id=study.id,code=sid,name=['低湿度层','高湿度层','边界层','复核层'][i],description='预先分层，独立试片；未声称随机分配封装。');db.add(s);db.flush()
    if not db.scalar(select(TableCount).where(TableCount.stratum_id==s.id)):db.add(TableCount(stratum_id=s.id,**dict(zip(['a','b','c','d'],values)),source='CN_20261112_封装分层计数.csv'))
  db.commit();user=db.scalar(select(User).where(User.role=='analyst'));study=db.scalar(select(AssociationStudy).where(AssociationStudy.code=='CN-REV'))
  run=db.scalar(select(AssociationRun).where(AssociationRun.name=='湿度构成 · 首轮分层核对'))
  if not run:
   snap=snapshot(db,study.id);run=AssociationRun(name='湿度构成 · 首轮分层核对',study_id=study.id,alpha=.05,created_by=user.id,input_snapshot=snap,result=analyze(snap,.05),status='completed');db.add(run);db.flush()
  if not db.scalar(select(VerificationNote).where(VerificationNote.title=='先分层，再讨论总体率')):db.add(VerificationNote(title='先分层，再讨论总体率',run_id=run.id,interpretation='两层内A成功率均较高，但样本湿度构成不同导致总体率方向相反。共同OR是分层加权摘要，不是封装因果效果。',action='保留各湿度层独立重复试片，按预先方案核对封装和浸湿时间。',status='approved',approved_by='admin@cenan.demo',review_comment='统计层边际与精确双侧定义已核对，批准独立复验记录。',created_by=user.id))
  db.commit();print({t.__tablename__:db.scalar(select(func.count()).select_from(t)) for t in [User,AssociationStudy,ExposureStratum,TableCount,AssociationRun,VerificationNote]})
  seed_paired(db,user)
  print({t.__tablename__:db.scalar(select(func.count()).select_from(t)) for t in [PairedStudy,PairedLayer,PairedPiece,PairedCell,PairedRun,PairedVerificationNote]})
if __name__=='__main__':seed()
