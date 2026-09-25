import sys
from pathlib import Path
from html.parser import HTMLParser
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; PUB=ROOT/'public'
routes=['/fr/','/fr/a-propos','/fr/services-et-secteurs','/fr/projets','/fr/publications','/fr/actualites','/fr/carrieres','/fr/experts','/fr/durabilite','/fr/contact','/fr/newsletter','/en/','/en/about','/en/services-industries','/en/projects','/en/insights','/en/actuality','/en/careers','/en/experts','/en/sustainability','/en/contact','/en/newsletter']
widths=[320,375,768,1024,1280,1440,1920]
common_css=(PUB/'assets/css/common.css').read_text()

def file_for_route(route):
    clean=route.strip('/')
    if not clean:return PUB/'fr/index.html'
    p=PUB/clean
    if p.is_dir(): p=p/'index.html'
    if p.exists(): return p
    candidates=[p.with_suffix('.html'), PUB/(clean+'.html') if clean else PUB/'index.html']
    for c in candidates:
        if c.exists(): return c
    if clean=='fr/services-et-secteurs': return PUB/'fr/services-et-secteurs.html'
    if clean=='en/services-industries': return PUB/'en/services-industries.html'
    raise FileNotFoundError(route)

fail=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    page=browser.new_page()
    for route in routes:
        f=file_for_route(route)
        html=f.read_text()
        lang=f.relative_to(PUB).parts[0]
        page_css=(PUB/'assets/css'/lang/f'{f.stem}.css').read_text()
        html=html.replace('<link rel="stylesheet" href="/assets/css/common.css">',f'<style>{common_css}</style>')
        import re
        html=re.sub(r'<link rel="stylesheet" href="/assets/css/[^\"]+">',f'<style>{page_css}</style>',html)
        html=re.sub(r'<script type="module"[^>]+></script>','',html)
        for w in widths:
            page.set_viewport_size({'width':w,'height':900})
            page.set_content(html,wait_until='load')
            overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth + 1')
            if overflow: fail.append((route,w))
    browser.close()
if fail:
    print('OVERFLOW FAIL')
    for x in fail: print(x)
    sys.exit(1)
print('OVERFLOW OK: 22 routes across 7 widths.')
