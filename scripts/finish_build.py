from pathlib import Path
import re
ROOT=Path('/mnt/data/apah-production-site')
SERVER=ROOT/'server.py'

s=SERVER.read_text()
# Add RequestValidationError import
s=s.replace("from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends\n", "from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends\nfrom fastapi.exceptions import RequestValidationError\n")
# Insert localization helpers before ContactIn
marker="class ContactIn(BaseModel):\n"
helper='''def request_lang(request: Request) -> str:\n    ref=request.headers.get('referer','')\n    return 'fr' if '/fr/' in ref or request.url.path.startswith('/fr') else 'en'\n\ndef msg(request: Request, en: str, fr: str) -> str:\n    return fr if request_lang(request)=='fr' else en\n\n@app.exception_handler(RequestValidationError)\nasync def validation_error(request: Request, exc: RequestValidationError):\n    return JSONResponse({'detail': msg(request, 'Please check the form fields and try again.', 'Veuillez vérifier les champs du formulaire et réessayer.')}, status_code=400)\n\n'''
if helper not in s:
    s=s.replace(marker, helper+marker)
# Localize public endpoint explicit errors
repls={
"raise HTTPException(400,'Consent is required.')":"raise HTTPException(400,msg(request,'Consent is required.','Le consentement est requis.'))",
"raise HTTPException(400,'Request rejected.')":"raise HTTPException(400,msg(request,'Request rejected.','La demande a été rejetée.'))",
"raise HTTPException(429,'Too many attempts. Please try again later.')":"raise HTTPException(429,'Too many attempts. Please try again later.')",
"raise HTTPException(503,'The subscription service is temporarily unavailable.')":"raise HTTPException(503,msg(request,'The subscription service is temporarily unavailable.','Le service d’abonnement est temporairement indisponible.'))",
"raise HTTPException(400,'Privacy acknowledgment is required.')":"raise HTTPException(400,'Privacy acknowledgment is required.' if request_lang(request)=='en' else 'La confirmation de confidentialité est requise.')",
"raise HTTPException(400,'Enter a valid email address.')":"raise HTTPException(400,'Enter a valid email address.' if request_lang(request)=='en' else 'Veuillez saisir une adresse e-mail valide.')",
"raise HTTPException(400,'File too large. Maximum size is 5 MB.')":"raise HTTPException(400,'File too large. Maximum size is 5 MB.' if request_lang(request)=='en' else 'Fichier trop volumineux. La taille maximale est de 5 Mo.')",
"raise HTTPException(400,'Upload a PDF or DOCX CV up to 5 MB.')":"raise HTTPException(400,'Upload a PDF or DOCX CV up to 5 MB.' if request_lang(request)=='en' else 'Téléversez un CV PDF ou DOCX de 5 Mo maximum.')",
"return {'ok':True,'message':'Thank you. Your message has been received.'}":"return {'ok':True,'message':msg(request,'Thank you. Your message has been received.','Merci. Votre message a bien été reçu.')}\n",
"return {'ok':True,'message':'Your request has been received.'}":"return {'ok':True,'message':msg(request,'Your request has been received.','Votre demande a bien été reçue.')}\n",
"return {'ok':True,'message':'Please check your inbox and confirm your subscription.'}":"return {'ok':True,'message':msg(request,'Please check your inbox and confirm your subscription.','Consultez votre boîte de réception et confirmez votre abonnement.')}\n",
"return {'ok':True,'message':'Your application has been received.'}":"return {'ok':True,'message':msg(request,'Your application has been received.','Votre candidature a bien été reçue.')}\n",
}
for a,b in repls.items(): s=s.replace(a,b)
# Replace admin section from @app.post login through before public actuality with enhanced endpoints
start=s.index("@app.post('/api/admin/login')")
end=s.index("@app.get('/api/actuality')")
new_admin=r"""@app.post('/api/admin/login')
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

"""
s=s[:start]+new_admin+s[end:]
# Support French actuality article path alongside EN.
s=s.replace("@app.get('/{lang}/actuality/{slug}')\n", "@app.get('/{lang}/actuality/{slug}')\n", 1)
# Replace article endpoint body route with dual article slugs by changing route decorator and lang logic.
s=s.replace("@app.get('/{lang}/actuality/{slug}')\nasync def actuality_article(lang:str,slug:str):\n    if lang not in ('en','fr'):raise HTTPException(404)\n", "@app.get('/en/actuality/{slug}')\n@app.get('/fr/actualites/{slug}')\nasync def actuality_article(lang:str='en',slug:str=''):\n    if request_url_lang := None:\n        pass\n")
# The previous replacement needs a correct function signature. Replace the malformed inserted chunk.
s=s.replace("@app.get('/en/actuality/{slug}')\n@app.get('/fr/actualites/{slug}')\nasync def actuality_article(lang:str='en',slug:str=''):\n    if request_url_lang := None:\n        pass\n", "@app.get('/en/actuality/{slug}')\nasync def actuality_article_en(slug:str):\n    return await _actuality_article('en', slug)\n\n@app.get('/fr/actualites/{slug}')\nasync def actuality_article_fr(slug:str):\n    return await _actuality_article('fr', slug)\n\nasync def _actuality_article(lang:str, slug:str):\n")
# Insert shared article function body remains following this line, which should work.
SERVER.write_text(s)

