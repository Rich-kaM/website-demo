from pathlib import Path
from html.parser import HTMLParser
import re, sys
ROOT=Path(__file__).resolve().parents[1]; PUB=ROOT/'public'
errors=[]
placeholder_patterns=[r'\bTODO\b',r'\bTBD\b',r'Coming soon',r'Your text here',r'example\.com',r'John Doe',r'Lorem ipsum',r'\[TO BE (?:SUPPLIED|VERIFIED|DEFINED WITH LEGAL REVIEW)\]']
class P(HTMLParser):
    def __init__(self):super().__init__();self.tags=[];self.title='';self.meta_desc=False;self.h1=0
    def handle_starttag(self,tag,attrs):
        self.tags.append(tag)
        d=dict(attrs)
        if tag=='h1':self.h1+=1
        if tag=='meta' and d.get('name')=='description' and d.get('content'):self.meta_desc=True
    def handle_data(self,data):
        if 'title' in self.tags:self.title+=data
    def handle_endtag(self,tag):
        if self.tags and self.tags[-1]==tag:self.tags.pop()

pages=[p for p in PUB.rglob('*.html') if '/errors/' not in p.as_posix() or True]
for p in pages:
    txt=p.read_text(errors='ignore')
    for pat in placeholder_patterns:
        if re.search(pat,txt,re.I):
            # Allow documentation markers only in docs, never public HTML.
            errors.append(f'placeholder in {p}: {pat}')
    q=P();q.feed(txt)
    if p.name not in ('index.html',) and not q.title.strip(): errors.append(f'missing title {p}')
    if p.name not in ('index.html',) and not q.meta_desc and not str(p).startswith(str(PUB/'errors')) and not str(p).startswith(str(PUB/'admin')): errors.append(f'missing meta description {p}')
    if q.h1>1 and 'errors' not in str(p): errors.append(f'multiple h1 {p}')
    for a in re.findall(r'<(?:img)\b([^>]*)>',txt,re.I):
        if not re.search(r'\balt=',a,re.I): errors.append(f'missing img alt {p}')
        if not re.search(r'\b(width|height)=',a,re.I): errors.append(f'missing img dimensions {p}')
    for link in re.findall(r'(?:href|src)="([^"]+)"',txt,re.I):
        if link.startswith('/') and not link.startswith('//') and not link.startswith('/api/'):
            if any(link.startswith(x) for x in ['/assets/']):
                target=PUB/link.lstrip('/')
                if not target.exists(): errors.append(f'missing asset {link} referenced by {p}')

# Admin pages use their own page-level assets.
for lang in ('en','fr'):
    adm=PUB/'admin'/lang/'index.html'
    txt=adm.read_text(errors='ignore')
    if f'/assets/css/admin/{lang}/index.css' not in txt: errors.append(f'missing admin-specific CSS reference {adm}')
    if f'/assets/js/admin/{lang}/index.js' not in txt: errors.append(f'missing admin-specific JS reference {adm}')

# matching CSS/JS for content pages
for p in pages:
    if p.name=='index.html' and p.parent==PUB: continue
    if p.is_relative_to(PUB/'errors') or p.is_relative_to(PUB/'admin'): continue
    lang=p.relative_to(PUB).parts[0]; stem=p.stem
    if not (PUB/'assets/css'/lang/f'{stem}.css').exists(): errors.append(f'missing CSS for {p}')
    if not (PUB/'assets/js'/lang/f'{stem}.js').exists(): errors.append(f'missing JS for {p}')

if errors:
    print('VALIDATION FAILED')
    print('\n'.join(errors[:200]))
    sys.exit(1)
print(f'VALIDATION OK: {len(pages)} HTML pages checked.')
