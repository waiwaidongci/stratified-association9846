from sqlalchemy import select
from fastapi import HTTPException
from src.models import PairedRun
from src.config.queue import queue
from src.utils.audit import record
from src.utils.serializers import serialize
from .paired_study_service import snapshot
from .paired_analysis_algorithm import analyze_paired
QUEUE='cenan:paired-runs'
def listing(db):
 rows=[]
 for x in db.scalars(select(PairedRun).order_by(PairedRun.id.desc())):
  r=serialize(x);r.pop('result');r.pop('input_snapshot');rows.append(r)
 return rows
def create(db,data,user):
 if db.scalar(select(PairedRun).where(PairedRun.name==data.name)):raise HTTPException(409,'配对研究名称重复')
 snap=snapshot(db,data.study_id)
 row=PairedRun(**data.model_dump(),created_by=user.id,input_snapshot=snap);db.add(row);db.flush()
 record(db,user,'paired_run.queued',row.id);db.commit();queue.rpush(QUEUE,str(row.id));return serialize(row)
def compute(db,id):
 row=db.get(PairedRun,id)
 if not row or row.status not in ['queued','running']:return
 row.status='running';db.commit()
 row.result=analyze_paired(row.input_snapshot,row.alpha);row.status='completed';row.error=''
 record(db,None,'paired_worker.completed',row.id);db.commit();return serialize(row)