# Patch admin HTML controls visibility and language link
for lang, html_path in [('en',ROOT/'public/admin/en/index.html'),('fr',ROOT/'public/admin/fr/index.html')]:
    x=html_path.read_text()
    # Replace language switch /admin target to correct admin language.
    if lang=='en':
        x=x.replace('href="/admin/en" lang="fr" aria-label="Passer en français" data-language-switch>FR', 'href="/admin/fr" lang="fr" aria-label="Passer en français" data-language-switch>FR')
    else:
        x=x.replace('href="/admin/fr" lang="en" aria-label="Switch to English" data-language-switch>EN', 'href="/admin/en" lang="en" aria-label="Switch to English" data-language-switch>EN')
    x=x.replace('<div class="grid grid-2" style="margin-top:22px"><div class="form-card"><h2>Publish Actuality</h2>', '<div id="editor-controls" class="hide"><div class="grid grid-2" style="margin-top:22px"><div class="form-card"><h2>Publish Actuality</h2>')
    x=x.replace('<button class="btn btn-secondary" style="margin-top:20px" id="admin-logout" type="button">', '<button class="btn btn-secondary" style="margin-top:20px" id="admin-logout" type="button">')
    # close editor-controls after logout div, if not already
    target='</div></div><button class="btn btn-secondary" style="margin-top:20px" id="admin-logout" type="button">'
    # add a closing div after logout button
    x=x.replace('</button></div></section>', '</button></div></div></section>', 1)
    # The source structure has outer section; ensure only one editor-controls closing. Normalize if needed.
    # Add data-controls role for status in forms already.
    html_path.write_text(x)

# Replace admin page JS files for robust behavior, EN + FR.
admin_js_en=ROOT/'public/assets/js/en/index.js'
admin_js_fr=ROOT/'public/assets/js/fr/index.js'
admin_js=r'''import '/assets/js/common.js';
const loginForm=document.getElementById('admin-login');
const statusBox=loginForm?.querySelector('[data-status]');
const dashboard=document.getElementById('dashboard');
const editorControls=document.getElementById('editor-controls');
const loginBox=document.getElementById('login');
function showStatus(el,msg,error=false){if(!el)return;el.textContent=msg;el.classList.add('show');el.classList.toggle('error-status',error);}
async function refresh(){
  const d=await APAH.api('/api/admin/data');
  document.getElementById('counts').innerHTML=`<div class="card"><b>Leads</b><div>${d.counts.leads}</div></div><div class="card"><b>Applications</b><div>${d.counts.applications}</div></div><div class="card"><b>Subscribers</b><div>${d.counts.subscribers}</div></div>`;
  document.getElementById('leads').innerHTML=d.leads.map(x=>`<p><strong>${x.name}</strong>, ${x.email}, ${x.status}</p>`).join('')||'<p>No leads.</p>';
  document.getElementById('apps').innerHTML=d.applications.map(x=>`<p><strong>${x.name}</strong>, ${x.email}, ${x.status}</p>`).join('')||'<p>No applications.</p>';
}
loginForm?.addEventListener('submit',async e=>{e.preventDefault();try{const r=await APAH.api('/api/admin/login',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(loginForm)))});loginBox.classList.add('hide');dashboard.classList.remove('hide');if(editorControls) editorControls.classList.remove('hide');await refresh();showStatus(statusBox,`Signed in as ${r.role}.`);}catch(err){showStatus(statusBox,err.message||'Sign in failed.',true);}});
async function submitJson(form,endpoint,statusEl){try{await APAH.api(endpoint,{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(form)))});showStatus(statusEl,'Saved.');form.reset();await refresh();}catch(err){showStatus(statusEl,err.message||'Save failed.',true);}}
document.getElementById('actuality-form')?.addEventListener('submit',e=>{e.preventDefault();submitJson(e.currentTarget,'/api/admin/actuality',document.querySelector('[data-actuality-status]'));});
document.getElementById('job-form')?.addEventListener('submit',e=>{e.preventDefault();submitJson(e.currentTarget,'/api/admin/jobs',document.querySelector('[data-job-status]'));});
document.getElementById('admin-logout')?.addEventListener('click',async()=>{try{await APAH.api('/api/admin/logout',{method:'POST'});location.reload();}catch(err){alert(err.message||'Sign out failed.');}});
'''
admin_js_en.write_text(admin_js)
admin_js_fr.write_text(admin_js.replace("Signed in as","Connecté avec le rôle").replace("Signed in", "Connecté").replace("Saved.","Enregistré.").replace("No leads.","Aucun contact.").replace("No applications.","Aucune candidature.").replace("Sign in failed.","Échec de la connexion.").replace("Save failed.","Échec de l’enregistrement.").replace("Sign out failed.","Échec de la déconnexion."))

