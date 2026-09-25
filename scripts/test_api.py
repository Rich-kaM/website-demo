import subprocess,sys,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
proc=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    time.sleep(1.5)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl): return None
    opener=urllib.request.build_opener(NoRedirect)
    def get(url):
        try:
            r=opener.open('http://127.0.0.1:8000'+url,timeout=5);return r.status,r.read()
        except urllib.error.HTTPError as e:return e.code,e.read()
    tests=[('/api/health',200),('/en/',200),('/fr/',200),('/en/contact',200),('/fr/contact',200),('/robots.txt',200),('/sitemap.xml',200),('/does-not-exist',404),('/en/services',301),('/fr/industries',301)]
    ok=True
    for url,expect in tests:
        status,body=get(url); print(url,status); ok &= status==expect
    sys.exit(0 if ok else 1)
finally:
    proc.terminate();proc.wait(timeout=5)
