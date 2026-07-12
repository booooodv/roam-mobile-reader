#!/usr/bin/env python3
import json, os, re, subprocess, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CONFIG_PATH=Path(os.environ.get('ROAM_READER_CONFIG', ROOT/'config.json'))
CONFIG=json.loads(CONFIG_PATH.read_text(encoding='utf-8')) if CONFIG_PATH.exists() else {}
PORT=int(os.environ.get('PORT', CONFIG.get('port',8765)))
HOST=os.environ.get('HOST', CONFIG.get('host','127.0.0.1'))
GRAPH=os.environ.get('ROAM_GRAPH', CONFIG.get('graph',''))

def rpc_session():
 p=subprocess.Popen(['npx','-y','@roam-research/roam-mcp'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
 seq=0
 def rpc(method,params):
  nonlocal seq
  seq+=1; rid=seq
  p.stdin.write(json.dumps({'jsonrpc':'2.0','id':rid,'method':method,'params':params},ensure_ascii=False)+'\n');p.stdin.flush()
  while True:
   line=p.stdout.readline()
   if not line: raise RuntimeError('Roam MCP closed: '+p.stderr.read()[-1000:])
   try:o=json.loads(line)
   except:continue
   if o.get('id')==rid:
    if 'error'in o:raise RuntimeError(str(o['error']))
    return o.get('result')
 rpc('initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'course-reader','version':'1'}})
 p.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})+'\n');p.stdin.flush()
 def call(name,args): return rpc('tools/call',{'name':name,'arguments':args})
 if not GRAPH: raise RuntimeError('Set graph in config.json or ROAM_GRAPH')
 call('get_graph_guidelines',{'graph':GRAPH})
 return p,call

def text_result(r):
 try:return json.loads(r['content'][0]['text'])
 except:return r

def sync(items):
 p,call=rpc_session(); results=[]
 try:
  page_cache={}
  for item in items:
   title=item.get('title',''); quote=' '.join(item.get('text','').split())
   if not title or len(quote)<2: results.append({'id':item.get('id'),'ok':False,'error':'划线内容为空'});continue
   # Read the exact lesson page and parse block UIDs directly. Full-text search
   # tokenizes punctuation/CJK and was unreliable for whole-block matching.
   if title not in page_cache:
    page_cache[title]=text_result(call('get_page',{'title':title,'maxDepth':20,'graph':GRAPH}))
   page=page_cache[title]; md=page.get('markdown','') if isinstance(page,dict) else json.dumps(page,ensure_ascii=False)
   candidates=[]
   def canon(v):
    v=re.sub(r'<[^>]+>','',v)
    v=re.sub(r'\[\[([^\]]+)\]\]',r'\1',v)
    v=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',v)
    v=re.sub(r'(`+|\*\*|__|~~|\^\^)','',v)
    v=v.replace('&amp;','&').replace('&lt;','<').replace('&gt;','>').replace('&quot;','"').replace('&#39;',"'")
    return ' '.join(v.split()).strip()
   for line in md.splitlines():
    m=re.search(r'<roam uid="([^"]+)"',line)
    if not m: continue
    uid=m.group(1)
    s=re.sub(r'\s*<roam\b[^>]*?/?>\s*$','',line).strip()
    s=re.sub(r'^\s*(?:[-*+]\s+)?(?:#{1,6}\s+)?','',s).strip()
    normalized=canon(s)
    if normalized==canon(quote): candidates.append((uid,s))
   # exact unique block only
   candidates=list({x[0]:x for x in candidates}.values())
   if len(candidates)!=1:
    results.append({'id':item.get('id'),'ok':False,'error':f'未能在页面中唯一定位整块（匹配 {len(candidates)} 个）'});continue
   uid,s=candidates[0]
   if s==f'^^{quote}^^': results.append({'id':item.get('id'),'ok':True,'already':True});continue
   ns='^^'+s+'^^'
   call('update_block',{'uid':uid,'string':ns,'graph':GRAPH})
   chk=text_result(call('get_block',{'uid':uid,'maxDepth':0,'graph':GRAPH}))
   chk_blob=json.dumps(chk,ensure_ascii=False)
   # MCP wraps returned strings with metadata; verify semantic text + highlight markers.
   ok=('^^' in chk_blob and canon(quote) in canon(chk_blob))
   results.append({'id':item.get('id'),'ok':ok,'uid':uid,'error':None if ok else '写入后回读未通过'})
 finally:p.terminate()
 return results

class H(SimpleHTTPRequestHandler):
 def end_headers(self):
  self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
  self.send_header('Pragma','no-cache')
  self.send_header('Expires','0')
  super().end_headers()
 def do_POST(self):
  if self.path!='/api/sync': self.send_error(404);return
  try:
   n=int(self.headers.get('Content-Length','0')); payload=json.loads(self.rfile.read(n)); items=payload.get('highlights',[])
   if len(items)>100: raise ValueError('单次最多100条')
   out={'results':sync(items)}
   print('SYNC_RESULT '+json.dumps(out,ensure_ascii=False),flush=True)
   raw=json.dumps(out,ensure_ascii=False).encode()
   self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  except Exception as e:
   raw=json.dumps({'error':str(e)},ensure_ascii=False).encode();self.send_response(500);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def log_message(self,fmt,*args): print(fmt%args,flush=True)
os.chdir(ROOT)
print(f'Course reader: http://{HOST}:{PORT}',flush=True)
ThreadingHTTPServer((HOST,PORT),H).serve_forever()
