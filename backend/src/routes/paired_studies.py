from fastapi import APIRouter,Depends
from src.config.database import session
from src.middlewares.auth import require
from src.constants.enums import Role
from src.schemas.paired import PairedStudyContent
from src.controllers.paired_study_controller import listing,replace_content,snapshot
router=APIRouter(prefix='/paired-studies')
@router.get('')
def index(db=Depends(session),u=Depends(require(Role.ADMIN,Role.ANALYST,Role.VIEWER))):return listing(db)
@router.get('/{id}/snapshot')
def detail(id:int,db=Depends(session),u=Depends(require(Role.ADMIN,Role.ANALYST,Role.VIEWER))):return snapshot(db,id)
@router.put('',status_code=200)
def replace(data:PairedStudyContent,db=Depends(session),u=Depends(require(Role.ADMIN,Role.ANALYST))):return replace_content(db,data,u)
