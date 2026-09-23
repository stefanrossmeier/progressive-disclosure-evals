#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, subprocess, time
from pathlib import Path
from typing import Any
from _common import markdown_document_id, serve
ROOT=Path(__file__).resolve().parents[1]; TOOL=ROOT/'.tools'/'agent-memory'; MEM=TOOL/'.venv'/'bin'/'mem'
class W:
    def __init__(self): self.runtime=None
    def env(self,corpus):
        e=os.environ.copy(); e['AGENT_MEMORY_STORE']=str(Path(self.runtime)/'stores'/corpus); e['NO_COLOR']='1'; return e
    def cli(self,corpus,*a,check=True):
        r=subprocess.run([str(MEM),*a],env=self.env(corpus),text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if check and r.returncode: raise RuntimeError(f"mem failed: {' '.join(a)}\n{r.stdout[-4000:]}\n{r.stderr[-4000:]}")
        return r
    def ver(self):
        p=ROOT/'.tools'/'agent-memory.sha'; return p.read_text().strip() if p.exists() else 'unknown-sha'
    def hello(self,q): self.runtime=q['runtime_root']; return {'backend':'agent-memory','provider_version':self.ver(),'cli':str(MEM)}
    def ingest(self,q):
        self.runtime=q['runtime_root']; c=q['corpus']; mem=Path(q['memory_root']); store=Path(self.runtime)/'stores'/c
        if store.exists(): import shutil; shutil.rmtree(store)
        self.cli(c,'init'); start=time.perf_counter(); n=0
        for p in sorted(mem.rglob('*.md')):
            rel=p.relative_to(mem).as_posix(); body=p.read_text(encoding='utf-8'); doc=markdown_document_id(p,body)
            abstract=f"Document-ID: {doc}; Source-Path: {rel}"
            self.cli(c,'record','--type','decision','--field',f'project={c}','--abstract',abstract,'--body',body)
            n+=1
        self.cli(c,'rebuild')
        return {'backend':'agent-memory','provider_version':self.ver(),'documents':n,'elapsed_ms':(time.perf_counter()-start)*1000,'metadata':{'mode':'native record + BM25 rebuild','source_of_truth':'agent-memory markdown store'}}
    def query(self,q):
        self.runtime=q['runtime_root']; c=q['corpus']; lim=int(q['limit']); start=time.perf_counter(); r=self.cli(c,'--json','recall',q['query'],'--limit',str(lim)); data=json.loads(r.stdout)
        hits=data if isinstance(data,list) else data.get('hits') or data.get('results') or data.get('items') or data.get('memories') or [data]
        normalized=[]
        for raw in hits[:lim]:
            hit=dict(raw) if isinstance(raw,dict) else {'value':raw}
            abstract=hit.get('abstract')
            if isinstance(abstract,str):
                match=re.search(r'(?i)\bDocument-ID:\s*([^;\n]+)',abstract)
                if match:
                    hit['document_id']=match.group(1).strip()
            normalized.append(hit)
        return {'backend':'agent-memory','provider_version':self.ver(),'requested_limit':lim,'elapsed_ms':(time.perf_counter()-start)*1000,'retrieval_llm_calls':0,'hits':normalized,'metadata':{'mode':'native_bm25_recall'}}
    def handle(self,q):
        if q['op']=='close': return {'closed':True}
        return {'hello':self.hello,'ingest':self.ingest,'query':self.query}[q['op']](q)
if __name__=='__main__': serve(W().handle)