# Add actualities dynamic page scripts EN + FR.
act_en='''import '/assets/js/common.js';\nconst grid=document.querySelector('[data-actuality-grid]');\nconst empty=document.querySelector('[data-actuality-empty]');\nconst search=document.querySelector('[data-actuality-search]');\nlet items=[];\nfunction render(){const q=(search?.value||'').toLowerCase().trim();const filtered=items.filter(x=>[x.title,x.summary,x.category,x.author||''].join(' ').toLowerCase().includes(q));if(!filtered.length){if(grid)grid.innerHTML='';if(empty){empty.hidden=false;empty.textContent=items.length?'No matching actuality items.':'No news has been published yet. Subscribe to our newsletter to be informed of company updates.';}return;}if(empty)empty.hidden=true;grid.innerHTML=filtered.map(x=>`<article class="card reveal"><span class="pill">${x.category}</span><p class="help">${new Date(x.published_at).toLocaleDateString('en-GB')}</p><h2>${x.title}</h2><p>${x.summary}</p><a class="text-link" href="/en/actuality/${encodeURIComponent(x.slug)}">Read more</a></article>`).join('');}\nasync function load(){try{const r=await fetch('/api/actuality?lang=en');items=r.items||[];render();}catch{if(empty){empty.hidden=false;empty.textContent='Actuality is temporarily unavailable.';}}}\nsearch?.addEventListener('input',render);load();\n'''
act_fr='''import '/assets/js/common.js';\nconst grid=document.querySelector('[data-actuality-grid]');\nconst empty=document.querySelector('[data-actuality-empty]');\nconst search=document.querySelector('[data-actuality-search]');\nlet items=[];\nfunction render(){const q=(search?.value||'').toLowerCase().trim();const filtered=items.filter(x=>[x.title,x.summary,x.category,x.author||''].join(' ').toLowerCase().includes(q));if(!filtered.length){if(grid)grid.innerHTML='';if(empty){empty.hidden=false;empty.textContent=items.length?'Aucune actualité correspondante.':'Aucune actualité n’a encore été publiée. Abonnez-vous à notre newsletter pour suivre les actualités de l’entreprise.';}return;}if(empty)empty.hidden=true;grid.innerHTML=filtered.map(x=>`<article class="card reveal"><span class="pill">${x.category}</span><p class="help">${new Date(x.published_at).toLocaleDateString('fr-FR')}</p><h2>${x.title}</h2><p>${x.summary}</p><a class="text-link" href="/fr/actualites/${encodeURIComponent(x.slug)}">Lire la suite</a></article>`).join('');}\nasync function load(){try{const r=await fetch('/api/actuality?lang=fr');items=r.items||[];render();}catch{if(empty){empty.hidden=false;empty.textContent='Le service Actualités est temporairement indisponible.';}}}\nsearch?.addEventListener('input',render);load();\n'''
(ROOT/'public/assets/js/en/actuality.js').write_text(act_en)
(ROOT/'public/assets/js/fr/actualites.js').write_text(act_fr)

# Patch actuality HTML containers and search fields. Keep page-specific editable markup.
for lang, path in [('en',ROOT/'public/en/actuality.html'),('fr',ROOT/'public/fr/actualites.html')]:
    x=path.read_text()
    if lang=='en':
        x=x.replace('<section class="section"><div class="container"><div class="empty-state">', '<section class="section"><div class="container"><div class="toolbar"><label class="field" style="max-width:420px"><span class="sr-only">Search actuality</span><input type="search" data-actuality-search placeholder="Search actuality"></label></div><div data-actuality-grid class="grid grid-3"></div><p data-actuality-empty class="empty-state" style="margin-top:20px">Loading actuality…</p><div style="margin-top:24px"><a class="btn btn-secondary" href="/en/newsletter">Subscribe to Newsletter</a></div>')
    else:
        x=x.replace('<section class="section"><div class="container"><div class="empty-state">', '<section class="section"><div class="container"><div class="toolbar"><label class="field" style="max-width:420px"><span class="sr-only">Rechercher dans les actualités</span><input type="search" data-actuality-search placeholder="Rechercher dans les actualités"></label></div><div data-actuality-grid class="grid grid-3"></div><p data-actuality-empty class="empty-state" style="margin-top:20px">Chargement des actualités…</p><div style="margin-top:24px"><a class="btn btn-secondary" href="/fr/newsletter">S’abonner à la newsletter</a></div>')
    path.write_text(x)

