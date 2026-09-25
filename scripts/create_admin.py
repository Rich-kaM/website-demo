from pathlib import Path
import sys, secrets, base64, hashlib, sqlite3
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server import db, hash_password

def new_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
email=input('Admin email: ').strip().lower()
password=input('Admin password, 10+ characters: ')
if len(password)<10: raise SystemExit('Password must be at least 10 characters.')
secret=new_totp_secret()
con=db()
con.execute('INSERT INTO users(email,password_hash,totp_secret,role,created_at) VALUES(?,?,?,?,datetime("now")) ON CONFLICT(email) DO UPDATE SET password_hash=excluded.password_hash,totp_secret=excluded.totp_secret,role="Admin",active=1',(email,hash_password(password),secret))
con.commit();con.close()
print('\nAdmin created.')
print('Email:',email)
print('TOTP secret:',secret)
print('Add the secret to an authenticator app. The website accepts standard 6-digit TOTP codes.')
