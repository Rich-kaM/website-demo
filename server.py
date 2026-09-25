from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, ValidationError
import sqlite3, os, secrets, hashlib, hmac, base64, time, json, re, mimetypes, socket, struct
from pathlib import Path
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from html import escape
import smtplib

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / 'public'
PRIVATE = ROOT / 'private'
PRIVATE.mkdir(exist_ok=True)
UPLOADS = PRIVATE / 'uploads'
UPLOADS.mkdir(exist_ok=True)
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
DB_PATH = DATA / 'apah.db'
ENV = os.getenv('APP_ENV', 'development').lower()
SECRET = os.getenv('APP_SECRET', 'dev-only-change-this-secret-' + secrets.token_urlsafe(16)).encode()
COOKIE_SECURE = os.getenv('COOKIE_SECURE', '1' if ENV == 'production' else '0') == '1'
BASE_URL = os.getenv('APP_BASE_URL', '').rstrip('/')
APP_NAME = 'Africa Power Advisory Holding'

app = FastAPI(title=APP_NAME, docs_url=None, redoc_url=None)
app.mount('/assets', StaticFiles(directory=str(PUBLIC/'assets')), name='assets')

# Security headers middleware
@app.middleware('http')
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if COOKIE_SECURE:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con


def init_db():
    con = db()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      totp_secret TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'Viewer',
      active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      token_hash TEXT UNIQUE NOT NULL,
      user_id INTEGER,
      csrf_hash TEXT NOT NULL,
      expires_at TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS leads (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      phone TEXT,
      organization TEXT,
      country TEXT,
      purpose TEXT,
      service TEXT,
      preferred_contact TEXT,
      context TEXT,
      consent INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'new',
      assignee_id INTEGER,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY(assignee_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS newsletter_subscribers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      first_name TEXT,
      organization TEXT,
      language TEXT NOT NULL,
      topics TEXT NOT NULL DEFAULT '[]',
      consent_version TEXT NOT NULL,
      consent_source TEXT NOT NULL,
      consent_at TEXT NOT NULL,
      confirmed_at TEXT,
      unsubscribed_at TEXT,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS newsletter_tokens (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      subscriber_id INTEGER NOT NULL,
      token_hash TEXT UNIQUE NOT NULL,
      expires_at TEXT NOT NULL,
      used_at TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY(subscriber_id) REFERENCES newsletter_subscribers(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS applications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      email TEXT NOT NULL,
      phone TEXT,
      position TEXT,
      message TEXT,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'received',
      future_consent INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS actualities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      slug TEXT UNIQUE NOT NULL,
      title_en TEXT NOT NULL,
      title_fr TEXT NOT NULL,
      summary_en TEXT NOT NULL,
      summary_fr TEXT NOT NULL,
      body_en TEXT NOT NULL,
      body_fr TEXT NOT NULL,
      category TEXT NOT NULL,
      author TEXT,
      status TEXT NOT NULL DEFAULT 'Draft',
      published_at TEXT,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS jobs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      slug TEXT UNIQUE NOT NULL,
      title_en TEXT NOT NULL,
      title_fr TEXT NOT NULL,
      department TEXT NOT NULL,
      location TEXT NOT NULL,
      contract_type TEXT NOT NULL,
      summary_en TEXT NOT NULL,
      summary_fr TEXT NOT NULL,
      description_en TEXT NOT NULL,
      description_fr TEXT NOT NULL,
      closing_date TEXT,
      reference_number TEXT,
      status TEXT NOT NULL DEFAULT 'Draft',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER,
      action TEXT NOT NULL,
      entity_type TEXT NOT NULL,
      entity_id INTEGER,
      metadata TEXT,
      created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS rate_limits (
      key TEXT PRIMARY KEY,
      window_start INTEGER NOT NULL,
      count INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_actualities_status_date ON actualities(status,published_at);
    CREATE INDEX IF NOT EXISTS idx_jobs_status_date ON jobs(status,closing_date);
    CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
    ''')
    con.commit(); con.close()

init_db()


def now_iso(): return datetime.now(timezone.utc).isoformat()

def hash_secret(value: str) -> str:
    return hmac.new(SECRET, value.encode(), hashlib.sha256).hexdigest()

def hash_password(password: str, salt=None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return 'scrypt$16384$8$1$' + base64.urlsafe_b64encode(salt).decode().rstrip('=') + '$' + base64.urlsafe_b64encode(dk).decode().rstrip('=')

def verify_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt_b64, dk_b64 = stored.split('$',5)
        salt = base64.urlsafe_b64decode(salt_b64+'==')
        expected = base64.urlsafe_b64decode(dk_b64+'==')
        dk = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p), dklen=64)
        return hmac.compare_digest(dk, expected)
    except Exception: return False

def totp_code(secret_b32: str, for_counter=None):
    if for_counter is None: for_counter=int(time.time())//30
    key=base64.b32decode(secret_b32.upper()+('='*((8-len(secret_b32)%8)%8)))
    msg=for_counter.to_bytes(8,'big')
    digest=hmac.new(key,msg,hashlib.sha1).digest(); off=digest[-1]&15
    val=((digest[off]&127)<<24)|((digest[off+1])<<16)|((digest[off+2])<<8)|digest[off+3]
    return str(val%1000000).zfill(6)

def verify_totp(secret_b32, code):
    if not re.fullmatch(r'\d{6}', code or ''): return False
    c=int(time.time())//30
    return any(hmac.compare_digest(totp_code(secret_b32,c+i),code) for i in (-1,0,1))

def create_session(user_id):
    token=secrets.token_urlsafe(48); csrf=secrets.token_urlsafe(32); expiry=datetime.now(timezone.utc)+timedelta(hours=8)
    con=db(); con.execute('INSERT INTO sessions(token_hash,user_id,csrf_hash,expires_at,created_at) VALUES(?,?,?,?,?)',(hash_secret(token),user_id,hash_secret(csrf),expiry.isoformat(),now_iso()));con.commit();con.close()
    return token,csrf

def session_from_request(request: Request):
    tok=request.cookies.get('apah_session')
    if not tok:return None
    con=db(); row=con.execute('SELECT * FROM sessions WHERE token_hash=? AND expires_at>?',(hash_secret(tok),now_iso())).fetchone();con.close();return row

def require_csrf(request: Request):
    s=session_from_request(request)
    if s:
        sent=request.headers.get('X-CSRF-Token','')
        if not sent or not hmac.compare_digest(hash_secret(sent), s['csrf_hash']): raise HTTPException(403,'Invalid CSRF token')

def rate_limit(request: Request, bucket: str, limit=10, window=3600):
    ip=request.client.host if request.client else 'unknown'; key=hash_secret(bucket+'|'+ip)
    now=int(time.time()); start=now-(now%window)
    con=db(); row=con.execute('SELECT * FROM rate_limits WHERE key=?',(key,)).fetchone()
    if not row or row['window_start']!=start:
        con.execute('INSERT INTO rate_limits(key,window_start,count) VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET window_start=excluded.window_start,count=1',(key,start));con.commit();con.close();return
    if row['count']>=limit:con.close();raise HTTPException(429,'Too many attempts. Please try again later.')
    con.execute('UPDATE rate_limits SET count=count+1 WHERE key=?',(key,));con.commit();con.close()

def request_lang(request: Request) -> str:
    ref=request.headers.get('referer','')
    return 'fr' if '/fr/' in ref or request.url.path.startswith('/fr') else 'en'

def msg(request: Request, en: str, fr: str) -> str:
    return fr if request_lang(request)=='fr' else en

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse({'detail': msg(request, 'Please check the form fields and try again.', 'Veuillez vérifier les champs du formulaire et réessayer.')}, status_code=400)

class ContactIn(BaseModel):
    name: str = Field(min_length=2,max_length=160)
    email: EmailStr
    phone: str|None = Field(default=None,max_length=60)
    organization: str|None = Field(default=None,max_length=180)
    country: str|None = Field(default=None,max_length=120)
    purpose: str|None = Field(default=None,max_length=160)
    service: str|None = Field(default=None,max_length=180)
    preferred_contact: str|None = Field(default=None,max_length=80)
    message: str = Field(min_length=5,max_length=5000)
    consent: str
    website: str|None = Field(default=None,max_length=100)

class ChatIn(BaseModel):
    name: str = Field(min_length=2,max_length=160)
    email: EmailStr
    phone: str|None = Field(default=None,max_length=60)
    organization: str|None = Field(default=None,max_length=180)
    country: str|None = Field(default=None,max_length=120)
    purpose: str|None = Field(default=None,max_length=160)
    service: str|None = Field(default=None,max_length=180)
    preferred_contact: str|None = Field(default=None,max_length=80)
    context: str|None = Field(default=None,max_length=2000)
    consent: str
    website: str|None = Field(default=None,max_length=100)

class NewsletterIn(BaseModel):
    email: EmailStr
    first_name: str|None=Field(default=None,max_length=80)
    organization: str|None=Field(default=None,max_length=180)
    topics: list[str] = []
    consent: str
    website: str|None = Field(default=None,max_length=100)

class AdminLoginIn(BaseModel):
    email: EmailStr
    password: str=Field(min_length=10,max_length=200)
    otp: str=Field(pattern=r'^\d{6}$')


def send_email(to, subject, body, reply_to=None):
    host=os.getenv('SMTP_HOST'); port=int(os.getenv('SMTP_PORT','587')); user=os.getenv('SMTP_USERNAME'); pwd=os.getenv('SMTP_PASSWORD'); sender=os.getenv('SMTP_FROM')
    if not all([host,user,pwd,sender]):
        if ENV=='production': raise RuntimeError('SMTP not configured')
        print(f'[email-preview] TO={to} SUBJECT={subject}\n{body}')
        return False
    msg=EmailMessage();msg['From']=sender;msg['To']=to;msg['Subject']=subject
    if reply_to:msg['Reply-To']=reply_to
    msg.set_content(body)
    with smtplib.SMTP(host,port,timeout=15) as s:
        s.starttls();s.login(user,pwd);s.send_message(msg)
    return True

@app.get('/api/health')
async def health():
    con=db(); con.execute('SELECT 1'); con.close(); return {'status':'ok','service':'apah','environment':ENV}

@app.get('/api/csrf')
async def csrf(request: Request):
    s=session_from_request(request)
    if not s:
        return {'token':None}
    existing=request.cookies.get('apah_csrf') or ''
    if existing and hmac.compare_digest(hash_secret(existing), s['csrf_hash']):
        return {'token':existing}
    new_csrf=secrets.token_urlsafe(32); tok=request.cookies.get('apah_session'); token_hash=hash_secret(tok)
    con=db();con.execute('UPDATE sessions SET csrf_hash=? WHERE token_hash=?',(hash_secret(new_csrf),token_hash));con.commit();con.close()
    response=JSONResponse({'token':new_csrf})
    response.set_cookie('apah_csrf',new_csrf,httponly=False,secure=COOKIE_SECURE,samesite='lax',max_age=8*3600,path='/')
    return response

@app.post('/api/contact')
async def contact(payload: ContactIn, request: Request):
    rate_limit(request,'contact',8,3600)
    if payload.consent.lower()!='yes':raise HTTPException(400,msg(request,'Consent is required.','Le consentement est requis.'))
    if payload.website: raise HTTPException(400,msg(request,'Request rejected.','La demande a été rejetée.'))
    con=db(); ts=now_iso(); con.execute('INSERT INTO leads(name,email,phone,organization,country,purpose,service,preferred_contact,context,consent,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(payload.name,payload.email,payload.phone,payload.organization,payload.country,payload.purpose,payload.service,payload.preferred_contact,payload.message,1,ts,ts));con.commit();con.close()
    if os.getenv('NOTIFY_EMAIL'):
        try: send_email(os.getenv('NOTIFY_EMAIL'),f'New website inquiry from {payload.name}',f'Name: {payload.name}\nEmail: {payload.email}\nOrganization: {payload.organization or ""}\nPurpose: {payload.purpose or ""}\nService: {payload.service or ""}\nMessage:\n{payload.message}')
        except Exception: pass
    return {'ok':True,'message':msg(request,'Thank you. Your message has been received.','Merci. Votre message a bien été reçu.')}


@app.post('/api/chat')
async def chat(payload: ChatIn, request: Request):
    rate_limit(request,'chat',12,3600)
    if payload.consent.lower()!='yes':raise HTTPException(400,msg(request,'Consent is required.','Le consentement est requis.'))
    if payload.website: raise HTTPException(400,msg(request,'Request rejected.','La demande a été rejetée.'))
    con=db();ts=now_iso();con.execute('INSERT INTO leads(name,email,phone,organization,country,purpose,service,preferred_contact,context,consent,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(payload.name,payload.email,payload.phone,payload.organization,payload.country,payload.purpose or 'Website chatbot',payload.service,payload.preferred_contact,payload.context,1,'new',ts,ts));con.commit();con.close()
    return {'ok':True,'message':msg(request,'Your request has been received.','Votre demande a bien été reçue.')}


@app.post('/api/newsletter/subscribe')
async def newsletter(payload: NewsletterIn, request: Request):
    rate_limit(request,'newsletter',4,3600)
    if payload.consent.lower()!='yes':raise HTTPException(400,msg(request,'Consent is required.','Le consentement est requis.'))
    if payload.website: raise HTTPException(400,msg(request,'Request rejected.','La demande a été rejetée.'))
    lang='fr' if request.headers.get('referer','').find('/fr/')>=0 else 'en'
    ts=now_iso(); con=db();
    existing=con.execute('SELECT id FROM newsletter_subscribers WHERE email=?',(payload.email,)).fetchone()
    if existing:
        sid=existing['id']
    else:
        cur=con.execute('INSERT INTO newsletter_subscribers(email,first_name,organization,language,topics,consent_version,consent_source,consent_at,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(payload.email,payload.first_name,payload.organization,lang,json.dumps(payload.topics), 'newsletter-v1', request.headers.get('referer','website'),ts,ts)); sid=cur.lastrowid
    token=secrets.token_urlsafe(36); exp=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat();con.execute('INSERT INTO newsletter_tokens(subscriber_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)',(sid,hash_secret(token),exp,ts));con.commit();con.close()
    base=BASE_URL or str(request.base_url).rstrip('/'); confirm=f'{base}/newsletter/confirm?token=' + token
    subject='Confirm your APAH newsletter subscription' if lang=='en' else 'Confirmez votre abonnement à la newsletter APAH'
    body=('Please confirm your newsletter subscription using this link:\n'+confirm) if lang=='en' else ('Veuillez confirmer votre abonnement à la newsletter avec ce lien :\n'+confirm)
    try: send_email(payload.email,subject,body)
    except Exception:
        con=db();con.execute('DELETE FROM newsletter_tokens WHERE token_hash=?',(hash_secret(token),));con.commit();con.close();raise HTTPException(503,msg(request,'The subscription service is temporarily unavailable.','Le service d’abonnement est temporairement indisponible.'))
    return {'ok':True,'message':msg(request,'Please check your inbox and confirm your subscription.','Consultez votre boîte de réception et confirmez votre abonnement.')}


@app.get('/newsletter/confirm')
async def newsletter_confirm(token: str, request: Request):
    con=db(); row=con.execute('SELECT * FROM newsletter_tokens WHERE token_hash=? AND used_at IS NULL AND expires_at>?',(hash_secret(token),now_iso())).fetchone()
    if not row: con.close();return RedirectResponse('/fr/newsletter?status=invalid',303)
    con.execute('UPDATE newsletter_tokens SET used_at=? WHERE id=?',(now_iso(),row['id']));con.execute('UPDATE newsletter_subscribers SET confirmed_at=?,unsubscribed_at=NULL WHERE id=?',(now_iso(),row['subscriber_id']));con.commit();sub=con.execute('SELECT language FROM newsletter_subscribers WHERE id=?',(row['subscriber_id'],)).fetchone();con.close()
    return RedirectResponse(('/fr/newsletter?status=confirmed' if sub['language']=='fr' else '/en/newsletter?status=confirmed'),303)

@app.get('/newsletter/unsubscribe')
async def unsubscribe(token: str):
    con=db(); row=con.execute('SELECT subscriber_id FROM newsletter_tokens WHERE token_hash=?',(hash_secret(token),)).fetchone()
    if row: con.execute('UPDATE newsletter_subscribers SET unsubscribed_at=? WHERE id=?',(now_iso(),row['subscriber_id']));con.commit()
    con.close(); return HTMLResponse('<!doctype html><html><head><meta charset="utf-8"><title>Newsletter preference</title></head><body style="font-family:system-ui;max-width:700px;margin:10vh auto;padding:20px"><h1>Your newsletter preference was updated.</h1><p>You will no longer receive marketing emails from this subscription.</p></body></html>')


def safe_ext(name): return Path(name or '').suffix.lower()
def valid_upload(content: bytes, filename: str):
    ext=safe_ext(filename); allowed={'.pdf':b'%PDF-','.docx':b'PK\x03\x04'}
    if ext not in allowed: return False
    return content.startswith(allowed[ext])

def malware_scan(content: bytes) -> bool:
    required=os.getenv('UPLOAD_SCAN_REQUIRED','0')=='1' or ENV=='production'
    host=os.getenv('CLAMAV_HOST'); port=int(os.getenv('CLAMAV_PORT','3310')); unix_socket=os.getenv('CLAMAV_SOCKET')
    if not host and not unix_socket:
        if required:
            raise HTTPException(503,'Upload scanning is not configured. Please try again later.')
        return False
    try:
        sock=socket.socket(socket.AF_UNIX if unix_socket else socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect(unix_socket if unix_socket else (host,port))
        sock.sendall(b'zINSTREAM\0')
        for i in range(0,len(content),1024*1024):
            chunk=content[i:i+1024*1024];sock.sendall(struct.pack('!I',len(chunk)));sock.sendall(chunk)
        sock.sendall(struct.pack('!I',0))
        response=sock.recv(4096).decode('utf-8','ignore')
        sock.close()
        if 'FOUND' in response:
            return True
        if 'OK' not in response:
            raise RuntimeError('Unexpected scanner response')
        return False
    except HTTPException:
        raise
    except Exception:
        if required: raise HTTPException(503,'Upload security scanning is temporarily unavailable.')
        return False

@app.post('/api/applications')
async def applications(request: Request, name: str=Form(...), email: str=Form(...), phone: str=Form(''), position: str=Form(''), message: str=Form(''), privacy_ack: str=Form(...), future_consent: str=Form(''), website: str=Form(''), cv: UploadFile=File(...)):
    rate_limit(request,'applications',5,3600)
    if privacy_ack!='yes':raise HTTPException(400,'Privacy acknowledgment is required.' if request_lang(request)=='en' else 'La confirmation de confidentialité est requise.')
    if website:raise HTTPException(400,msg(request,'Request rejected.','La demande a été rejetée.'))
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+',email):raise HTTPException(400,'Enter a valid email address.' if request_lang(request)=='en' else 'Veuillez saisir une adresse e-mail valide.')
    if cv.size and cv.size>5*1024*1024:raise HTTPException(400,'File too large. Maximum size is 5 MB.' if request_lang(request)=='en' else 'Fichier trop volumineux. La taille maximale est de 5 Mo.')
    content=await cv.read()
    allowed_mime={'.pdf':{'application/pdf','application/octet-stream',''},'.docx':{'application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/zip','application/octet-stream',''}}
    suffix=safe_ext(cv.filename)
    if len(content)>5*1024*1024 or not valid_upload(content,cv.filename) or cv.content_type not in allowed_mime.get(suffix,set()):
        raise HTTPException(400,'Upload a PDF or DOCX CV up to 5 MB.' if request_lang(request)=='en' else 'Téléversez un CV PDF ou DOCX de 5 Mo maximum.')
    if malware_scan(content):
        raise HTTPException(400,'The uploaded file was rejected by security scanning.' if request_lang(request)=='en' else 'Le fichier téléversé a été rejeté par le contrôle de sécurité.')
    stored=secrets.token_urlsafe(24).replace('-','_')+suffix; dest=UPLOADS/stored; dest.write_bytes(content)
    ts=now_iso();con=db();con.execute('INSERT INTO applications(name,email,phone,position,message,file_name,file_path,future_consent,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(name,email,phone,position,message,cv.filename,stored,1 if future_consent=='yes' else 0,ts,ts));con.commit();con.close()
    return {'ok':True,'message':msg(request,'Your application has been received.','Votre candidature a bien été reçue.')}


@app.post('/api/admin/login')
async def admin_login(payload: AdminLoginIn, request: Request):
    rate_limit(request,'admin-login',8,900)
    con=db();row=con.execute('SELECT * FROM users WHERE email=? AND active=1',(payload.email.lower(),)).fetchone();con.close()
    if not row or not verify_password(payload.password,row['password_hash']) or not verify_totp(row['totp_secret'],payload.otp):
        raise HTTPException(401,'Invalid sign-in details.')
    token,csrf=create_session(row['id'])
    resp=JSONResponse({'ok':True,'role':row['role']})
    resp.set_cookie('apah_session',token,httponly=True,secure=COOKIE_SECURE,samesite='lax',max_age=8*3600,path='/')
    resp.set_cookie('apah_csrf',csrf,httponly=False,secure=COOKIE_SECURE,samesite='lax',max_age=8*3600,path='/')
    return resp

@app.post('/api/admin/logout')
async def admin_logout(request: Request):
    require_csrf(request);tok=request.cookies.get('apah_session')
    con=db();con.execute('DELETE FROM sessions WHERE token_hash=?',(hash_secret(tok),));con.commit();con.close()
    resp=JSONResponse({'ok':True});resp.delete_cookie('apah_session',path='/');resp.delete_cookie('apah_csrf',path='/');return resp

def admin_user(request):
    s=session_from_request(request)
    if not s:raise HTTPException(401,'Authentication required.')
    con=db();u=con.execute('SELECT * FROM users WHERE id=? AND active=1',(s['user_id'],)).fetchone();con.close()
    if not u:raise HTTPException(401,'Authentication required.')
    return u

def role_ok(user, *roles):
    return user['role'] in roles or user['role']=='Admin'

def valid_slug(slug: str) -> bool:
    return bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug or ''))

def audit(u, action, entity_type, entity_id, metadata=None):
    con=db();con.execute('INSERT INTO audit_logs(user_id,action,entity_type,entity_id,metadata,created_at) VALUES(?,?,?,?,?,?)',(u['id'],action,entity_type,entity_id,json.dumps(metadata or {}),now_iso()));con.commit();con.close()

@app.get('/api/admin/data')
async def admin_data(request: Request):
    u=admin_user(request)
    con=db()
    counts={k:con.execute(q).fetchone()[0] for k,q in {'leads':'SELECT COUNT(*) FROM leads','applications':'SELECT COUNT(*) FROM applications','subscribers':'SELECT COUNT(*) FROM newsletter_subscribers WHERE confirmed_at IS NOT NULL AND unsubscribed_at IS NULL','actualities':'SELECT COUNT(*) FROM actualities','jobs':'SELECT COUNT(*) FROM jobs'}.items()}
    leads=[dict(r) for r in con.execute('SELECT id,name,email,organization,status,created_at FROM leads ORDER BY id DESC LIMIT 100')]
    apps=[dict(r) for r in con.execute('SELECT id,name,email,position,status,created_at FROM applications ORDER BY id DESC LIMIT 100')]
    subs=[dict(r) for r in con.execute('SELECT id,email,language,confirmed_at,unsubscribed_at FROM newsletter_subscribers ORDER BY id DESC LIMIT 100')]
    actualities=[dict(r) for r in con.execute('SELECT id,slug,title_en,title_fr,category,status,published_at,updated_at FROM actualities ORDER BY id DESC LIMIT 100')]
    jobs=[dict(r) for r in con.execute('SELECT id,slug,title_en,title_fr,department,location,contract_type,status,closing_date,updated_at FROM jobs ORDER BY id DESC LIMIT 100')]
    con.close();return {'user':dict(u),'counts':counts,'leads':leads,'applications':apps,'subscribers':subs,'actualities':actualities,'jobs':jobs}

@app.patch('/api/admin/leads/{lead_id}')
async def update_lead(lead_id:int, request:Request):
    u=admin_user(request);require_csrf(request)
    if not role_ok(u,'Admin','Editor','Viewer'):raise HTTPException(403,'Not authorized.')
    data=await request.json();status=data.get('status');assignee=data.get('assignee_id')
    allowed={'new','contacted','qualified','closed'}
    if status not in allowed:raise HTTPException(400,'Invalid status.')
    con=db();con.execute('UPDATE leads SET status=?,assignee_id=?,updated_at=? WHERE id=?',(status,assignee or None,now_iso(),lead_id));con.commit();con.close();audit(u,'update','lead',lead_id,{'status':status,'assignee_id':assignee});return {'ok':True}

@app.post('/api/admin/actuality')
async def admin_actuality(request: Request):
    u=admin_user(request);require_csrf(request)
    if not role_ok(u,'Admin','Editor','Approver'): raise HTTPException(403,'Not authorized.')
    data=await request.json()
    required=['slug','title_en','title_fr','summary_en','summary_fr','body_en','body_fr','category','status']
    if any(not str(data.get(k,'')).strip() for k in required): raise HTTPException(400,'Required fields are missing.')
    if not valid_slug(data['slug']): raise HTTPException(400,'Use a lowercase URL slug with letters, numbers and hyphens.')
    status=data['status'];allowed={'Draft','In review','Approved','Published','Archived'}
    if status not in allowed: raise HTTPException(400,'Invalid status.')
    if status=='Published' and not role_ok(u,'Admin','Approver'): raise HTTPException(403,'Publication requires an approver role.')
    ts=now_iso();pub=ts if status=='Published' else None
    con=db();con.execute('''INSERT INTO actualities(slug,title_en,title_fr,summary_en,summary_fr,body_en,body_fr,category,author,status,published_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET title_en=excluded.title_en,title_fr=excluded.title_fr,summary_en=excluded.summary_en,summary_fr=excluded.summary_fr,body_en=excluded.body_en,body_fr=excluded.body_fr,category=excluded.category,author=excluded.author,status=excluded.status,published_at=excluded.published_at,updated_at=excluded.updated_at''',
      (data['slug'],data['title_en'],data['title_fr'],data['summary_en'],data['summary_fr'],data['body_en'],data['body_fr'],data['category'],data.get('author'),status,pub,ts))
    row=con.execute('SELECT id FROM actualities WHERE slug=?',(data['slug'],)).fetchone();con.commit();con.close();audit(u,'upsert','actuality',row['id'],{'slug':data['slug'],'status':status});return {'ok':True,'id':row['id']}

@app.post('/api/admin/jobs')
async def admin_job(request: Request):
    u=admin_user(request);require_csrf(request)
    if not role_ok(u,'Admin','Editor','Recruiter','Approver'): raise HTTPException(403,'Not authorized.')
    data=await request.json()
    required=['slug','title_en','title_fr','department','location','contract_type','summary_en','summary_fr','description_en','description_fr','status']
    if any(not str(data.get(k,'')).strip() for k in required): raise HTTPException(400,'Required fields are missing.')
    if not valid_slug(data['slug']): raise HTTPException(400,'Use a lowercase URL slug with letters, numbers and hyphens.')
    status=data['status'];allowed={'Draft','In review','Approved','Published','Closed'}
    if status not in allowed: raise HTTPException(400,'Invalid status.')
    if status=='Published' and not role_ok(u,'Admin','Approver'): raise HTTPException(403,'Publication requires an approver role.')
    ts=now_iso();con=db();con.execute('''INSERT INTO jobs(slug,title_en,title_fr,department,location,contract_type,summary_en,summary_fr,description_en,description_fr,closing_date,reference_number,status,created_at,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET title_en=excluded.title_en,title_fr=excluded.title_fr,department=excluded.department,location=excluded.location,contract_type=excluded.contract_type,summary_en=excluded.summary_en,summary_fr=excluded.summary_fr,description_en=excluded.description_en,description_fr=excluded.description_fr,closing_date=excluded.closing_date,reference_number=excluded.reference_number,status=excluded.status,updated_at=excluded.updated_at''',
      (data['slug'],data['title_en'],data['title_fr'],data['department'],data['location'],data['contract_type'],data['summary_en'],data['summary_fr'],data['description_en'],data['description_fr'],data.get('closing_date') or None,data.get('reference_number') or None,status,ts,ts))
    row=con.execute('SELECT id FROM jobs WHERE slug=?',(data['slug'],)).fetchone();con.commit();con.close();audit(u,'upsert','job',row['id'],{'slug':data['slug'],'status':status});return {'ok':True,'id':row['id']}

@app.patch('/api/admin/applications/{application_id}')
async def update_application(application_id:int, request: Request):
    u=admin_user(request);require_csrf(request)
    if not role_ok(u,'Admin','Recruiter','Editor'): raise HTTPException(403,'Not authorized.')
    data=await request.json();status=data.get('status')
    allowed={'received','reviewing','shortlisted','rejected','hired','closed'}
    if status not in allowed: raise HTTPException(400,'Invalid status.')
    con=db();con.execute('UPDATE applications SET status=?,updated_at=? WHERE id=?',(status,now_iso(),application_id));con.commit();con.close();audit(u,'update','application',application_id,{'status':status});return {'ok':True}

@app.get('/api/actuality')
async def actuality(lang: str='en'):
    lang='fr' if lang=='fr' else 'en';con=db();rows=con.execute('SELECT slug,title_en,title_fr,summary_en,summary_fr,category,author,published_at FROM actualities WHERE status="Published" ORDER BY published_at DESC').fetchall();con.close()
    key='fr' if lang=='fr' else 'en';return {'items':[{'slug':r['slug'],'title':r[f'title_{key}'],'summary':r[f'summary_{key}'],'category':r['category'],'author':r['author'],'published_at':r['published_at']} for r in rows]}

@app.get('/api/jobs')
async def jobs(lang: str='en'):
    lang='fr' if lang=='fr' else 'en';con=db();rows=con.execute('SELECT slug,title_en,title_fr,department,location,contract_type,summary_en,summary_fr,closing_date,reference_number FROM jobs WHERE status="Published" ORDER BY created_at DESC').fetchall();con.close(); key='fr' if lang=='fr' else 'en';return {'jobs':[{'slug':r['slug'],'title':r[f'title_{key}'],'department':r['department'],'location':r['location'],'contract_type':r['contract_type'],'summary':r[f'summary_{key}'],'closing_date':r['closing_date'],'reference_number':r['reference_number']} for r in rows]}

@app.get('/robots.txt')
async def robots():
    return PlainTextResponse('User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /api/\nSitemap: /sitemap.xml\n')

@app.get('/sitemap.xml')
async def sitemap(request:Request):
    base=BASE_URL or str(request.base_url).rstrip('/');paths=[]
    for lang in ('fr','en'):
        for p in (PUBLIC/lang).rglob('*.html'):
            rel=p.relative_to(PUBLIC).as_posix()
            if rel.startswith('admin/') or rel.startswith('errors/'):continue
            if rel.endswith('/index.html'):
                paths.append(base+'/'+rel[:-10]+'/' if rel[:-10] else base+'/')
            elif rel.endswith('.html'):
                paths.append(base+'/'+rel[:-5])
    # Include canonical clean URLs only.
    con=db(); rows=con.execute('SELECT slug FROM actualities WHERE status="Published"').fetchall(); con.close()
    for r in rows:
        paths.append(base+'/en/actuality/'+r['slug'])
        paths.append(base+'/fr/actualites/'+r['slug'])
    unique=[]
    for x in sorted(set(paths)):
        if '/errors/' not in x: unique.append(x)
    body='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{x}</loc></url>' for x in unique)+'</urlset>'
    return Response(content=body,media_type='application/xml')

# Redirects from retired URLs
@app.get('/en/services')
async def old_en_services(): return RedirectResponse('/en/services-industries',301)
@app.get('/en/industries')
async def old_en_industries(): return RedirectResponse('/en/services-industries#industries',301)
@app.get('/fr/services')
async def old_fr_services(): return RedirectResponse('/fr/services-et-secteurs',301)
@app.get('/fr/industries')
async def old_fr_industries(): return RedirectResponse('/fr/services-et-secteurs#industries',301)

# Dynamic actuality article pages
@app.get('/en/actuality/{slug}')
async def actuality_article_en(slug:str):
    return await _actuality_article('en', slug)

@app.get('/fr/actualites/{slug}')
async def actuality_article_fr(slug:str):
    return await _actuality_article('fr', slug)

async def _actuality_article(lang:str, slug:str):
    con=db(); r=con.execute('SELECT * FROM actualities WHERE slug=? AND status="Published"',(slug,)).fetchone(); con.close()
    if not r: raise HTTPException(404)
    lang_file='actuality' if lang=='en' else 'actualites'
    template=(PUBLIC/lang/f'{lang_file}.html').read_text()
    key='fr' if lang=='fr' else 'en'
    title=escape(r[f'title_{key}'])
    summary=escape(r[f'summary_{key}'])
    body=escape(r[f'body_{key}']).replace(chr(10),'<br>')
    category=escape(r['category'])
    published=escape(r['published_at'] or '')
    route_part='actuality' if lang=='en' else 'actualites'
    canonical=f'/{lang}/{route_part}/{slug}'
    newsletter_label='Subscribe to Newsletter' if lang=='en' else 'S’abonner à la newsletter'
    og_locale='fr_FR' if lang=='fr' else 'en_US'
    main_html=f'''<main id="main"><section class="page-hero"><div class="container"><span class="eyebrow">{category}</span><h1>{title}</h1><p>{summary}</p><p class="help">{published}</p></div></section><section class="section"><div class="container legal"><p>{body}</p><div style="margin-top:30px"><a class="btn btn-primary" href="/{lang}/newsletter">{newsletter_label}</a></div></div></section></main>'''
    template=re.sub(r'<title>.*?</title>', f'<title>{title} | {APP_NAME}</title>', template, count=1, flags=re.S)
    template=re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{summary}">', template, count=1)
    template=re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{canonical}">', template, count=1)
    template=re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{title}">', template, count=1)
    template=re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{summary}">', template, count=1)
    template=re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{canonical}">', template, count=1)
    template=re.sub(r'<meta property="og:locale" content="[^"]*">', f'<meta property="og:locale" content="{'fr_FR' if lang=='fr' else 'en_US'}">', template, count=1)
    # Replace hreflang alternates with article equivalents.
    template=re.sub(r'<link rel="alternate" hreflang="en" href="[^"]*">', f'<link rel="alternate" hreflang="en" href="/en/actuality/{slug}">', template, count=1)
    template=re.sub(r'<link rel="alternate" hreflang="fr" href="[^"]*">', f'<link rel="alternate" hreflang="fr" href="/fr/actualites/{slug}">', template, count=1)
    template=re.sub(r'<link rel="alternate" hreflang="x-default" href="[^"]*">', f'<link rel="alternate" hreflang="x-default" href="/fr/actualites/{slug}">', template, count=1)
    old_main=template[template.index('<main id="main">'):template.index('</main>')+7]
    template=template.replace(old_main, main_html, 1)
    return HTMLResponse(template)

@app.exception_handler(404)
async def custom_404(request:Request, exc):
    lang='fr' if request.url.path.startswith('/fr') else 'en'
    path=PUBLIC/'errors'/lang/'404.html'
    if path.exists(): return FileResponse(path,status_code=404)
    return PlainTextResponse('Not found',status_code=404)

@app.get('/{path:path}')
async def static_resolver(path:str):
    if not path: return FileResponse(PUBLIC/'fr/index.html')
    clean=path.lstrip('/')
    candidate=PUBLIC/clean
    if candidate.is_file(): return FileResponse(candidate)
    if not candidate.suffix:
        html_candidate=candidate.with_suffix('.html')
        if html_candidate.is_file():return FileResponse(html_candidate)
        idx=candidate/'index.html'
        if idx.is_file():return FileResponse(idx)
    raise HTTPException(404)

if __name__=='__main__':
    import uvicorn
    uvicorn.run('server:app',host=os.getenv('HOST','127.0.0.1'),port=int(os.getenv('PORT','8000')),reload=False)