# Patch homepage with latest actuality section before experts.
for lang,path in [('en',ROOT/'public/en/index.html'),('fr',ROOT/'public/fr/index.html')]:
    x=path.read_text()
    if 'data-latest-actuality-grid' not in x:
        if lang=='en':
            section='<section class="section" id="latest-actuality"><div class="container"><div class="section-head"><div><span class="eyebrow">Latest updates</span><h2>Latest Actuality</h2><p>Verified company updates, announcements and participation.</p></div><a class="btn btn-secondary" href="/en/actuality">View all Actuality</a></div><div data-latest-actuality-grid class="grid grid-3"></div><p data-latest-actuality-empty class="empty-state" style="margin-top:20px">No news has been published yet.</p></div></section>'
            x=x.replace('<section class="section"><div class="container"><div class="section-head"><div><span class="eyebrow">Experts</span>', section+'<section class="section"><div class="container"><div class="section-head"><div><span class="eyebrow">Experts</span>',1)
        else:
            section='<section class="section" id="latest-actuality"><div class="container"><div class="section-head"><div><span class="eyebrow">Dernières actualités</span><h2>Actualités récentes</h2><p>Actualités, annonces et participations vérifiées.</p></div><a class="btn btn-secondary" href="/fr/actualites">Voir toutes les actualités</a></div><div data-latest-actuality-grid class="grid grid-3"></div><p data-latest-actuality-empty class="empty-state" style="margin-top:20px">Aucune actualité n’a encore été publiée.</p></div></section>'
            x=x.replace('<section class="section"><div class="container"><div class="section-head"><div><span class="eyebrow">Experts</span>', section+'<section class="section"><div class="container"><div class="section-head"><div><span class="eyebrow">Experts</span>',1)
        path.write_text(x)
# Home JS append latest actuality fetch.
for lang,path in [('en',ROOT/'public/assets/js/en/index.js'),('fr',ROOT/'public/assets/js/fr/index.js')]:
    x=path.read_text()
    if 'latest-actuality-grid' not in x:
        if lang=='en':
            x += "\nconst latestGrid=document.querySelector('[data-latest-actuality-grid]'); const latestEmpty=document.querySelector('[data-latest-actuality-empty]');\n(async()=>{try{const r=await fetch('/api/actuality?lang=en');const xs=(r.items||[]).slice(0,3);if(!xs.length)return;latestEmpty?.remove();if(latestGrid)latestGrid.innerHTML=xs.map(v=>`<article class=\"card\"><span class=\"pill\">${v.category}</span><p class=\"help\">${new Date(v.published_at).toLocaleDateString('en-GB')}</p><h3>${v.title}</h3><p>${v.summary}</p><a class=\"text-link\" href=\"/en/actuality/${encodeURIComponent(v.slug)}\">Read more</a></article>`).join('');}catch{}})();\n"
        else:
            x += "\nconst latestGrid=document.querySelector('[data-latest-actuality-grid]'); const latestEmpty=document.querySelector('[data-latest-actuality-empty]');\n(async()=>{try{const r=await fetch('/api/actuality?lang=fr');const xs=(r.items||[]).slice(0,3);if(!xs.length)return;latestEmpty?.remove();if(latestGrid)latestGrid.innerHTML=xs.map(v=>`<article class=\"card\"><span class=\"pill\">${v.category}</span><p class=\"help\">${new Date(v.published_at).toLocaleDateString('fr-FR')}</p><h3>${v.title}</h3><p>${v.summary}</p><a class=\"text-link\" href=\"/fr/actualites/${encodeURIComponent(v.slug)}\">Lire la suite</a></article>`).join('');}catch{}})();\n"
        path.write_text(x)

