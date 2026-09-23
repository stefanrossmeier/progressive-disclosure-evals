#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, importlib.metadata, json, os, shutil, socket, sqlite3, subprocess, time, urllib.error, urllib.request
from pathlib import Path
from typing import Any
from _common import environment_executable, markdown_document_id, serve

class EverOSWorker:
    def __init__(self):
        self.runtime_root: Path | None = None
        self.provider_version = importlib.metadata.version('everos')
        self.process: subprocess.Popen[str] | None = None
        self.port: int | None = None
        self.env: dict[str,str] | None = None
    def _configure(self, runtime_root: str) -> None:
        self.runtime_root=Path(runtime_root).resolve(); self.runtime_root.mkdir(parents=True,exist_ok=True)
        e=os.environ.copy(); e['NO_COLOR']='1'; e['PYTHONUNBUFFERED']='1'
        # EverOS 1.3.x requires [llm] configuration even for keyword-only
        # retrieval. Reuse the benchmark's existing OpenAI-compatible config
        # when the user has not supplied explicit EVEROS_LLM__* overrides.
        if not e.get('EVEROS_LLM__API_KEY') and e.get('OPENAI_API_KEY'):
            e['EVEROS_LLM__API_KEY']=e['OPENAI_API_KEY']
        if not e.get('EVEROS_LLM__MODEL') and e.get('OPENAI_MODEL'):
            e['EVEROS_LLM__MODEL']=e['OPENAI_MODEL']
        if not e.get('EVEROS_LLM__BASE_URL') and e.get('OPENAI_API_KEY'):
            e['EVEROS_LLM__BASE_URL']='https://api.openai.com/v1'
        self.env=e
    def _cli(self,*args:str,root:Path|None=None,check:bool=True):
        exe=environment_executable('everos'); cmd=[str(exe),*args] if exe else [os.sys.executable,'-m','everos',*args]
        env=dict(self.env or os.environ)
        if root is not None:
            env['EVEROS_ROOT']=str(root); cmd += ['--root',str(root)]
        r=subprocess.run(cmd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if check and r.returncode:
            raise RuntimeError(f"EverOS CLI failed: {' '.join(cmd)}\nstdout:\n{r.stdout[-6000:]}\nstderr:\n{r.stderr[-6000:]}")
        return r
    @staticmethod
    def _port()->int:
        s=socket.socket(); s.bind(('127.0.0.1',0)); p=s.getsockname()[1]; s.close(); return p
    def _store(self,corpus:str)->Path:
        assert self.runtime_root is not None
        return self.runtime_root/'stores'/corpus
    def _write_episode_logs(self, corpus:str, memory_root:Path) -> list[Path]:
        """Write one deterministic EverOS episode file per source document.

        A corpus import is not a real chat day. Keeping every source document in
        its own daily-log file gives cascade an ordinary one-entry unit to diff
        and index, rather than one oversized synthetic file containing 40/80
        unrelated entries.
        """
        store=self._store(corpus); owner='memory_eval'; docs=sorted(memory_root.rglob('*.md'))
        base=dt.date(2026,1,1)
        for i,p in enumerate(docs,1):
            day=base+dt.timedelta(days=i-1)
            day_text=day.isoformat(); eid=f'ep_{day.strftime("%Y%m%d")}_00000001'
            path=store/'default_app'/'default_project'/'users'/owner/'episodes'/f'episode-{day_text}.md'
            path.parent.mkdir(parents=True,exist_ok=True)
            rel=p.relative_to(memory_root).as_posix(); body=p.read_text(encoding='utf-8'); doc=markdown_document_id(p,body)
            lines=[
                '---',f'id: episode_log_{owner}_{day_text}','type: episode_daily','file_type: episode_daily','schema_version: 1',
                f'user_id: {owner}','track: user',f"date: '{day_text}'",'entry_count: 1',
                f"last_appended_at: '{day_text}T00:00:00+00:00'",'---',
                f'<!-- entry:{eid} -->',f'## {eid}',f'**session_id**: markdown-eval-{corpus}-{i:04d}',
                f'**timestamp**: {day_text}T00:00:00+00:00','**sender_ids**: [memory_eval]','**parent_type**: import',
                f'**parent_id**: {doc}','**type**: Conversation','### Subject',doc,'### Summary',
                f'Document-ID: {doc}; Source-Path: {rel}','### Episode',body,f'<!-- /entry:{eid} -->',
            ]
            path.write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
        return [
            store/'default_app'/'default_project'/'users'/owner/'episodes'/f'episode-{(base+dt.timedelta(days=i-1)).isoformat()}.md'
            for i in range(1, len(docs)+1)
        ]
    @staticmethod
    def _cascade_state(store:Path) -> dict[str,Any]:
        db=store/'.index'/'sqlite'/'system.db'
        if not db.exists(): return {'database':str(db),'exists':False}
        try:
            with sqlite3.connect(db) as conn:
                counts={str(status):int(count) for status,count in conn.execute('SELECT status, COUNT(*) FROM md_change_state GROUP BY status')}
                failed=[]
                if counts.get('failed',0):
                    for row in conn.execute("SELECT md_path, error, retryable FROM md_change_state WHERE status='failed' ORDER BY md_path LIMIT 10"):
                        failed.append({'md_path':row[0],'error':row[1],'retryable':bool(row[2])})
            return {'database':str(db),'exists':True,'counts':counts,'failed':failed}
        except sqlite3.Error as exc:
            return {'database':str(db),'exists':True,'error':f'{type(exc).__name__}: {exc}'}
    def _stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.kill()
        self.process=None
    def _start(self,corpus:str):
        self._stop(); store=self._store(corpus); self.port=self._port(); exe=environment_executable('everos')
        cmd=[str(exe),'server','start','--host','127.0.0.1','--port',str(self.port),'--root',str(store)] if exe else [os.sys.executable,'-m','everos','server','start','--host','127.0.0.1','--port',str(self.port),'--root',str(store)]
        env=dict(self.env or os.environ); env['EVEROS_ROOT']=str(store)
        assert self.runtime_root is not None; log_path=self.runtime_root/f'everos-{corpus}-server.log'
        log=log_path.open('a',encoding='utf-8'); self.process=subprocess.Popen(cmd,env=env,text=True,stdout=log,stderr=subprocess.STDOUT); log.close()
        last_error=''
        for _ in range(300):
            if self.process.poll() is not None:
                tail=log_path.read_text(encoding='utf-8',errors='replace')[-8000:]
                raise RuntimeError(f'EverOS server exited during startup with code {self.process.returncode}\ncommand: {" ".join(cmd)}\nserver log:\n{tail}')
            try:
                payload=json.loads(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/health',timeout=.5).read())
                if isinstance(payload,dict) and payload.get('status')=='ok': return
                last_error=f'unexpected health response: {payload!r}'
            except Exception as exc: last_error=f'{type(exc).__name__}: {exc}'
            time.sleep(.1)
        tail=log_path.read_text(encoding='utf-8',errors='replace')[-8000:]; self._stop()
        raise RuntimeError(f'EverOS server did not become healthy: {last_error}\ncommand: {" ".join(cmd)}\nserver log:\n{tail}')
    def hello(self,q):
        self._configure(q['runtime_root']); return {'backend':'everos','provider_version':self.provider_version,'python':os.sys.version.split()[0]}
    def ingest(self,q):
        self._configure(q['runtime_root']); corpus=str(q['corpus']); mem=Path(q['memory_root']).resolve(); store=self._store(corpus)
        if store.exists(): shutil.rmtree(store)
        store.mkdir(parents=True); self._cli('init',root=store)
        start=time.perf_counter(); episode_paths=self._write_episode_logs(corpus,mem); n=len(episode_paths)

        # Avoid the bulk-rebuild path here.  EverOS has had macOS/LanceDB
        # failure modes where a large rebuild leaves Markdown durable but only
        # partially projected into BM25/LanceDB.  The CLI supports an explicit
        # single-file sync path, which is deterministic for this benchmark and
        # keeps every source document independently attributable.
        for index,path in enumerate(episode_paths,1):
            sync=self._cli('cascade','sync',str(path),root=store,check=False)
            if sync.returncode != 0:
                state=self._cascade_state(store)
                raise RuntimeError(
                    f'EverOS cascade sync failed for {path.name} ({index}/{n})\n'
                    f'stdout:\n{sync.stdout[-6000:]}\nstderr:\n{sync.stderr[-6000:]}\n'
                    f'cascade_state={json.dumps(state,ensure_ascii=False)}'
                )

        status=self._cli('cascade','status',root=store,check=False)
        state=self._cascade_state(store)
        counts=state.get('counts',{}) if isinstance(state,dict) else {}
        if isinstance(counts,dict):
            failed=int(counts.get('failed',0) or 0)
            done=int(counts.get('done',0) or 0)
            if failed or done < n:
                raise RuntimeError(
                    'EverOS import verification failed after per-file cascade sync: '
                    f'expected at least {n} done rows and zero failed rows; state='
                    f'{json.dumps(state,ensure_ascii=False)}\n'
                    f'cascade status stdout:\n{status.stdout[-6000:]}\n'
                    f'cascade status stderr:\n{status.stderr[-6000:]}'
                )
        return {
            'backend':'everos','provider_version':self.provider_version,'documents':n,
            'elapsed_ms':(time.perf_counter()-start)*1000,
            'metadata':{
                'mode':'one-source-document-per-episode-file + per-file cascade sync',
                'search_method':'keyword','source_of_truth':'EverOS markdown',
                'cascade_state':state,
                'cascade_status':(status.stdout+status.stderr)[-4000:],
            },
        }
    def query(self,q):
        self._configure(q['runtime_root']); corpus=str(q['corpus']); lim=int(q['limit']); self._start(corpus); started=time.perf_counter()
        payload=json.dumps({'user_id':'memory_eval','app_id':'default','project_id':'default','query':str(q['query']),'method':'keyword','top_k':lim}).encode()
        req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/v2/memory/search',data=payload,headers={'Content-Type':'application/json'})
        try: data=json.loads(urllib.request.urlopen(req,timeout=60).read())
        finally: self._stop()
        hits=data.get('data',{}).get('episodes',[])[:lim]
        return {'backend':'everos','provider_version':self.provider_version,'requested_limit':lim,'elapsed_ms':(time.perf_counter()-started)*1000,'retrieval_llm_calls':0,'hits':hits,'metadata':{'mode':'keyword_bm25','owner':'memory_eval'}}
    def handle(self,q):
        if q['op']=='close': self._stop(); return {'closed':True}
        return {'hello':self.hello,'ingest':self.ingest,'query':self.query}[q['op']](q)
if __name__=='__main__': serve(EverOSWorker().handle)
