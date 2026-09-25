from pathlib import Path
import os, tempfile, shutil, sys
from fastapi.testclient import TestClient

os.environ['APP_ENV']='development'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    server.DB_PATH=root/'apah.db'
    server.PRIVATE=root/'private'; server.UPLOADS=server.PRIVATE/'uploads'; server.UPLOADS.mkdir(parents=True)
    server.init_db()
    secret='JBSWY3DPEHPK3PXP'
    con=server.db()
    password='TestPassword!123'
    cur=con.execute('INSERT INTO users(email,password_hash,totp_secret,role,created_at) VALUES(?,?,?,?,?)',('admin@apah.com',server.hash_password(password),'JBSWY3DPEHPK3PXP','Admin',server.now_iso()))
    con.commit(); con.close()
    client=TestClient(server.app)
    h=client.get('/api/health'); assert h.status_code==200 and h.json()['status']=='ok'
    assert 'Content-Security-Policy' in h.headers
    assert client.post('/api/contact',json={'name':'Test Person','email':'test@example.com','message':'Hello','consent':'yes','website':'bot'}).status_code==400
    r=client.post('/api/contact',headers={'referer':'http://testserver/fr/contact'},json={'name':'Test Person','email':'test@example.com','message':'Bonjour','consent':'no'}); assert r.status_code==400 and 'consent' in r.json()['detail'].lower()
    # Admin login with current TOTP
    otp=server.totp_code(secret)
    r=client.post('/api/admin/login',json={'email':'admin@apah.com','password':password,'otp':otp}); assert r.status_code==200, r.text
    csrf=client.get('/api/csrf').json()['token']; assert csrf
    headers={'X-CSRF-Token':csrf}
    r=client.post('/api/admin/actuality',headers=headers,json={'slug':'test-update','title_en':'Test Update','title_fr':'Mise à jour de test','summary_en':'Summary','summary_fr':'Résumé','body_en':'<p>Body</p>','body_fr':'<p>Corps</p>','category':'Announcement','author':'APAH','status':'Published'}); assert r.status_code==200,r.text
    assert client.get('/api/actuality?lang=en').json()['items'][0]['slug']=='test-update'
    r=client.get('/en/actuality/test-update'); assert r.status_code==200 and 'Switch to English' not in r.text and 'Subscribe to Newsletter' in r.text and 'data-language-switch' in r.text
    r=client.get('/fr/actualites/test-update'); assert r.status_code==200 and 'Mise à jour de test' in r.text and 'data-language-switch' in r.text
    sm=client.get('/sitemap.xml').text; assert '/en/actuality/test-update' in sm and '/fr/actualites/test-update' in sm
    csrf=client.get('/api/csrf').json()['token']
    r=client.post('/api/admin/jobs',headers={'X-CSRF-Token':csrf},json={'slug':'test-role','title_en':'Test Role','title_fr':'Poste de test','department':'Operations','location':'Kinshasa','contract_type':'Full-time','summary_en':'Summary','summary_fr':'Résumé','description_en':'Description','description_fr':'Description','status':'Published'}); assert r.status_code==200,r.text
    assert client.get('/api/jobs?lang=en').json()['jobs'][0]['slug']=='test-role'
    print('BACKEND TEST OK')
