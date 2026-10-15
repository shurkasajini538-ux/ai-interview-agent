"""Owner-scoped asynchronous jobs with replayable progress events."""
import hashlib
import json
import threading
import time
from .runtime import Operation,Cancelled,operation_context
from .storage import identifier


class Jobs:
    def __init__(self, max_active=8, max_records=100):
        if not 1 <= max_active <= max_records:
            raise ValueError('任务容量配置无效。')
        self.jobs={}
        self.lock=threading.RLock()
        self.max_active=max_active
        self.max_records=max_records

    def create(self,owner,request_id,payload,callback):
        fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with self.lock:
            for job in self.jobs.values():
                if job['owner']==owner and job['request_id']==request_id:
                    if job['fingerprint']!=fingerprint:
                        raise ValueError('相同请求编号不能用于不同操作。')
                    return self.public(job)
            if sum(j['state'] in ('running','queued','cancelling') and j['owner']==owner for j in self.jobs.values())>=2:
                raise BlockingIOError('当前已有操作在处理中，请等待完成。')
            if sum(j['state'] in ('running','queued','cancelling') for j in self.jobs.values()) >= self.max_active:
                raise BlockingIOError('服务正在处理较多操作，请稍后重试。')
            if len(self.jobs)>=self.max_records:
                completed=sorted((j for j in self.jobs.values() if j['state'] in ('done','failed','cancelled')),key=lambda j:j['created'])
                for job in completed[:len(self.jobs)-self.max_records+1]:
                    self.jobs.pop(job['id'],None)
            job={'id':identifier(),'owner':owner,'request_id':request_id,'fingerprint':fingerprint,
                 'state':'queued','operation':Operation(),'result':None,'error':'','created':time.monotonic()}
            self.jobs[job['id']]=job
        def run():
            with operation_context(job['operation']):
                try:
                    with job['operation'].lock:
                        job['operation'].check()
                        job['state']='running'
                    job['operation'].emit('stage',label='正在准备本次操作')
                    result=callback()
                    with job['operation'].lock:
                        job['operation'].check()
                        job.update(state='done',result=result)
                        job['operation'].events.append({'sequence':len(job['operation'].events)+1,'kind':'done'})
                except Cancelled as e:
                    with job['operation'].lock:
                        job.update(state='cancelled',error=str(e))
                except (ValueError,KeyError,BlockingIOError) as e:
                    with job['operation'].lock:
                        job.update(state='failed',error=str(e).strip("'"))
                except Exception:
                    with job['operation'].lock:
                        job.update(state='failed',error='操作未完成，请重试。已保存记录仍然保留。')
        try:
            threading.Thread(target=run,daemon=True).start()
        except RuntimeError:
            with job['operation'].lock:
                job.update(state='failed',error='暂时无法启动操作，请稍后重试。')
        return self.public(job)

    def get(self,job_id,owner):
        with self.lock:
            job=self.jobs.get(job_id)
        if not job or job['owner']!=owner:
            raise KeyError('操作不存在或已过期。刷新后请查看练习记录。')
        return job

    @staticmethod
    def public(job):
        with job['operation'].lock:
            return {k:job[k] for k in ('id','state','result','error')} | {'events':list(job['operation'].events)}

    def cancel(self,job_id,owner):
        job=self.get(job_id,owner)
        with job['operation'].lock:
            if job['operation'].committed or job['state'] in ('done','failed','cancelled'):
                return self.public(job)|{'cancel_accepted':False}
            job['operation'].cancelled.set()
            job['state']='cancelling'
            return self.public(job)|{'cancel_accepted':True}
