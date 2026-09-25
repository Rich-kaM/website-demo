import subprocess,sys,time,re,urllib.request,urllib.parse,urllib.error,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; PUB=ROOT/'public'
proc=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    time.sleep(1.2)
    base='http://127.0.0.1:8000'
    html_files=[p for p in PUB.rglob('*.html') if 'errors' not in p.parts and 'admin' not in p.parts and p.name!='index.html']
    failures=[]
    # Verify internal navigation targets.
    for f in html_files:
        txt=f.read_text(errors='ignore')
        for href in re.findall(r'href="([^"]+)"',txt,re.I):
            if not href.startswith('/') or href.startswith('//') or href.startswith('/api/') or href.startswith('/assets/') or href.startswith('/newsletter/') or href.startswith('/sitemap.xml') or href.startswith('/robots.txt'):
                continue
            target=urllib.parse.urlsplit(href).path
            try:
                req=urllib.request.Request(base+target,method='GET')
                with urllib.request.urlopen(req,timeout=5) as r: code=r.status
            except urllib.error.HTTPError as e: code=e.code
            except Exception as e: failures.append((f.relative_to(PUB).as_posix(),href,'ERR',str(e)));continue
            if code not in (200,301,302,303): failures.append((f.relative_to(PUB).as_posix(),href,code,''))
    # Browser theme and language switch behavior with local HTML and inline CSS/JS.
    common_css=(PUB/'assets/css/common.css').read_text(); common_js=(PUB/'assets/js/common.js').read_text().replace("const saved=localStorage.getItem('apah-theme');","const saved=null;").replace("localStorage.setItem('apah-theme',body.classList.contains('dark')?'dark':'light');","")
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=b.new_page(viewport={'width':1280,'height':900})
        for f in [PUB/'en/index.html',PUB/'fr/index.html',PUB/'en/services-industries/services/energy-advisory.html',PUB/'fr/services-et-secteurs/services/conseil-energetique.html']:
            html=f.read_text()
            html=html.replace('<link rel="stylesheet" href="/assets/css/common.css">',f'<style>{common_css}</style>')
            lang=f.relative_to(PUB).parts[0]
            html=re.sub(r'<link rel="stylesheet" href="/assets/css/[^\"]+">',f'<style>{(PUB/"assets/css"/lang/(f.stem+".css")).read_text()}</style>',html)
            html=re.sub(r'<script type="module"[^>]+></script>',f'<script>{common_js}</script>',html)
            page.set_content(html,wait_until='load')
            page.evaluate('document.body.classList.remove("dark")')
            theme=page.locator('[data-theme-toggle]').first
            theme.click();
            if not page.locator('body.dark').count(): failures.append((f.name,'theme','not dark',''))
            theme.click();
            sw=page.locator('[data-language-switch]').first
            target=sw.get_attribute('href')
            if not target or target==page.url: failures.append((f.name,'language','bad href',target))
        b.close()
    if failures:
        print('SITE TEST FAILED')
        for x in failures[:100]: print(x)
        sys.exit(1)
    print(f'SITE TEST OK: {len(html_files)} pages crawled for internal links, theme toggle and language switch.')
finally:
    proc.terminate();proc.wait(timeout=5)
