"""SAMS public website, owner CMS and private CRM starter.
DO NOT put real client records in this prototype without a professional security/privacy review.
"""
import os
import re
import secrets
import hashlib
import hmac
import time
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
import base64
import struct
import io
import qrcode
from cryptography.fernet import Fernet
import requests
import jwt
from jwt import PyJWKClient
from collections import defaultdict, deque
from datetime import datetime, timezone, date
from pathlib import Path
from contextlib import contextmanager

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, String, Integer, Boolean, DateTime, ForeignKey, Text, select, desc, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
ENV = os.getenv('APP_ENV', 'development')
AUTH_MODE = os.getenv('AUTH_MODE', 'microsoft')
TENANT_ID = os.getenv('ENTRA_TENANT_ID', '')
CLIENT_ID = os.getenv('ENTRA_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('ENTRA_CLIENT_SECRET', '')
PUBLIC_ORIGIN = os.getenv('PUBLIC_ORIGIN', 'http://localhost:8000').rstrip('/')
CONTACT_INBOX = 'sam.support.admin@gmail.com'
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_APP_PASSWORD', '')
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '465'))
MAIL_READY = bool(SMTP_USER and SMTP_PASSWORD)
# Explicit go-live switches. Defaults are OFF so unfinished legal/configuration work cannot
# accidentally open intake or real case data merely because SMTP or Entra was configured.
FORMS_APPROVED = os.getenv('SAMS_PUBLIC_FORMS_APPROVED', 'no') == 'yes'
PRIVACY_NOTICE_APPROVED = os.getenv('SAMS_PRIVACY_NOTICE_APPROVED', 'no') == 'yes'
FORM_READY = MAIL_READY and FORMS_APPROVED and PRIVACY_NOTICE_APPROVED and ENV != 'pilot'
CLIENT_RECORDS_ENABLED = os.getenv('SAMS_CRM_RECORDS_ENABLED', 'no') == 'yes' and ENV != 'pilot'
MS_READY = bool(TENANT_ID and CLIENT_ID and CLIENT_SECRET)
BOOTSTRAP_TOKEN_SHA256 = os.getenv('BOOTSTRAP_TOKEN_SHA256', '').lower()
MFA_KEY = os.getenv('MFA_ENCRYPTION_KEY', '')
if ENV == 'pilot' and AUTH_MODE != 'totp':
    raise RuntimeError('Free pilot must use mandatory authenticator-code login.')
if ENV == 'pilot' and not re.fullmatch(r'[a-f0-9]{64}', BOOTSTRAP_TOKEN_SHA256):
    raise RuntimeError('Set BOOTSTRAP_TOKEN_SHA256 to the SHA-256 of a private one-time setup code.')
if ENV == 'production' and AUTH_MODE != 'microsoft':
    raise RuntimeError('Production requires Microsoft Entra sign-in.')
if ENV == 'production' and not MS_READY:
    raise RuntimeError('Production requires ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET.')
if ENV == 'production' and not MAIL_READY:
    raise RuntimeError('Production requires SMTP_USER and SMTP_APP_PASSWORD before publishing forms.')
if ENV not in ('production','pilot') and not os.getenv('SESSION_SECRET'):
    dev_secret_file = ROOT/'.development_secret'
    if not dev_secret_file.exists():
        dev_secret_file.write_text(secrets.token_urlsafe(64),encoding='utf-8')
        dev_secret_file.chmod(0o600)
    SECRET=dev_secret_file.read_text(encoding='utf-8').strip()
else:
    SECRET=os.getenv('SESSION_SECRET','')
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{ROOT / "sams_dev.sqlite3"}')
if ENV in ('production','pilot'):
    if len(os.getenv('SESSION_SECRET', '')) < 48:
        raise RuntimeError('Set a long SESSION_SECRET before production use.')
    if not DATABASE_URL.startswith('postgresql'):
        raise RuntimeError('Production requires an independently secured PostgreSQL database.')
    if not os.getenv('PUBLIC_ORIGIN', '').startswith('https://'):
        raise RuntimeError('Set HTTPS PUBLIC_ORIGIN in production.')
    if ENV == 'pilot':
        if len(MFA_KEY) != 44:
            raise RuntimeError('A valid 44-character Fernet MFA_ENCRYPTION_KEY is required.')
        try: Fernet(MFA_KEY.encode())
        except Exception as exc: raise RuntimeError('Invalid MFA_ENCRYPTION_KEY.') from exc
    if ENV == 'production' and os.getenv('SECURITY_REVIEW_APPROVED') != 'yes':
        raise RuntimeError('Production must not start until an independent privacy/security review has been completed and SECURITY_REVIEW_APPROVED=yes is explicitly set.')
    if ENV == 'production' and CLIENT_RECORDS_ENABLED and os.getenv('SAMS_CASE_MANAGEMENT_SIGNOFF') != 'yes':
        raise RuntimeError('Confidential case records require SAMS_CASE_MANAGEMENT_SIGNOFF=yes after independent validation.')
if not MFA_KEY:
    MFA_KEY = base64.urlsafe_b64encode(hashlib.sha256(SECRET.encode('utf-8')).digest()).decode('ascii')
MFA_CIPHER = Fernet(MFA_KEY.encode())
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite:') else {}, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

def now(): return datetime.now(timezone.utc).replace(tzinfo=None)

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(140))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300), default="")
    entra_oid: Mapped[str | None] = mapped_column(String(80),unique=True,nullable=True,index=True)
    role: Mapped[str] = mapped_column(String(20), default='staff')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    # Website owners are not automatically clinicians or intake workers.
    intake_access: Mapped[bool] = mapped_column(Boolean, default=False)
    support_access: Mapped[bool] = mapped_column(Boolean, default=False)
    supervisor_access: Mapped[bool] = mapped_column(Boolean, default=False)
    # Simple server-side invalidation counter (in addition to the signed cookie).
    session_version: Mapped[int] = mapped_column(Integer, default=0)
    totp_ciphertext: Mapped[str] = mapped_column(String(512), default='')
    totp_pending_ciphertext: Mapped[str] = mapped_column(String(512), default='')
    totp_last_step: Mapped[int] = mapped_column(Integer, default=-1)
    totp_failed: Mapped[int] = mapped_column(Integer, default=0)
    totp_locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Content(Base):
    __tablename__ = 'site_content'
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    eyebrow: Mapped[str] = mapped_column(String(160), default='')
    heading: Mapped[str] = mapped_column(String(220))
    lead: Mapped[str] = mapped_column(Text, default='')
    body: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Service(Base):
    __tablename__ = 'services'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(180))
    icon: Mapped[str] = mapped_column(String(30), default='heart')
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default='planning')
    published: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

