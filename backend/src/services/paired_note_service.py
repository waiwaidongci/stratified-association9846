from sqlalchemy import select
from fastapi import HTTPException
from src.models import PairedVerificationNote,PairedRun
from src.constants.enums import NoteStatus
from src.utils.audit import record
from src.utils.serializers import serialize
from .paired_export_builder import build_paired_export_csv

def listing(db):return [serialize(x) for x in db.scalars(select(PairedVerificationNote).order_by(PairedVerificationNote.id.desc()))]
def create(db,data,user):
 run=db.get(PairedRun,data.run_id)
 if not run:raise HTTPException(404,'配对研究不存在')
 if run.status!='completed':raise HTTPException(409,'仅已完成配对研究可形成复验说明')
 if db.scalar(select(PairedVerificationNote).where(PairedVerificationNote.title==data.title)):raise HTTPException(409,'说明名称重复')
 note=PairedVerificationNote(**data.model_dump(),created_by=user.id);db.add(note);db.flush()
 record(db,user,'paired_note.created',note.id);db.commit();return serialize(note)
def review(db,id,data,user):
 note=db.get(PairedVerificationNote,id)
 if not note:raise HTTPException(404,'复验说明不存在')
 if note.status!=NoteStatus.DRAFT:raise HTTPException(409,'复验说明已审阅')
 note.status=NoteStatus(data.decision);note.review_comment=data.comment;note.approved_by=user.email
 record(db,user,'paired_note.'+data.decision,id);db.commit();return serialize(note)
def export(db,id,user):
 note=db.get(PairedVerificationNote,id)
 if not note:raise HTTPException(404,'复验说明不存在')
 if note.status!=NoteStatus.APPROVED:raise HTTPException(403,'仅已批准说明可导出')
 run=db.get(PairedRun,note.run_id)
 csv_text=build_paired_export_csv(serialize(note),run.result)
 record(db,user,'paired_note.exported',id);db.commit();return csv_text
