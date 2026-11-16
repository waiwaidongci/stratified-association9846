import time,logging
from pathlib import Path
from src.config.database import SessionLocal
from src.config.queue import queue
from src.models import AssociationRun,PairedRun
from src.services.run_service import compute,QUEUE
from src.services.paired_run_service import compute as paired_compute,QUEUE as PAIRED_QUEUE
logging.basicConfig(level=logging.INFO)
MODELS={QUEUE:(AssociationRun,compute),PAIRED_QUEUE:(PairedRun,paired_compute)}

def pop_item():
    # 轮流短阻塞两个队列，旧四格任务与配对复测任务互不阻塞、互不改变结果。
    for name in (QUEUE,PAIRED_QUEUE):
        item=queue.blpop(name,timeout=2)
        if item:return item
    return None

def handle(item):
    name,payload=item;_,compute_fn=MODELS[name]
    with SessionLocal() as db:
        try:compute_fn(db,int(payload))
        except Exception as exc:
            db.rollback();run=db.get(MODELS[name][0],int(payload))
            if run:run.status='failed';run.error=str(exc)[:500];db.commit()
            logging.exception('%s research failed',name)

def main():
    while True:
        Path('/tmp/heartbeat').touch()
        try:
            item=pop_item()
            if not item:continue
            handle(item)
        except Exception:
            logging.exception('worker loop');time.sleep(2)

if __name__=='__main__':main()