class Update(Base):
    __tablename__ = 'updates'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Client(Base):
    __tablename__ = 'crm_clients'
    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(180))
    preferred_contact: Mapped[str] = mapped_column(String(180), default='')
    support_area: Mapped[str] = mapped_column(String(90), default='General support')
    status: Mapped[str] = mapped_column(String(24), default='new')
    assigned_to: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class CaseNote(Base):
    __tablename__ = 'crm_case_notes'
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('crm_clients.id'), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(30), default='contact')
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Task(Base):
    __tablename__ = 'crm_tasks'
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('crm_clients.id'), index=True)
    assigned_to: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    title: Mapped[str] = mapped_column(String(200))
    due_date: Mapped[str] = mapped_column(String(10), default='')
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Enquiry(Base):
    __tablename__ = 'website_enquiries'
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(140))
    email: Mapped[str] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(35), default='')
    message: Mapped[str] = mapped_column(Text, default='')
    delivery_status: Mapped[str] = mapped_column(String(20), default='pending')
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Audit(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    reference: Mapped[str] = mapped_column(String(160), default='')
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=now)

Base.metadata.create_all(engine)

SEED_CONTENT = [
 ('home','Homepage','SUPPORT · CULTURE · CONNECTION','No shame. No judgement. Just mob supporting mob.','SAMS is an Aboriginal-led community initiative working to create a place of connection, understanding and practical support for people affected by alcohol and other drugs.','We believe support should start with listening, dignity and choice.'),
 ('about','About SAMS','OUR STORY','Built by mob, for mob.','Substance Affected Mob Support (SAMS) is an Aboriginal-led community initiative being developed to strengthen connection and support for people affected by alcohol and other drugs.','Our direction is guided by lived experience, community voices, cultural respect and the belief that everyone deserves to be heard. We are establishing our programs and processes carefully and will share confirmed opportunities as they become available.\n\nPeople do not need to be abstinent to be treated with dignity. Our approach is welcoming, non-judgemental and focused on a person’s own goals.'),
 ('services','What we do','OUR APPROACH','Practical support. Stronger connections.','We are developing community-led ways to listen, connect people with appropriate services and strengthen peer relationships.','Our program ideas are being developed. Items marked “In development” are not yet available as operational SAMS services.'),
 ('programs','Programs','WHAT’S BEING DEVELOPED','Programs shaped by community.','From yarning circles to peer connections, SAMS is exploring ways to create culturally safe spaces and practical pathways forward.','Program details, dates and eligibility will only be advertised once the SAMS team has confirmed them.'),
 ('support','Get support','YOU ARE NOT ALONE','There is support available now.','You deserve to speak with someone who listens. SAMS is still establishing its own support processes, but existing specialist services can help today.','If someone is in immediate danger, call 000. SAMS is not an emergency or crisis service.'),
 ('involved','Get involved','BE PART OF IT','Help build something meaningful.','SAMS is a community-led initiative, and there are many ways to contribute as we grow.','Opportunities may include volunteering, sharing community feedback, offering professional skills, forming partnerships, or helping shape future programs. New opportunities will be announced once confirmed.'),
 ('contact','Contact','REACH OUT','Start a conversation.','SAMS is finalising its public contact channels and intake process. We will publish verified details here when they are ready.','Please do not send sensitive personal, health or case information through social media or unverified contact channels.'),
 ('privacy','Privacy','OUR COMMITMENT','Your story deserves care.','We know that trust and confidentiality are essential to community support.','SAMS is developing formal privacy, consent, recordkeeping, retention, access-control, and incident-management processes. This page is not a final privacy policy. Do not use this prototype to submit personal or health information. Before collecting client data, SAMS must publish an approved privacy policy and verify applicable Victorian and Australian legal obligations.'),
]
SEED_SERVICES = [
 ('Peer mentoring','People with lived experience offering connection, encouragement and peer understanding, with training and appropriate boundaries.','planning',1,'people'),
 ('Community yarning circles','A welcoming space for community connection and conversation. Meeting formats and availability are being planned.','planning',2,'chat'),
 ('Support navigation','Helping people understand options and connecting them with the appropriate external services when pathways are established.','planning',3,'compass'),
 ('Wellbeing and community activities','Connection-focused activities designed with community input to reduce isolation and build belonging.','planning',4,'sun'),
]

def seed():
    with Session.begin() as db:
        for slug, name, eyebrow, heading, lead, body in SEED_CONTENT:
            if not db.scalar(select(Content).where(Content.slug == slug)):
                db.add(Content(slug=slug,name=name,eyebrow=eyebrow,heading=heading,lead=lead,body=body))
        if not db.scalar(select(Service.id).limit(1)):
            for title,summary,status,order,icon in SEED_SERVICES:
                db.add(Service(title=title, summary=summary,status=status,sort_order=order,icon=icon))
seed()

# Passwords are derived with scrypt and independent 16-byte salts. Never store plaintext passwords.
def encode_password(password: str) -> str:
    if len(password) < 12: raise ValueError('Password must have at least 12 characters.')
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode(), salt=salt,n=2**14,r=8,p=1,dklen=32)
    return f'scrypt${salt.hex()}${derived.hex()}'

def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm,salt_hex,hash_hex=encoded.split('$')
        if algorithm!='scrypt': return False
        calc=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt_hex),n=2**14,r=8,p=1,dklen=32)
        return hmac.compare_digest(calc,bytes.fromhex(hash_hex))
    except (ValueError, TypeError): return False

def encrypt_mfa(secret: str) -> str:
    return MFA_CIPHER.encrypt(secret.encode('ascii')).decode('ascii')

def decrypt_mfa(ciphertext: str) -> str:
    return MFA_CIPHER.decrypt(ciphertext.encode('ascii')).decode('ascii')

def totp_value(secret: str, step: int) -> str:
    key = base64.b32decode(secret, casefold=True)
    digest = hmac.new(key, struct.pack('>Q', step), hashlib.sha1).digest()
    offset = digest[-1] & 15
    number = struct.unpack('>I', digest[offset:offset+4])[0] & 0x7fffffff
    return f'{number % 1000000:06d}'

def matched_totp_step(secret: str, supplied: str, last_step: int = -1, *, at: float | None = None):
    if not re.fullmatch(r'[0-9]{6}', supplied or ''):
        return None
    now_step = int((at if at is not None else time.time()) // 30)
    for step in (now_step, now_step-1, now_step+1):
        if step > last_step and hmac.compare_digest(totp_value(secret, step), supplied):
            return step
    return None

def totp_setup_uri(secret: str, username: str) -> str:
    # Never call an external QR-code generator: the shared secret must remain private.
    from urllib.parse import quote
    return 'otpauth://totp/' + quote(f'SAMS:{username}',safe='') + '?' + urlencode({'secret':secret,'issuer':'SAMS','algorithm':'SHA1','digits':6,'period':30})

def totp_qr_data(uri: str) -> str:
    img=qrcode.make(uri)
    stream=io.BytesIO();img.save(stream,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode('ascii')

app = FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=SECRET,https_only=ENV in ('production','pilot'),same_site='lax',max_age=28800,session_cookie='sams_session')
app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
templates=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=select_autoescape(['html','xml']))
templates.globals.update(year=datetime.now().year)

