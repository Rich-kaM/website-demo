from pathlib import Path
import re, sys
ROOT=Path(__file__).resolve().parents[1]
scan_roots=[ROOT/'public',ROOT/'server.py',ROOT/'scripts',ROOT/'docs',ROOT/'README.md',ROOT/'.env.example']
secret_patterns=[r'ghp_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'AKIA[0-9A-Z]{16}',r'-----BEGIN [A-Z ]+PRIVATE KEY-----',r'(?i)sk-[A-Za-z0-9_-]{20,}']
placeholder_patterns=[r'\[TO BE (?:SUPPLIED|VERIFIED|DEFINED WITH LEGAL REVIEW)\]',r'\bTODO\b',r'\bTBD\b',r'lorem ipsum',r'John Doe',r'example\.com']
errors=[]
files=[]
for item in scan_roots:
    p=item if item.is_file() else item
    if p.is_file(): files=[p] if not files else files+[p]
    elif p.exists(): files.extend(x for x in p.rglob('*') if x.is_file() and x.suffix.lower() in {'.html','.js','.css','.py','.md','.yaml','.yml','.env'})
for p in files:
    txt=p.read_text(errors='ignore')
    for pat in secret_patterns:
        if re.search(pat,txt): errors.append(f'secret pattern: {p}: {pat}')
# Public pages must not leak source placeholder markers or developer task text.
for p in (ROOT/'public').rglob('*.html'):
    txt=p.read_text(errors='ignore')
    for pat in placeholder_patterns:
        if re.search(pat,txt,re.I): errors.append(f'public placeholder: {p}: {pat}')
# Public bundles must not contain environment secret names with assigned values.
for p in (ROOT/'public').rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.js','.css','.html'}:
        txt=p.read_text(errors='ignore')
        if re.search(r'(?i)(APP_SECRET|SMTP_PASSWORD|OPTIONAL_CAPTCHA_SECRET)\s*[:=]\s*[\'\"][^\'\"]+',txt): errors.append(f'public config secret assignment: {p}')
if errors:
    print('SECURITY SCAN FAILED')
    print('\n'.join(errors[:100]))
    sys.exit(1)
print(f'SECURITY SCAN OK: {len(files)} source/docs files inspected.')