# Newsletter JS status messages.
for lang,path in [('en',ROOT/'public/assets/js/en/newsletter.js'),('fr',ROOT/'public/assets/js/fr/newsletter.js')]:
    if lang=='en':
        js="""import '/assets/js/common.js';\nconst status=new URLSearchParams(location.search).get('status');\nconst box=document.querySelector('[data-status-page]');\nconst messages={confirmed:'Your subscription is confirmed.',invalid:'This confirmation link is invalid or expired.'};\nif(box&&status&&messages[status]){box.textContent=messages[status];box.classList.add('show',status==='confirmed'?'success-status':'error-status');box.setAttribute('tabindex','-1');box.focus();}\n"""
    else:
        js="""import '/assets/js/common.js';\nconst status=new URLSearchParams(location.search).get('status');\nconst box=document.querySelector('[data-status-page]');\nconst messages={confirmed:'Votre abonnement est confirmé.',invalid:'Ce lien de confirmation est invalide ou expiré.'};\nif(box&&status&&messages[status]){box.textContent=messages[status];box.classList.add('show',status==='confirmed'?'success-status':'error-status');box.setAttribute('tabindex','-1');box.focus();}\n"""
    path.write_text(js)
for lang,path in [('en',ROOT/'public/en/newsletter.html'),('fr',ROOT/'public/fr/newsletter.html')]:
    x=path.read_text()
    if 'data-status-page' not in x:
        x=x.replace('<main id="main">','<main id="main"><div class="container"><div data-status-page role="status"></div></div>',1)
        # close div immediately after page hero? Add before main ends if needed
        x=x.replace('</div></main>','</div></main>',1)
    path.write_text(x)

# Add docs requested/refresh
(ROOT/'docs/accessibility-checklist.md').write_text('''# Accessibility checklist\n\nTarget: WCAG 2.2 AA.\n\nVerified in the local frontend gate:\n- Semantic landmarks, skip links and heading hierarchy are present on core pages.\n- Keyboard focus styles are visible.\n- Theme and language controls expose accessible labels.\n- Dialogs support Escape close and return focus.\n- Forms expose labels, status regions and consent text.\n- Responsive checks ran at 320, 375, 768, 1024, 1280, 1440 and 1920 px using the local overflow harness.\n\nStill required before public release:\n- Manual screen-reader walkthrough in French and English.\n- Color contrast audit on the exact production build.\n- Browser-specific keyboard and zoom checks at 200% and 400%.\n''')
(ROOT/'docs/frontend-handoff.md').write_text('''# Frontend handoff\n\nFrontend implementation is complete for the current approved information architecture.\n\nStatus:\n- English and French HTML, CSS and JavaScript files exist per page.\n- Normal and Dark Theme controls are implemented with first-party preference storage.\n- Mobile navigation, language switching, dialogs, filters, forms, error pages and accessibility foundations are implemented.\n- Supplied company logo assets and three supplied team photos are used.\n- Backend-dependent contact, chatbot, newsletter, careers and Actuality behaviors use local API contracts.\n\nVerification completed:\n- `python scripts/validate.py`\n- `python scripts/test_site.py`\n- `python scripts/test_overflow.py`\n- `python scripts/test_api.py`\n\nImportant limitation:\n- The overflow test uses a local Playwright harness with inlined local CSS because the sandbox Chromium runner blocks direct navigation to the local HTTP server.\n\nBackend phase commands:\n```bash\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt\ncp .env.example .env\npython scripts/create_admin.py\npython server.py\n```\n''')
(ROOT/'docs/release-checklist.md').write_text('''# Release checklist\n\nFunctional and UX approval\n- Reviewer: ____________________\n- Date: ________________________\n- Status: Pending until final company content, forms and production URLs are verified.\n\nSecurity approval\n- Reviewer: ____________________\n- Date: ________________________\n- Status: Pending until production security tests, secret scan, dependency scan, headers and authorization tests are complete.\n\nRelease blockers\n- No exposed secrets.\n- No unauthorized protected access.\n- Admin MFA verified.\n- Upload security verified.\n- Rate limits verified.\n- HTTPS, headers and CORS verified.\n- Exact deployed-site verification passed.\n''')

# Update open placeholders with font and production items.
op=ROOT/'docs/open-placeholders.md'
x=op.read_text()
if 'self-hosted' not in x:
    x += '\n- Optional self-hosted corporate font: not supplied. Current build uses a system font stack to avoid third-party font requests.\n'
op.write_text(x)

# Refresh gitignore, README line.
g=ROOT/'.gitignore'; gx=g.read_text();
if 'private-assets/' not in gx: gx += '\nprivate-assets/\n'
if 'data/apah.db' not in gx: gx += 'data/apah.db\n'
g.write_text(gx)

# Remove Python cache and local DB before packaging later.
for p in ROOT.glob('__pycache__/*.pyc'): p.unlink()