# Default cache prevention on private pages; security headers on every response.
@app.middleware('http')
async def security_headers(request: Request, call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    if request.url.path.startswith(('/owner','/staff','/login','/account','/auth/','/enquiry')):
        response.headers['Cache-Control']='no-store'
        response.headers['X-Robots-Tag']='noindex, nofollow'
    if ENV in ('production','pilot'): response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    return response

@contextmanager
def open_db():
    with Session() as db:
        yield db

def current_user(request, db):
    uid=request.session.get('uid')
    user=db.get(User,uid) if isinstance(uid,int) else None
    if not user or not user.active: return None
    if request.session.get('sv') != user.session_version: return None
    if ENV in ('production','pilot') and (time.time() - request.session.get('auth_at', 0) > 3600):
        return None
    return user

def require_user(request,db,owner=False):
    user=current_user(request,db)
    if user is None: raise HTTPException(303,headers={'Location':'/login'})
    if AUTH_MODE in ('development-password','totp') and user.must_change_password and request.url.path not in ('/account/password','/logout'):
        raise HTTPException(303,headers={'Location':'/account/password'})
    if owner and user.role!='owner': raise HTTPException(403,'Owners only')
    if request.url.path.startswith('/staff') and not (user.intake_access or user.support_access or user.supervisor_access):
        raise HTTPException(403, 'No CRM permissions')
    return user

def csrf(request):
    token=request.session.get('csrf')
    if not token:
        token=secrets.token_urlsafe(32)
        request.session['csrf']=token
    return token

def verify_csrf(request, posted):
    token=request.session.get('csrf','')
    if not token or not hmac.compare_digest(token,str(posted)):
        raise HTTPException(403,'Security check failed; refresh the page and try again.')

def render(request,name,*,db=None,user=None,status=200,**context):
    own=db is None
    if own: db=Session()
    try:
        if user is None: user=current_user(request,db)
        data=dict(request=request,user=user,csrf=csrf(request),mail_ready=FORM_READY,auth_mode=AUTH_MODE,**context)
        result=templates.get_template(name).render(**data)
        return HTMLResponse(result,status_code=status)
    finally:
        if own: db.close()

def go(path): return RedirectResponse(path,status_code=303)

def log(db,user,action,reference=''):
    db.add(Audit(actor_id=user.id if user else None,action=action,reference=reference[:160]))

def clean(value,limit): return str(value or '').strip()[:limit]

def can_access(user,client):
    # Site administrator status alone never grants unrestricted access to cases.
    return bool(user.supervisor_access or (user.support_access and client.assigned_to == user.id))

def require_case_authority(user):
    if not (user.support_access or user.supervisor_access):
        raise HTTPException(403, 'You do not have case-record permission')

def require_record_collection():
    if not CLIENT_RECORDS_ENABLED:
        raise HTTPException(503, 'Case records are disabled until a formal privacy/security go-live decision.')

def allowed_client(db,user,client_id):
    client=db.get(Client,client_id)
    if client is None: raise HTTPException(404)
    if not can_access(user,client): raise HTTPException(403,'You do not have access to this record')
    return client

# ===== Public site =====
@app.get('/',response_class=HTMLResponse)
def home(request:Request):
    with open_db() as db:
        content=db.scalar(select(Content).where(Content.slug=='home'))
        services=db.scalars(select(Service).where(Service.published==True).order_by(Service.sort_order,Service.id).limit(3)).all()
        updates=db.scalars(select(Update).where(Update.published==True).order_by(desc(Update.created_at)).limit(2)).all()
        return render(request,'home.html',db=db,content=content,services=services,updates=updates,active='home')

@app.get('/about',response_class=HTMLResponse)
def about(request:Request): return public_page(request,'about')
@app.get('/what-we-do',response_class=HTMLResponse)
def services(request:Request): return public_page(request,'services')
@app.get('/programs',response_class=HTMLResponse)
def programs(request:Request): return public_page(request,'programs')
@app.get('/get-support',response_class=HTMLResponse)
def support(request:Request): return public_page(request,'support')
@app.get('/get-involved',response_class=HTMLResponse)
def involved(request:Request): return public_page(request,'involved')
@app.get('/contact',response_class=HTMLResponse)
def contact(request:Request): return public_page(request,'contact')
@app.get('/privacy',response_class=HTMLResponse)
def privacy(request:Request): return public_page(request,'privacy')

def public_page(request,slug):
    with open_db() as db:
        content=db.scalar(select(Content).where(Content.slug==slug))
        services=db.scalars(select(Service).where(Service.published==True).order_by(Service.sort_order,Service.id)).all() if slug in ('services','programs') else []
        return render(request,'page.html',db=db,content=content,services=services,active=slug)

@app.get('/updates',response_class=HTMLResponse)
def updates(request:Request):
    with open_db() as db:
        posts=db.scalars(select(Update).where(Update.published==True).order_by(desc(Update.created_at))).all()
        return render(request,'updates.html',db=db,posts=posts,active='updates')

# ===== Microsoft Entra ID sign-in: OpenID Connect authorisation code, PKCE =====
# Users must be given explicit SAMS.* app roles in SAMS's Microsoft Entra tenant.
# Microsoft Authenticator / MFA is ENFORCED BY THE TENANT, not by application UI.
ENTRA_ISSUER=f'https://login.microsoftonline.com/{TENANT_ID}/v2.0' if TENANT_ID else ''

def microsoft_ready(): return AUTH_MODE=='microsoft' and MS_READY

@app.get('/login',response_class=HTMLResponse)
def login_page(request:Request):
    with open_db() as db:
        user=current_user(request,db)
        if user:return go('/owner' if user.role=='owner' else '/workspace')
        return render(request,'login.html',db=db,active='',error=None,entra_ready=microsoft_ready())

# A one-time owner bootstrap is available only while the external database has no team users.
@app.get('/setup',response_class=HTMLResponse)
def owner_setup_page(request: Request):
    if ENV != 'pilot' or AUTH_MODE != 'totp': raise HTTPException(404)
    with open_db() as db:
        if db.scalar(select(User.id).limit(1)):raise HTTPException(404)
    return render(request,'setup_pilot.html',error=None)

@app.post('/setup')
def owner_setup(request: Request,token:str=Form(''),username:str=Form(''),full_name:str=Form(''),password:str=Form(''),csrf_token:str=Form('')):
    if ENV != 'pilot' or AUTH_MODE != 'totp': raise HTTPException(404)
    verify_csrf(request,csrf_token)
    if not hmac.compare_digest(hashlib.sha256(token.encode('utf-8')).hexdigest(),BOOTSTRAP_TOKEN_SHA256):
        return render(request,'setup_pilot.html',error='Setup code could not be verified.',status=403)
    username=username.strip().lower()
    if not re.fullmatch(r'[a-z0-9_.-]{3,80}',username) or len(full_name.strip()) < 2:
        return render(request,'setup_pilot.html',error='Enter a valid username and full name.',status=400)
    try: hashed=encode_password(password)
    except ValueError as exc: return render(request,'setup_pilot.html',error=str(exc),status=400)
    with open_db() as db:
        # One-time setup only. Unique lock is the owner username plus database guard.
        if db.scalar(select(User.id).limit(1)):raise HTTPException(404)
        obj=User(full_name=clean(full_name,140),username=username,password_hash=hashed,role='owner',active=True,must_change_password=False)
        db.add(obj);db.flush()
        log(db,obj,'initial_owner_created')
        db.commit()
        request.session.clear();request.session.update({'pre_uid':obj.id,'pre_sv':obj.session_version,'pre_auth_at':int(time.time())})
        csrf(request)
    return go('/auth/otp')


def get_preauth_user(request: Request, db):
    if AUTH_MODE != 'totp':raise HTTPException(404)
    ident=request.session.get('pre_uid')
    if not isinstance(ident,int) or time.time()-request.session.get('pre_auth_at',0)>600:
        request.session.clear();raise HTTPException(303,headers={'Location':'/login'})
    user=db.get(User,ident)
    if not user or not user.active or request.session.get('pre_sv')!=user.session_version:
        request.session.clear();raise HTTPException(303,headers={'Location':'/login'})
    return user

@app.get('/auth/otp',response_class=HTMLResponse)
def otp_page(request: Request):
    with open_db() as db:
        user=get_preauth_user(request,db)
        setup=not bool(user.totp_ciphertext)
        uri=None;qr=None;manual=None
        if setup:
            if not user.totp_pending_ciphertext:
                # Random 160-bit shared secret created on server and encrypted at rest.
                raw=base64.b32encode(secrets.token_bytes(20)).decode('ascii')
                user.totp_pending_ciphertext=encrypt_mfa(raw)
                db.commit()
            manual=decrypt_mfa(user.totp_pending_ciphertext)
            uri=totp_setup_uri(manual,user.username)
            qr=totp_qr_data(uri)
        return render(request,'totp_pilot.html',display_name=user.full_name,setup=setup,manual=manual,qr=qr,error=None)

@app.post('/auth/otp')
def otp_verify(request: Request,code:str=Form(''),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        user=get_preauth_user(request,db)
        setup=not bool(user.totp_ciphertext)
        if user.totp_locked_until and now()<user.totp_locked_until:
            return render(request,'totp_pilot.html',display_name=user.full_name,setup=False,manual=None,qr=None,error='Too many attempts. Please try again later.',status=429)
        if setup and not user.totp_pending_ciphertext:
            return go('/auth/otp')
        secret=decrypt_mfa(user.totp_pending_ciphertext if setup else user.totp_ciphertext)
        step=matched_totp_step(secret,code,user.totp_last_step)
        if step is None:
            user.totp_failed+=1
            if user.totp_failed>=5:
                from datetime import timedelta
                user.totp_locked_until=now()+timedelta(minutes=15)
                log(db,user,'mfa_rate_limited')
            db.commit()
            uri=totp_setup_uri(secret,user.username) if setup else None
            return render(request,'totp_pilot.html',display_name=user.full_name,setup=setup,manual=secret if setup else None,qr=totp_qr_data(uri) if uri else None,error='The code was incorrect or already used.',status=401)
        if setup:
            user.totp_ciphertext=user.totp_pending_ciphertext;user.totp_pending_ciphertext=''
            log(db,user,'mfa_enrolled')
        user.totp_last_step=step;user.totp_failed=0;user.totp_locked_until=None
        user.session_version+=1
        log(db,user,'mfa_verified_login')
        db.commit()
        request.session.clear();request.session.update({'uid':user.id,'sv':user.session_version,'auth_at':int(time.time())})
        csrf(request)
        if user.must_change_password:return go('/account/password')
        return go('/owner' if user.role=='owner' else '/workspace')

@app.get('/auth/microsoft')
def entra_login(request:Request):
    if not microsoft_ready():raise HTTPException(503,'Microsoft Entra is not configured.')
    request.session.clear()
    state=secrets.token_urlsafe(32)
    nonce=secrets.token_urlsafe(32)
    verifier=secrets.token_urlsafe(64)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    request.session.update({'oidc_state':state,'oidc_nonce':nonce,'oidc_verifier':verifier,'oidc_started':int(time.time())})
    query={'client_id':CLIENT_ID,'response_type':'code','redirect_uri':PUBLIC_ORIGIN+'/auth/callback',
           'response_mode':'query','scope':'openid profile email','state':state,'nonce':nonce,
           'code_challenge':challenge,'code_challenge_method':'S256'}
    return RedirectResponse(f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize?{urlencode(query)}',status_code=303)

@app.get('/auth/callback')
def entra_callback(request:Request,code:str='',state:str='',error:str=''):
    if not microsoft_ready():raise HTTPException(503,'Microsoft Entra is not configured.')
    expected=request.session.get('oidc_state')
    started=request.session.get('oidc_started',0)
    if error or not code or not state or not expected or not hmac.compare_digest(state,expected) or time.time()-started>600:
        request.session.clear();raise HTTPException(401,'Microsoft sign-in could not be verified.')
    nonce=request.session['oidc_nonce'];verifier=request.session['oidc_verifier']
    try:
        response=requests.post(f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token',
            data={'client_id':CLIENT_ID,'client_secret':CLIENT_SECRET,'grant_type':'authorization_code',
                  'code':code,'redirect_uri':PUBLIC_ORIGIN+'/auth/callback','code_verifier':verifier},timeout=12)
        response.raise_for_status()
        id_token=response.json()['id_token']
        signing_key=PyJWKClient(f'https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys').get_signing_key_from_jwt(id_token).key
        claims=jwt.decode(id_token,signing_key,algorithms=['RS256'],audience=CLIENT_ID,issuer=ENTRA_ISSUER,
                          options={'require':['exp','iat','iss','aud','sub','nonce','tid','oid']})
    except Exception:
        request.session.clear();raise HTTPException(401,'Microsoft sign-in could not be verified.')
    if claims.get('tid')!=TENANT_ID or not hmac.compare_digest(str(claims.get('nonce','')),nonce):
        request.session.clear();raise HTTPException(401,'Invalid Microsoft sign-in claims.')
    roles=claims.get('roles') or []
    if not isinstance(roles,list):roles=[]
    role=('owner' if 'SAMS.Owner' in roles else 'intake' if 'SAMS.Intake' in roles else
          'staff' if ('SAMS.Support' in roles or 'SAMS.CaseSupervisor' in roles) else None)
    intake_access='SAMS.Intake' in roles
    support_access='SAMS.Support' in roles
    supervisor_access='SAMS.CaseSupervisor' in roles
    if not role:
        request.session.clear();raise HTTPException(403,'A SAMS Microsoft Entra app role is required.')
    oid=str(claims['oid'])
    full_name=clean(claims.get('name') or 'SAMS team member',140)
    with open_db() as db:
        user=db.scalar(select(User).where(User.entra_oid==oid))
        if user and not user.active:
            request.session.clear();raise HTTPException(403,'This SAMS account has been suspended.')
        if not user:
            user=User(entra_oid=oid,username='ms_'+oid.lower(),password_hash='',
                      full_name=full_name,role=role,active=True,must_change_password=False,
                      intake_access=intake_access,support_access=support_access,supervisor_access=supervisor_access)
            db.add(user);db.flush()
        else:
            user.role=role;user.full_name=full_name;user.must_change_password=False
            user.intake_access=intake_access;user.support_access=support_access
            user.supervisor_access=supervisor_access
            user.session_version += 1  # invalidate older browser sessions at new sign-in
        log(db,user,'microsoft_signin');db.commit()
        request.session.clear();request.session.update({'uid':user.id,'sv':user.session_version,'auth_at':int(time.time())});csrf(request)
    return go('/owner' if role=='owner' else '/workspace')

# Only for offline developer testing. Never enabled in production or behind public server.
failed_logins=defaultdict(deque)
@app.post('/login')
def local_login(request:Request,username:str=Form(''),password:str=Form(''),csrf_token:str=Form('')):
    if ENV=='production' or AUTH_MODE not in ('development-password','totp'):raise HTTPException(404)
    verify_csrf(request,csrf_token)
    username=username.strip().lower()
    key=f'{request.client.host if request.client else "unknown"}:{username}'
    attempts=failed_logins[key]
    while attempts and attempts[0]<time.monotonic()-900:attempts.popleft()
    if len(attempts)>=6:return render(request,'login.html',error='Too many sign-in attempts.',entra_ready=False,status=429)
    with open_db() as db:
        user=db.scalar(select(User).where(User.username==username,User.active==True))
        if not user or not verify_password(password,user.password_hash):
            attempts.append(time.monotonic())
            return render(request,'login.html',db=db,error='Incorrect login details.',entra_ready=False,status=401)
        failed_logins.pop(key,None)
        if AUTH_MODE == 'totp':
            request.session.clear()
            request.session.update({'pre_uid':user.id,'pre_sv':user.session_version,'pre_auth_at':int(time.time())})
            csrf(request)
            return go('/auth/otp')
        request.session.clear();request.session.update({'uid':user.id,'sv':user.session_version,'auth_at':int(time.time())});csrf(request)
        log(db,user,'dev_login');db.commit()
        return go('/account/password' if user.must_change_password else ('/owner' if user.role=='owner' else '/staff'))

@app.post('/logout')
def logout(request:Request,csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        user=current_user(request,db)
        if user:
            user.session_version += 1
            log(db,user,'session_logged_out')
            db.commit()
    request.session.clear()
    return go('/')

@app.get('/account/password',response_class=HTMLResponse)
def password_page(request:Request):
    if AUTH_MODE not in ('development-password','totp'):raise HTTPException(404)
    with open_db() as db:
        user=current_user(request,db)
        if not user:return go('/login')
        return render(request,'password.html',db=db,user=user,error=None,success=None)

@app.post('/account/password')
def password_update(request:Request,old_password:str=Form(''),new_password:str=Form(''),csrf_token:str=Form('')):
    if AUTH_MODE not in ('development-password','totp'):raise HTTPException(404)
    verify_csrf(request,csrf_token)
    with open_db() as db:
        user=current_user(request,db)
        if not user:return go('/login')
        if not verify_password(old_password,user.password_hash):
            return render(request,'password.html',db=db,user=user,error='Incorrect password.',success=None,status=400)
        try:hashed=encode_password(new_password)
        except ValueError as exc:return render(request,'password.html',db=db,user=user,error=str(exc),success=None,status=400)
        user.password_hash=hashed;user.must_change_password=False
        log(db,user,'password_updated');db.commit()
        return go('/owner' if user.role=='owner' else '/workspace')

# ===== Owner CMS =====
@app.get('/workspace',response_class=HTMLResponse)
def workspace_page(request: Request):
    with open_db() as db:
        person=require_user(request,db)
        return render(request,'workspace_pilot.html',db=db,user=person,area='workspace')

@app.get('/owner',response_class=HTMLResponse)
def owner_dashboard(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        stats=dict(pages=db.query(Content).count(),services=db.query(Service).count(),posts=db.query(Update).count(),team=db.query(User).count())
        recent=db.scalars(select(Audit).order_by(desc(Audit.occurred_at)).limit(8)).all()
        return render(request,'owner.html',db=db,user=u,stats=stats,recent=recent,area='dashboard')

@app.get('/owner/content',response_class=HTMLResponse)
def content_list(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        return render(request,'content_list.html',db=db,user=u,items=db.scalars(select(Content).order_by(Content.id)).all(),area='content')

@app.get('/owner/content/{slug}',response_class=HTMLResponse)
def content_edit(request:Request,slug:str):
    with open_db() as db:
        u=require_user(request,db,True);obj=db.scalar(select(Content).where(Content.slug==slug))
        if not obj: raise HTTPException(404)
        return render(request,'content_edit.html',db=db,user=u,obj=obj,area='content')

@app.post('/owner/content/{slug}')
def content_save(request:Request,slug:str,eyebrow:str=Form(''),heading:str=Form(''),lead:str=Form(''),body:str=Form(''),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db,True);obj=db.scalar(select(Content).where(Content.slug==slug))
        if not obj: raise HTTPException(404)
        obj.eyebrow=clean(eyebrow,160);obj.heading=clean(heading,220) or obj.heading
        obj.lead=clean(lead,2000);obj.body=clean(body,12000);obj.updated_at=now()
        log(db,u,'content_updated',slug);db.commit();return go('/owner/content')

@app.get('/owner/services',response_class=HTMLResponse)
def owner_services(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        return render(request,'collection.html',db=db,user=u,area='services',heading='Services & programs',subheading='Control what appears on the public programs pages.',items=db.scalars(select(Service).order_by(Service.sort_order,Service.id)).all(),kind='services')

@app.get('/owner/services/new',response_class=HTMLResponse)
def service_new(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        return render(request,'service_edit.html',db=db,user=u,obj=None,area='services')

@app.get('/owner/services/{item_id}',response_class=HTMLResponse)
def service_edit(request:Request,item_id:int):
    with open_db() as db:
        u=require_user(request,db,True);obj=db.get(Service,item_id)
        if not obj: raise HTTPException(404)
        return render(request,'service_edit.html',db=db,user=u,obj=obj,area='services')

@app.post('/owner/services/save')
def service_save(request:Request,item_id:int=Form(0),title:str=Form(''),summary:str=Form(''),status:str=Form('planning'),published:str=Form(''),sort_order:int=Form(0),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db,True)
        if not clean(title,180): raise HTTPException(400,'Title is required')
        obj=db.get(Service,item_id) if item_id else Service()
        if item_id and not obj: raise HTTPException(404)
        obj.title=clean(title,180);obj.summary=clean(summary,2500)
        obj.status=status if status in ('planning','active','paused') else 'planning'
        obj.published=(published=='on');obj.sort_order=max(0,min(sort_order,9999))
        if not item_id:db.add(obj)
        db.flush();log(db,u,'service_saved',str(obj.id));db.commit()
        return go('/owner/services')

@app.post('/owner/services/{item_id}/delete')
def service_delete(request:Request,item_id:int,csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db,True);obj=db.get(Service,item_id)
        if not obj: raise HTTPException(404)
        db.delete(obj);log(db,u,'service_deleted',str(item_id));db.commit()
        return go('/owner/services')

@app.get('/owner/updates',response_class=HTMLResponse)
def owner_updates(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        return render(request,'collection.html',db=db,user=u,area='updates',heading='News & updates',subheading='Publish news when the details have been confirmed.',items=db.scalars(select(Update).order_by(desc(Update.created_at))).all(),kind='updates')

@app.get('/owner/updates/new',response_class=HTMLResponse)
def update_new(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        return render(request,'update_edit.html',db=db,user=u,obj=None,area='updates')

@app.get('/owner/updates/{item_id}',response_class=HTMLResponse)
def update_edit(request:Request,item_id:int):
    with open_db() as db:
        u=require_user(request,db,True);obj=db.get(Update,item_id)
        if not obj: raise HTTPException(404)
        return render(request,'update_edit.html',db=db,user=u,obj=obj,area='updates')

@app.post('/owner/updates/save')
def update_save(request:Request,item_id:int=Form(0),title:str=Form(''),body:str=Form(''),published:str=Form(''),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db,True)
        if not clean(title,200):raise HTTPException(400,'Title is required')
        obj=db.get(Update,item_id) if item_id else Update(created_at=now())
        if item_id and not obj:raise HTTPException(404)
        obj.title=clean(title,200);obj.body=clean(body,10000);obj.published=published=='on'
        if not item_id:db.add(obj)
        db.flush();log(db,u,'update_saved',str(obj.id));db.commit();return go('/owner/updates')

@app.post('/owner/updates/{item_id}/delete')
def update_delete(request:Request,item_id:int,csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db,True);obj=db.get(Update,item_id)
        if not obj:raise HTTPException(404)
        db.delete(obj);log(db,u,'update_deleted',str(item_id));db.commit();return go('/owner/updates')

@app.get('/owner/team',response_class=HTMLResponse)
def team(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        return render(request,'team.html',db=db,user=u,people=db.scalars(select(User).order_by(User.id)).all(),area='team')

@app.get('/owner/team/new',response_class=HTMLResponse)
def team_new(request:Request):
    if AUTH_MODE=='microsoft':raise HTTPException(403,'Use Microsoft Entra to provision accounts.')
    with open_db() as db:
        u=require_user(request,db,True)
        return render(request,'team_edit.html',db=db,user=u,obj=None,area='team',error=None)

@app.get('/owner/team/{item_id}',response_class=HTMLResponse)
def team_edit(request:Request,item_id:int):
    if AUTH_MODE=='microsoft':raise HTTPException(403,'Use Microsoft Entra to manage accounts.')
    with open_db() as db:
        u=require_user(request,db,True);obj=db.get(User,item_id)
        if not obj: raise HTTPException(404)
        return render(request,'team_edit.html',db=db,user=u,obj=obj,area='team',error=None)

@app.post('/owner/team/save')
def team_save(request:Request,item_id:int=Form(0),full_name:str=Form(''),username:str=Form(''),role:str=Form('staff'),new_password:str=Form(''),active:str=Form(''),csrf_token:str=Form('')):
    if AUTH_MODE=='microsoft':raise HTTPException(403,'Use Microsoft Entra to manage accounts.')
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db,True)
        obj=db.get(User,item_id) if item_id else User()
        if item_id and not obj:raise HTTPException(404)
        username=clean(username.lower(),80)
        err=None
        if not re.fullmatch(r'[a-z0-9_.-]{3,80}',username):err='Username must be 3+ letters/numbers and may include . - _'
        elif db.scalar(select(User).where(User.username==username,User.id!=item_id)):err='This username already exists.'
        elif len(clean(full_name,140))<2:err='Enter a full name.'
        elif not item_id and len(new_password)<12:err='New accounts need a temporary password of at least 12 characters.'
        elif new_password and len(new_password)<12:err='Password must contain at least 12 characters.'
        if err:return render(request,'team_edit.html',db=db,user=u,obj=obj if item_id else None,area='team',error=err,status=400)
        obj.full_name=clean(full_name,140);obj.username=username
        obj.role=role if role in ('owner','staff','intake') else 'staff'
        # Development identities are NOT authorised for case information by default.
        # In a deployed Microsoft tenant, permissions are assigned via SAMS.* app roles.
        obj.active=active=='on'
        if item_id==u.id and (not obj.active or obj.role!='owner'):
            raise HTTPException(400,'You cannot remove your own owner access.')
        if new_password:
            obj.password_hash=encode_password(new_password);obj.must_change_password=True
            obj.totp_ciphertext='';obj.totp_pending_ciphertext='';obj.totp_last_step=-1
            obj.session_version += 1
        if not item_id:db.add(obj)
        db.flush();log(db,u,'team_saved',str(obj.id));db.commit();return go('/owner/team')

@app.get('/owner/audit',response_class=HTMLResponse)
def audit(request:Request):
    with open_db() as db:
        u=require_user(request,db,True)
        events=db.execute(select(Audit,User.full_name).outerjoin(User,Audit.actor_id==User.id).order_by(desc(Audit.occurred_at)).limit(120)).all()
        return render(request,'audit.html',db=db,user=u,events=events,area='audit')

# ===== Staff CRM =====
@app.get('/staff',response_class=HTMLResponse)
def staff_dashboard(request:Request):
    with open_db() as db:
        u=require_user(request,db)
        accessible=select(Client).order_by(desc(Client.updated_at))
        if not u.supervisor_access:accessible=accessible.where(Client.assigned_to==u.id)
        cases=db.scalars(accessible.limit(5)).all() if CLIENT_RECORDS_ENABLED and (u.support_access or u.supervisor_access) else []
        tasks=db.scalars(select(Task).where(Task.assigned_to==u.id,Task.done==False).order_by(Task.due_date,Task.id).limit(6)).all() if CLIENT_RECORDS_ENABLED and (u.support_access or u.supervisor_access) else []
        return render(request,'staff.html',db=db,user=u,cases=cases,tasks=tasks,area='staff',records_enabled=CLIENT_RECORDS_ENABLED)

@app.get('/staff/clients',response_class=HTMLResponse)
def crm_list(request:Request,q:str=''):
    with open_db() as db:
        u=require_user(request,db)
        require_record_collection();require_case_authority(u)
        stmt=select(Client).order_by(desc(Client.updated_at))
        if not u.supervisor_access:stmt=stmt.where(Client.assigned_to==u.id)
        if q.strip():stmt=stmt.where(Client.display_name.ilike('%'+q.strip()[:100]+'%'))
        rows=db.scalars(stmt.limit(200)).all()
        people={p.id:p.full_name for p in db.scalars(select(User)).all()}
        return render(request,'crm_list.html',db=db,user=u,clients=rows,people=people,q=q,area='clients')

@app.get('/staff/clients/new',response_class=HTMLResponse)
def crm_new(request:Request):
    with open_db() as db:
        u=require_user(request,db)
        require_record_collection();require_case_authority(u)
        people=db.scalars(select(User).where(User.active==True,User.support_access==True).order_by(User.full_name)).all()
        return render(request,'crm_edit.html',db=db,user=u,obj=None,people=people,area='clients')

@app.get('/staff/clients/{client_id}/edit',response_class=HTMLResponse)
def crm_edit(request:Request,client_id:int):
    with open_db() as db:
        u=require_user(request,db)
        require_record_collection();require_case_authority(u)
        obj=allowed_client(db,u,client_id)
        people=db.scalars(select(User).where(User.active==True,User.support_access==True).order_by(User.full_name)).all()
        return render(request,'crm_edit.html',db=db,user=u,obj=obj,people=people,area='clients')

@app.post('/staff/clients/save')
def crm_save(request:Request,client_id:int=Form(0),display_name:str=Form(''),preferred_contact:str=Form(''),support_area:str=Form('General support'),status:str=Form('new'),assigned_to:int=Form(0),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db)
        require_record_collection();require_case_authority(u)
        if not clean(display_name,180):raise HTTPException(400,'Display name required')
        obj=allowed_client(db,u,client_id) if client_id else Client(created_by=u.id,created_at=now())
        obj.display_name=clean(display_name,180);obj.preferred_contact=clean(preferred_contact,180)
        obj.support_area=clean(support_area,90)
        obj.status=status if status in ('new','active','referred','closed') else 'new'
        if u.supervisor_access and assigned_to:
            person=db.get(User,assigned_to)
            if not person or not person.active or not person.support_access:raise HTTPException(400,'Choose an active support worker')
            obj.assigned_to=assigned_to
        elif not client_id:obj.assigned_to=u.id
        obj.updated_at=now()
        if not client_id:db.add(obj)
        db.flush();log(db,u,'client_saved',str(obj.id));db.commit()
        return go('/staff/clients/'+str(obj.id))

@app.get('/staff/clients/{client_id}',response_class=HTMLResponse)
def crm_detail(request:Request,client_id:int):
    with open_db() as db:
        u=require_user(request,db);require_record_collection();require_case_authority(u);obj=allowed_client(db,u,client_id)
        notes=db.execute(select(CaseNote,User.full_name).join(User,User.id==CaseNote.author_id).where(CaseNote.client_id==client_id).order_by(desc(CaseNote.created_at))).all()
        tasks=db.scalars(select(Task).where(Task.client_id==client_id).order_by(Task.done,Task.due_date,Task.id)).all()
        assigned=db.get(User,obj.assigned_to)
        log(db,u,'client_viewed',str(client_id));db.commit()
        return render(request,'crm_detail.html',db=db,user=u,obj=obj,notes=notes,tasks=tasks,assigned=assigned,area='clients')

@app.post('/staff/clients/{client_id}/notes')
def note_add(request:Request,client_id:int,kind:str=Form('contact'),detail:str=Form(''),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db);require_record_collection();require_case_authority(u);obj=allowed_client(db,u,client_id)
        if not clean(detail,3500):raise HTTPException(400,'Note required')
        kind=kind if kind in ('contact','referral','followup') else 'contact'
        db.add(CaseNote(client_id=obj.id,author_id=u.id,kind=kind,detail=clean(detail,3500)))
        obj.updated_at=now();log(db,u,'note_added',str(client_id));db.commit()
        return go('/staff/clients/'+str(client_id))

@app.post('/staff/clients/{client_id}/tasks')
def task_add(request:Request,client_id:int,title:str=Form(''),due_date:str=Form(''),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db);require_record_collection();require_case_authority(u);obj=allowed_client(db,u,client_id)
        if not clean(title,200):raise HTTPException(400,'Task title required')
        due=clean(due_date,10)
        if due:
            try:date.fromisoformat(due)
            except ValueError:raise HTTPException(400,'Invalid due date')
        db.add(Task(client_id=obj.id,assigned_to=obj.assigned_to,title=clean(title,200),due_date=due))
        log(db,u,'task_added',str(client_id));db.commit();return go('/staff/clients/'+str(client_id))

@app.get('/staff/tasks',response_class=HTMLResponse)
def task_list(request:Request):
    with open_db() as db:
        u=require_user(request,db)
        require_record_collection();require_case_authority(u)
        stmt=select(Task,Client.display_name).join(Client,Task.client_id==Client.id)
        if not u.supervisor_access:stmt=stmt.where(Client.assigned_to==u.id,Task.assigned_to==u.id)
        rows=db.execute(stmt.order_by(Task.done,Task.due_date,Task.id)).all()
        return render(request,'task_list.html',db=db,user=u,rows=rows,area='tasks')

@app.post('/staff/tasks/{task_id}/toggle')
def task_toggle(request:Request,task_id:int,csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db)
        task=db.get(Task,task_id)
        if not task:raise HTTPException(404)
        require_record_collection();require_case_authority(u)
        allowed_client(db,u,task.client_id)
        if not u.supervisor_access and task.assigned_to!=u.id:raise HTTPException(403)
        task.done=not task.done;log(db,u,'task_toggled',str(task_id));db.commit()
        return go('/staff/tasks')

# ===== Public forms, inbound inbox routing =====
# Support enquiries deliberately collect minimal non-clinical information.
ENQUIRY_KINDS = {'general':'General enquiry','volunteer':'Volunteering','partnership':'Partnership','support':'Request for contact'}
submission_times=defaultdict(deque)

def smtp_deliver(enquiry:Enquiry):
    if not MAIL_READY: raise RuntimeError('Outgoing Gmail is not configured')
    msg=EmailMessage()
    msg['From']=SMTP_USER
    msg['To']=CONTACT_INBOX
    msg['Subject']=f'SAMS website: {ENQUIRY_KINDS[enquiry.kind]} #{enquiry.id}'
    # NOTIFY-ONLY FOR EVERY FORM. Public visitors might put health or child-protection
    # information in *any* free text field, regardless of the form label.
    msg.set_content(
        f'New {ENQUIRY_KINDS[enquiry.kind].lower()} received (internal reference #{enquiry.id}).\n'
        'Open the restricted SAMS enquiry inbox with your authorised Microsoft account.\n'
        'No visitor names, email addresses, telephone numbers or form messages are in this alert.'
    )
    with smtplib.SMTP_SSL(SMTP_HOST,SMTP_PORT,timeout=15) as smtp:
        smtp.login(SMTP_USER,SMTP_PASSWORD)
        smtp.send_message(msg)

@app.post('/enquiry')
def submit_enquiry(request:Request,kind:str=Form('general'),name:str=Form(''),email:str=Form(''),phone:str=Form(''),message:str=Form(''),consent:str=Form(''),website:str=Form(''),csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    if not FORM_READY:
        raise HTTPException(503,'SAMS enquiries are not yet available. Please use the support numbers on this site if you need assistance.')
    if website: return go('/enquiry/received')  # bot field
    ip=request.client.host if request.client else 'unknown'
    attempts=submission_times[ip]
    while attempts and attempts[0]<time.monotonic()-3600:attempts.popleft()
    if len(attempts)>=5:raise HTTPException(429,'Too many requests. Please try later.')
    if kind not in ENQUIRY_KINDS:raise HTTPException(400,'Unknown form type')
    name=clean(name,140);email=clean(email,254);phone=clean(phone,35);message=clean(message,1800)
    if len(name)<2 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or consent!='yes':
        raise HTTPException(400,'Name, valid email and privacy acknowledgement are required.')
    if kind!='support' and not message: raise HTTPException(400,'Please write a brief message.')
    if kind=='support': message=''  # do not solicit/store health disclosures in public forms
    attempts.append(time.monotonic())
    with open_db() as db:
        item=Enquiry(kind=kind,name=name,email=email,phone=phone,message=message)
        db.add(item);db.commit();db.refresh(item)
        enquiry_id=item.id
        try:
            smtp_deliver(item)
            item.delivery_status='sent'
        except (OSError,smtplib.SMTPException,RuntimeError) as exc:
            item.delivery_status='failed'
            db.commit()
            # retained for restricted staff follow-up, never pretend the email was sent
            raise HTTPException(503,'We could not deliver this enquiry right now. Please contact SAMS by another confirmed channel if urgent.')
        db.commit()
    return go('/enquiry/received')

@app.get('/enquiry/received',response_class=HTMLResponse)
def enquiry_received(request:Request):
    return render(request,'enquiry_received.html',active='contact')

@app.get('/staff/enquiries',response_class=HTMLResponse)
def enquiries_dashboard(request:Request):
    with open_db() as db:
        u=require_user(request,db)
        if not u.intake_access:raise HTTPException(403,'Intake access required')
        rows=db.scalars(select(Enquiry).order_by(desc(Enquiry.created_at)).limit(200)).all()
        log(db,u,'enquiries_list_viewed');db.commit()
        return render(request,'enquiries.html',db=db,user=u,rows=rows,area='enquiries')

@app.get('/staff/enquiries/{enquiry_id}',response_class=HTMLResponse)
def enquiry_detail(request:Request,enquiry_id:int):
    with open_db() as db:
        u=require_user(request,db)
        if not u.intake_access:raise HTTPException(403)
        item=db.get(Enquiry,enquiry_id)
        if not item:raise HTTPException(404)
        log(db,u,'enquiry_viewed',str(enquiry_id));db.commit()
        return render(request,'enquiry_detail.html',db=db,user=u,item=item,area='enquiries')

@app.post('/staff/enquiries/{enquiry_id}/resend')
def resend_enquiry(request:Request,enquiry_id:int,csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        user=require_user(request,db)
        if not user.intake_access:raise HTTPException(403)
        entry=db.get(Enquiry,enquiry_id)
        if not entry:raise HTTPException(404)
        if entry.delivery_status=='sent':return go(f'/staff/enquiries/{enquiry_id}')
        if not FORM_READY:raise HTTPException(503,'Email or approved privacy configuration is not ready')
        try:smtp_deliver(entry)
        except (OSError,smtplib.SMTPException,RuntimeError):
            log(db,user,'enquiry_resend_failed',str(enquiry_id));db.commit()
            raise HTTPException(503,'Email service unavailable; please retry later.')
        entry.delivery_status='sent'
        log(db,user,'enquiry_resend_succeeded',str(enquiry_id));db.commit()
        return go(f'/staff/enquiries/{enquiry_id}')

@app.post('/staff/enquiries/{enquiry_id}/handled')
def enquiry_handled(request:Request,enquiry_id:int,csrf_token:str=Form('')):
    verify_csrf(request,csrf_token)
    with open_db() as db:
        u=require_user(request,db)
        if not u.intake_access:raise HTTPException(403)
        item=db.get(Enquiry,enquiry_id)
        if not item:raise HTTPException(404)
        item.handled=not item.handled
        log(db,u,'enquiry_handled',str(enquiry_id));db.commit()
        return go(f'/staff/enquiries/{enquiry_id}')

@app.exception_handler(403)
def forbidden(request,exc):
    return render(request,'error.html',status=403,title='Access denied',message='You do not have permission to open this page.')

@app.exception_handler(404)
def missing(request,exc):
    return render(request,'error.html',status=404,title='Page not found',message='The page you requested does not exist.')
