from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3, os, secrets, json

ROOT=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(ROOT,'instance','incident_management.db')
UPLOADS=os.path.join(ROOT,'static','uploads')
os.makedirs(os.path.dirname(DB),exist_ok=True); os.makedirs(UPLOADS,exist_ok=True)
app=Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH']=5*1024*1024
TOKENS={}
ROLES=['PROFESSOR','ANALISTA','COORDENADOR','ADMINISTRATIVO']

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init_db():
 with db() as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,login TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
  CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,birth_date TEXT NOT NULL,image_url TEXT,active INTEGER NOT NULL DEFAULT 1);
  CREATE TABLE IF NOT EXISTS schoolclasses(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,shift TEXT NOT NULL,year INTEGER NOT NULL,semester TEXT NOT NULL,canceled INTEGER NOT NULL DEFAULT 0);
  CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL REFERENCES students(id),class_id INTEGER NOT NULL REFERENCES schoolclasses(id),UNIQUE(student_id,class_id));
  CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL);
  CREATE TABLE IF NOT EXISTS types(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category_id INTEGER NOT NULL REFERENCES categories(id),UNIQUE(name,category_id));
  CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY AUTOINCREMENT,class_id INTEGER NOT NULL REFERENCES schoolclasses(id),student_id INTEGER NOT NULL REFERENCES students(id),register_date TEXT NOT NULL,category TEXT NOT NULL,type TEXT NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'AGUARDANDO',update_date TEXT,deleted INTEGER NOT NULL DEFAULT 0,user_id INTEGER NOT NULL REFERENCES users(id));
  ''')
  if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0:
   for name,login,role in [('Professor Demo','professor','PROFESSOR'),('Analista Demo','analista','ANALISTA'),('Coordenador Demo','coordenador','COORDENADOR'),('Administrativo Demo','administrativo','ADMINISTRATIVO')]:
    c.execute('INSERT INTO users(name,login,password,role) VALUES(?,?,?,?)',(name,login,generate_password_hash('1234'),role))
  for cat,types in [('DISCIPLINAR',['INDISCIPLINA','ATRASO']),('PEDAGOGICA',['RENDIMENTO']),('ADMINISTRATIVA',['OUTROS'])]:
   c.execute('INSERT OR IGNORE INTO categories(name) VALUES(?)',(cat,))
   cid=c.execute('SELECT id FROM categories WHERE name=?',(cat,)).fetchone()['id']
   for t in types: c.execute('INSERT OR IGNORE INTO types(name,category_id) VALUES(?,?)',(t,cid))
init_db()

def current_user():
 token=request.headers.get('Authorization','').replace('Bearer ','').strip()
 return TOKENS.get(token)
def auth(fn):
 @wraps(fn)
 def wrapped(*a,**kw):
  u=current_user()
  if not u:return jsonify(error='Autenticacao necessaria.'),401
  request.user=u
  return fn(*a,**kw)
 return wrapped
def roles(*allowed):
 def dec(fn):
  @wraps(fn)
  @auth
  def wrapped(*a,**kw):
   if request.user['role'] not in allowed:return jsonify(error='Acesso negado para este perfil.'),403
   return fn(*a,**kw)
  return wrapped
 return dec
def data(): return request.get_json(silent=True) or {}
def item(row): return dict(row) if row else None
def paginated(items):
 try: page=max(0,int(request.args.get('page',0))); size=min(100,max(1,int(request.args.get('size',20))))
 except ValueError: page,size=0,20
 total=len(items); return jsonify(content=items[page*size:(page+1)*size],totalElements=total,number=page,totalPages=max(1,(total+size-1)//size),first=page==0,last=(page+1)*size>=total)
def normdate(v):
 value=str(v or '').strip()
 # Accept ISO datetime-local values and the legacy DD/MM/YYYY format from older screens.
 if len(value)>=10 and value[4:5]=='-' and value[7:8]=='-': return value.replace('T',' ')
 import re
 m=re.match(r'^(\d{2})/(\d{2})/(\d{4})(?:\s*-\s*(\d{2}:\d{2}))?$',value)
 if m:
  return f'{m.group(3)}-{m.group(2)}-{m.group(1)} {m.group(4) or "00:00"}'
 return value
def incident_dict(c,r):
 student=c.execute('SELECT name FROM students WHERE id=?',(r['student_id'],)).fetchone(); cl=c.execute('SELECT name FROM schoolclasses WHERE id=?',(r['class_id'],)).fetchone()
 user=c.execute('SELECT name,login FROM users WHERE id=?',(r['user_id'],)).fetchone()
 return {'id':r['id'],'idSchoolClass':r['class_id'],'idStudent':r['student_id'],'schoolClassName':cl['name'] if cl else '-', 'studentName':student['name'] if student else '-', 'registerDate':r['register_date'],'category':r['category'],'type':r['type'],'description':r['description'],'status':r['status'],'updateDate':r['update_date'],'deleted':bool(r['deleted']),'userId':r['user_id'],'userName':user['name'] if user else '-'}
def get_incident(c, ident): return c.execute('SELECT * FROM incidents WHERE id=? AND deleted=0',(ident,)).fetchone()
def check_incident_permission(c, row, editing=False):
 role=request.user['role']
 if role=='PROFESSOR': return row is None or row['user_id']==request.user['id']
 return role in ('COORDENADOR','ANALISTA') and not editing

@app.get('/')
@app.get('/index.html')
def root(): return send_from_directory(ROOT,'index.html')
@app.get('/templates/<path:filename>')
def template_files(filename):
    return send_from_directory(os.path.join(ROOT, 'templates'), filename)

@app.get('/health')
def health(): return jsonify(status='ok',database='sqlite')
@app.post('/login')
def login():
 d=data(); login=str(d.get('login','')).strip(); password=str(d.get('password',''))
 with db() as c: u=c.execute('SELECT * FROM users WHERE login=? AND active=1',(login,)).fetchone()
 if not u or not check_password_hash(u['password'],password): return jsonify(error='Usuario ou senha invalidos.'),401
 token=secrets.token_urlsafe(32); TOKENS[token]={'id':u['id'],'name':u['name'],'login':u['login'],'role':u['role']}
 return jsonify(tokenJWT=token,id=u['id'],login=u['login'],name=u['name'],role=u['role'])
@app.post('/register')
def register():
 d=data(); name=str(d.get('name','')).strip(); login=str(d.get('login','')).strip(); password=str(d.get('password',''))
 if not name or not login or len(password)<4:
  return jsonify(error='Informe nome, login e senha com pelo menos 4 caracteres.'),400
 try:
  with db() as c:
   cur=c.execute('INSERT INTO users(name,login,password,role) VALUES(?,?,?,?)',(name,login,generate_password_hash(password),'PROFESSOR'))
   return jsonify(id=cur.lastrowid,name=name,login=login,role='PROFESSOR',message='Cadastro realizado! Agora entre com seu login e senha.'),201
 except sqlite3.IntegrityError:
  return jsonify(error='Este login ja esta cadastrado.'),409

@app.post('/logout')
@auth
def logout():
 token=request.headers.get('Authorization','').replace('Bearer ',''); TOKENS.pop(token,None); return jsonify(ok=True)

@app.get('/students')
@roles('ADMINISTRATIVO','COORDENADOR','ANALISTA','PROFESSOR')
def students_list():
 class_id=request.args.get('classId')
 with db() as c:
  sql='SELECT DISTINCT s.* FROM students s'; args=[]
  if class_id:
   sql+=' JOIN enrollments e ON e.student_id=s.id'; sql+=' WHERE s.active=1 AND e.class_id=?'; args.append(class_id)
  else:
   sql+=' WHERE s.active=1'
  sql+=' ORDER BY s.id'
  arr=[{'id':r['id'],'name':r['name'],'birthDate':r['birth_date'],'imageUrl':r['image_url'],'foto':r['image_url'],'active':bool(r['active'])} for r in c.execute(sql,args)]
 return paginated(arr)
@app.post('/students')
@roles('ADMINISTRATIVO')
def student_create():
 d=data(); name=str(d.get('name','')).strip(); birth=normdate(d.get('birthDate'))
 if not name or not birth:return jsonify(error='Nome e data de nascimento sao obrigatorios.'),400
 with db() as c:
  cur=c.execute('INSERT INTO students(name,birth_date) VALUES(?,?)',(name,birth)); return jsonify(id=cur.lastrowid,name=name,birthDate=birth),201
@app.get('/students/<int:ident>')
@auth
def student_get(ident):
 with db() as c:r=c.execute('SELECT * FROM students WHERE id=?',(ident,)).fetchone()
 if not r:return jsonify(error='Aluno nao encontrado.'),404
 return jsonify(id=r['id'],name=r['name'],birthDate=r['birth_date'],imageUrl=r['image_url'],active=bool(r['active']))
@app.put('/students')
@roles('ADMINISTRATIVO')
def student_update():
 d=data(); ident=d.get('id');
 with db() as c:
  r=c.execute('SELECT * FROM students WHERE id=?',(ident,)).fetchone()
  if not r:return jsonify(error='Aluno nao encontrado.'),404
  c.execute('UPDATE students SET name=?,birth_date=? WHERE id=?',(d.get('name',r['name']),normdate(d.get('birthDate',r['birth_date'])),ident))
 return jsonify(ok=True)
@app.delete('/students/<int:ident>')
@roles('ADMINISTRATIVO')
def student_delete(ident):
 with db() as c:
  if not c.execute('SELECT 1 FROM students WHERE id=?',(ident,)).fetchone():return jsonify(error='Aluno nao encontrado.'),404
  c.execute('DELETE FROM enrollments WHERE student_id=?',(ident,)); c.execute('UPDATE incidents SET deleted=1 WHERE student_id=?',(ident,)); c.execute('UPDATE students SET active=0 WHERE id=?',(ident,))
 return jsonify(ok=True)
@app.patch('/students/<int:ident>/image')
@roles('ADMINISTRATIVO')
def student_image(ident):
 f=request.files.get('image')
 if not f:return jsonify(error='Arquivo de imagem obrigatorio.'),400
 if not f.mimetype.startswith('image/'):return jsonify(error='O arquivo precisa ser uma imagem.'),400
 ext=os.path.splitext(f.filename)[1].lower()[:8] or '.img'; filename=f'aluno_{ident}{ext}'; f.save(os.path.join(UPLOADS,filename)); url='/static/uploads/'+filename
 with db() as c:c.execute('UPDATE students SET image_url=? WHERE id=?',(url,ident))
 return jsonify(imageUrl=url)

@app.get('/schoolclasses')
@auth
def classes_list():
 with db() as c:
  arr=[{'id':r['id'],'name':r['name'],'shift':r['shift'],'year':r['year'],'semester':r['semester'],'canceled':bool(r['canceled'])} for r in c.execute('SELECT * FROM schoolclasses WHERE canceled=0 ORDER BY year DESC,semester,name')]
 return paginated(arr)

@app.get('/schoolclasses/canceled')
@roles('ADMINISTRATIVO','COORDENADOR')
def canceled_classes():
 with db() as c:
  arr=[{'id':r['id'],'name':r['name'],'shift':r['shift'],'year':r['year'],'semester':r['semester'],'canceled':bool(r['canceled'])} for r in c.execute('SELECT * FROM schoolclasses WHERE canceled=1 ORDER BY year DESC,semester,name')]
 return paginated(arr)
@app.post('/schoolclasses')
@roles('ADMINISTRATIVO')
def class_create():
 d=data(); name=str(d.get('name','')).strip(); shift=str(d.get('shift','')).upper(); semester=str(d.get('semester','')).upper()
 if not name or shift not in ('MANHA','MANHÃ','TARDE','NOITE') or semester not in ('PRIMEIRO','SEGUNDO','1','2','1º SEMESTRE','2º SEMESTRE') or not str(d.get('year','')).isdigit():return jsonify(error='Informe nome, turno, ano e semestre validos.'),400
 semester='PRIMEIRO' if semester in ('PRIMEIRO','1','1º SEMESTRE') else 'SEGUNDO'
 with db() as c:cur=c.execute('INSERT INTO schoolclasses(name,shift,year,semester) VALUES(?,?,?,?)',(name,shift,int(d['year']),semester)); return jsonify(id=cur.lastrowid,name=name,shift=shift,year=int(d['year']),semester=semester),201
@app.get('/schoolclasses/shifts')
@auth
def shifts():return jsonify(['MANHA','TARDE','NOITE'])
@app.get('/schoolclasses/semesters')
@auth
def semesters():return jsonify(['PRIMEIRO','SEGUNDO'])
@app.get('/schoolclasses/<int:ident>')
@auth
def class_get(ident):
 with db() as c:r=c.execute('SELECT * FROM schoolclasses WHERE id=?',(ident,)).fetchone()
 if not r:return jsonify(error='Turma nao encontrada.'),404
 return jsonify(id=r['id'],name=r['name'],shift=r['shift'],year=r['year'],semester=r['semester'],canceled=bool(r['canceled']))
@app.put('/schoolclasses')
@roles('ADMINISTRATIVO')
def class_update():
 d=data(); ident=d.get('id')
 with db() as c:
  r=c.execute('SELECT * FROM schoolclasses WHERE id=?',(ident,)).fetchone()
  if not r:return jsonify(error='Turma nao encontrada.'),404
  c.execute('UPDATE schoolclasses SET name=?,shift=?,year=?,semester=? WHERE id=?',(d.get('name',r['name']),d.get('shift',r['shift']),int(d.get('year',r['year'])),d.get('semester',r['semester']),ident))
 return jsonify(ok=True)
@app.delete('/schoolclasses/<int:ident>')
@roles('ADMINISTRATIVO')
def class_delete(ident):
 with db() as c:
  c.execute('DELETE FROM enrollments WHERE class_id=?',(ident,)); c.execute('UPDATE incidents SET deleted=1 WHERE class_id=?',(ident,)); c.execute('UPDATE schoolclasses SET canceled=1 WHERE id=?',(ident,))
 return jsonify(ok=True)

@app.get('/enrollments')
@roles('ADMINISTRATIVO','COORDENADOR','ANALISTA','PROFESSOR')
def enrollment_list():
    class_id=request.args.get('classId'); student_id=request.args.get('studentId')
    with db() as c:
        sql='SELECT e.id,e.student_id,e.class_id,s.name student_name,sc.name class_name,sc.year,sc.semester FROM enrollments e JOIN students s ON s.id=e.student_id JOIN schoolclasses sc ON sc.id=e.class_id WHERE s.active=1 AND sc.canceled=0'; args=[]
        if class_id: sql+=' AND e.class_id=?'; args.append(class_id)
        if student_id: sql+=' AND e.student_id=?'; args.append(student_id)
        sql+=' ORDER BY s.name'
        arr=[{'id':r['id'],'studentId':r['student_id'],'classId':r['class_id'],'studentName':r['student_name'],'className':r['class_name'],'year':r['year'],'semester':r['semester']} for r in c.execute(sql,args)]
    return paginated(arr)
@app.post('/enrollments')
@roles('ADMINISTRATIVO')
def enrollment_create():
    d=data(); student_id=d.get('studentId'); class_id=d.get('classId')
    if not student_id or not class_id:return jsonify(error='Aluno e turma sao obrigatorios.'),400
    try:
        with db() as c:
            cur=c.execute('INSERT INTO enrollments(student_id,class_id) VALUES(?,?)',(int(student_id),int(class_id)))
            return jsonify(id=cur.lastrowid,studentId=int(student_id),classId=int(class_id)),201
    except sqlite3.IntegrityError:return jsonify(error='Vinculo duplicado ou aluno/turma inexistente.'),409
@app.delete('/enrollments/<int:ident>')
@roles('ADMINISTRATIVO')
def enrollment_delete(ident):
    with db() as c:
        if c.execute('SELECT 1 FROM incidents i JOIN enrollments e ON e.student_id=i.student_id AND e.class_id=i.class_id WHERE e.id=? AND i.deleted=0',(ident,)).fetchone():return jsonify(error='Este vinculo possui ocorrencias; nao pode ser removido.'),409
        c.execute('DELETE FROM enrollments WHERE id=?',(ident,))
    return jsonify(ok=True)

@app.get('/categories')
@roles('ADMINISTRATIVO')
def category_list():
    with db() as c: return jsonify([dict(r) for r in c.execute('SELECT id,name FROM categories ORDER BY name')])
@app.post('/categories')
@roles('ADMINISTRATIVO')
def category_create():
    name=str(data().get('name','')).strip().upper()
    if not name:return jsonify(error='Nome da categoria obrigatorio.'),400
    try:
        with db() as c: cur=c.execute('INSERT INTO categories(name) VALUES(?)',(name,)); return jsonify(id=cur.lastrowid,name=name),201
    except sqlite3.IntegrityError:return jsonify(error='Categoria ja cadastrada.'),409
@app.delete('/categories/<int:ident>')
@roles('ADMINISTRATIVO')
def category_delete(ident):
    with db() as c:
        if c.execute('SELECT 1 FROM types WHERE category_id=?',(ident,)).fetchone():return jsonify(error='Remova primeiro os tipos desta categoria.'),409
        c.execute('DELETE FROM categories WHERE id=?',(ident,))
    return jsonify(ok=True)
@app.get('/types')
@roles('ADMINISTRATIVO')
def type_list():
    with db() as c:return jsonify([dict(r) for r in c.execute('SELECT t.id,t.name,t.category_id,c.name category FROM types t JOIN categories c ON c.id=t.category_id ORDER BY c.name,t.name')])
@app.post('/types')
@roles('ADMINISTRATIVO')
def type_create():
    d=data(); name=str(d.get('name','')).strip().upper(); category_id=d.get('categoryId')
    if not name or not category_id:return jsonify(error='Nome e categoria sao obrigatorios.'),400
    try:
        with db() as c:cur=c.execute('INSERT INTO types(name,category_id) VALUES(?,?)',(name,int(category_id)));return jsonify(id=cur.lastrowid,name=name,categoryId=int(category_id)),201
    except sqlite3.IntegrityError:return jsonify(error='Tipo duplicado ou categoria inexistente.'),409
@app.delete('/types/<int:ident>')
@roles('ADMINISTRATIVO')
def type_delete(ident):
    with db() as c:
        r=c.execute('SELECT name FROM types WHERE id=?',(ident,)).fetchone()
        if not r:return jsonify(error='Tipo nao encontrado.'),404
        if c.execute('SELECT 1 FROM incidents WHERE upper(type)=upper(?) AND deleted=0',(r['name'],)).fetchone():return jsonify(error='Este tipo ja foi usado em ocorrencias.'),409
        c.execute('DELETE FROM types WHERE id=?',(ident,))
    return jsonify(ok=True)

@app.get('/incidents/categories')
@auth
def categories():
 with db() as c:return jsonify([r['name'] for r in c.execute('SELECT name FROM categories ORDER BY name')])
@app.get('/incidents/types/<path:category>')
@auth
def types(category):
 with db() as c:return jsonify([r['name'] for r in c.execute('SELECT t.name FROM types t JOIN categories c ON c.id=t.category_id WHERE lower(c.name)=lower(?) ORDER BY t.name',(category,))])
@app.get('/incidents/status')
@auth
def statuses():return jsonify([{'name':x,'description':x.replace('_',' ').title()} for x in ['AGUARDANDO','EM_ATENDIMENTO','RESOLVIDA','ENCERRADA_SEM_SOLUCAO','FECHADA']])
@app.patch('/incidents/status')
@roles('COORDENADOR','ADMINISTRATIVO')
def update_status_compat():
    d=data(); ident=d.get('id'); status=str(d.get('status','')).upper()
    if status not in ('AGUARDANDO','EM_ATENDIMENTO','RESOLVIDA','ENCERRADA_SEM_SOLUCAO','FECHADA'): return jsonify(error='Status invalido.'),400
    with db() as c:
        cur=c.execute('UPDATE incidents SET status=?,update_date=? WHERE id=? AND deleted=0',(status,d.get('updateDate'),ident))
        if cur.rowcount==0:return jsonify(error='Ocorrencia nao encontrada.'),404
    return jsonify(ok=True)
@app.get('/incidents/status/<status_filter>')
@roles('PROFESSOR','ANALISTA','COORDENADOR')
def incidents_by_status(status_filter):
 mapping={'waiting':['AGUARDANDO'],'progressing':['EM_ATENDIMENTO'],'active':['AGUARDANDO','EM_ATENDIMENTO'],'solved':['RESOLVIDA'],'unsolved':['ENCERRADA_SEM_SOLUCAO'],'closed':['FECHADA'],'unresolved':['AGUARDANDO','EM_ATENDIMENTO','ENCERRADA_SEM_SOLUCAO']}
 statuses=mapping.get(status_filter.lower())
 if statuses is None: return jsonify(error='Filtro de status desconhecido.'),404
 with db() as c:
  placeholders=','.join('?' for _ in statuses)
  rows=c.execute(f'SELECT * FROM incidents WHERE deleted=0 AND status IN ({placeholders}) ORDER BY id DESC',statuses).fetchall()
  arr=[incident_dict(c,r) for r in rows]
 return paginated(arr)

@app.get('/incidents')
@roles('PROFESSOR','ANALISTA','COORDENADOR')
def incidents_list():
 with db() as c:
  sql='SELECT * FROM incidents WHERE deleted=0'; args=[]
  sql+=' ORDER BY id DESC'; rows=c.execute(sql,args).fetchall(); arr=[incident_dict(c,r) for r in rows]
  # Optional filters accepted by query string
  for key,field in [('studentId','idStudent'),('classId','idSchoolClass'),('category','category'),('type','type')]:
   val=request.args.get(key)
   if val:arr=[x for x in arr if str(x[field]).lower()==val.lower()]
  start=request.args.get('from'); end=request.args.get('to')
  if start:arr=[x for x in arr if x['registerDate'][:10]>=start]
  if end:arr=[x for x in arr if x['registerDate'][:10]<=end]
  sort_key=request.args.get('sort','id').split(',')[0]
  sort_fields={'id':'id','registerDate':'registerDate','category':'category','type':'type','status':'status','schoolClass.name':'schoolClassName','student.name':'studentName'}
  field=sort_fields.get(sort_key,'id')
  reverse=request.args.get('direction','desc').lower()!='asc'
  arr.sort(key=lambda x:str(x.get(field,'')).lower(),reverse=reverse)
 return paginated(arr)
@app.post('/incidents')
@roles('PROFESSOR')
def incident_create():
 d=data(); cl=d.get('idSchoolClass'); st=d.get('idStudent'); dt=normdate(d.get('registerDate')); cat=str(d.get('category','')).strip().upper(); typ=str(d.get('type','')).strip().upper(); desc=str(d.get('description','')).strip()
 if not all([cl,st,dt,cat,typ,desc]):return jsonify(error='Turma, aluno, data, categoria, tipo e descricao sao obrigatorios.'),400
 with db() as c:
  if not c.execute('SELECT 1 FROM enrollments WHERE class_id=? AND student_id=?',(cl,st)).fetchone():return jsonify(error='O aluno precisa estar vinculado a turma selecionada.'),400
  if not c.execute('SELECT 1 FROM types t JOIN categories c ON c.id=t.category_id WHERE upper(c.name)=? AND upper(t.name)=?',(cat,typ)).fetchone():return jsonify(error='O tipo informado nao pertence a categoria.'),400
  cur=c.execute('INSERT INTO incidents(class_id,student_id,register_date,category,type,description,user_id) VALUES(?,?,?,?,?,?,?)',(cl,st,dt,cat,typ,desc,request.user['id'])); row=get_incident(c,cur.lastrowid); return jsonify(incident_dict(c,row)),201
@app.get('/incidents/<int:ident>')
@roles('PROFESSOR','ANALISTA','COORDENADOR')
def incident_get(ident):
 with db() as c:
  r=get_incident(c,ident)
  if not r:return jsonify(error='Ocorrencia nao encontrada.'),404
  return jsonify(incident_dict(c,r))
@app.put('/incidents')
@roles('PROFESSOR')
def incident_update():
 d=data(); ident=d.get('id')
 with db() as c:
  r=get_incident(c,ident)
  if not r:return jsonify(error='Ocorrencia nao encontrada.'),404
  if r['user_id']!=request.user['id']:return jsonify(error='Voce so pode alterar suas proprias ocorrencias.'),403
  cl=d.get('idSchoolClass',r['class_id']); st=d.get('idStudent',r['student_id']); cat=str(d.get('category',r['category'])).upper(); typ=str(d.get('type',r['type'])).upper(); desc=d.get('description',r['description']); dt=normdate(d.get('registerDate',r['register_date']))
  if not c.execute('SELECT 1 FROM enrollments WHERE class_id=? AND student_id=?',(cl,st)).fetchone():return jsonify(error='Aluno nao vinculado a turma.'),400
  c.execute('UPDATE incidents SET class_id=?,student_id=?,register_date=?,category=?,type=?,description=?,update_date=CURRENT_TIMESTAMP WHERE id=?',(cl,st,dt,cat,typ,desc,ident));return jsonify(incident_dict(c,get_incident(c,ident)))
@app.delete('/incidents/<int:ident>')
@roles('PROFESSOR')
def incident_delete(ident):
 with db() as c:
  r=get_incident(c,ident)
  if not r:return jsonify(error='Ocorrencia nao encontrada.'),404
  if r['user_id']!=request.user['id']:return jsonify(error='Voce so pode excluir suas proprias ocorrencias.'),403
  c.execute('UPDATE incidents SET deleted=1 WHERE id=?',(ident,))
 return jsonify(ok=True)
@app.patch('/incidents/<int:ident>/status')
@roles('COORDENADOR','ADMINISTRATIVO')
def incident_status(ident):
 d=data(); status=str(d.get('status','')).upper()
 if status not in ('AGUARDANDO','EM_ATENDIMENTO','RESOLVIDA','ENCERRADA_SEM_SOLUCAO','FECHADA'):return jsonify(error='Status invalido.'),400
 with db() as c:c.execute('UPDATE incidents SET status=?,update_date=CURRENT_TIMESTAMP WHERE id=? AND deleted=0',(status,ident))
 return jsonify(ok=True)
@app.get('/incidents/summary')
@roles('COORDENADOR','ANALISTA')
def incident_summary():
 with db() as c:
  rows=c.execute('SELECT * FROM incidents WHERE deleted=0').fetchall()
  def group(field):
   d={}
   for r in rows:d[r[field]]=d.get(r[field],0)+1
   return [{'key':k,'value':v} for k,v in sorted(d.items(),key=lambda x:x[1],reverse=True)]
  status={r['status']:0 for r in rows}
  for r in rows:status[r['status']]=status.get(r['status'],0)+1
  byclass=[]; bystudent=[]
  for r in rows:
   cl=c.execute('SELECT name FROM schoolclasses WHERE id=?',(r['class_id'],)).fetchone(); st=c.execute('SELECT name FROM students WHERE id=?',(r['student_id'],)).fetchone()
   byclass.append(cl['name'] if cl else 'Sem turma'); bystudent.append(st['name'] if st else 'Sem aluno')
  def countlist(vals):
   d={}
   for x in vals:d[x]=d.get(x,0)+1
   return [{'key':k,'value':v} for k,v in sorted(d.items(),key=lambda x:x[1],reverse=True)]
  return jsonify(active=status.get('AGUARDANDO',0)+status.get('EM_ATENDIMENTO',0),waiting=status.get('AGUARDANDO',0),progressing=status.get('EM_ATENDIMENTO',0),solved=status.get('RESOLVIDA',0),unsolved=status.get('ENCERRADA_SEM_SOLUCAO',0),closed=status.get('FECHADA',0),byCategory=group('category'),byType=group('type'),bySchooclass=countlist(byclass),byStudent=countlist(bystudent),byPeriod=countlist([r['register_date'][:7] for r in rows]))

@app.get('/users/roles')
@auth
def user_roles():return jsonify(ROLES)
@app.patch('/users')
@roles('ADMINISTRATIVO')
def user_update_role():
 d=data(); ident=d.get('id'); role=str(d.get('role','')).upper()
 if not ident or role not in ROLES: return jsonify(error='Informe um usuário e um perfil válido.'),400
 with db() as c:
  cur=c.execute('UPDATE users SET role=? WHERE id=? AND active=1',(role,ident))
  if not cur.rowcount: return jsonify(error='Usuário não encontrado.'),404
 return jsonify(ok=True,message='Perfil atualizado com sucesso.')

@app.patch('/users/password')
@auth
def user_change_password():
 d=data(); ident=d.get('id'); old=str(d.get('oldPassword','')); new=str(d.get('newPassword',''))
 if not ident or not old or len(new)<6: return jsonify(error='Informe a senha atual e uma nova senha com pelo menos 6 caracteres.'),400
 if int(ident)!=int(request.user['id']): return jsonify(error='Você só pode alterar a própria senha.'),403
 with db() as c:
  user=c.execute('SELECT * FROM users WHERE id=? AND active=1',(ident,)).fetchone()
  if not user or not check_password_hash(user['password'],old): return jsonify(error='A senha atual está incorreta.'),400
  c.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(new),ident))
 return jsonify(ok=True,message='Senha alterada com sucesso.')

@app.get('/users')
@roles('ADMINISTRATIVO')
def users_list():
 with db() as c:arr=[{'id':r['id'],'name':r['name'],'login':r['login'],'role':r['role'],'active':bool(r['active'])} for r in c.execute('SELECT * FROM users ORDER BY id')]
 return paginated(arr)
@app.post('/users')
@roles('ADMINISTRATIVO')
def user_create():
 d=data(); name=str(d.get('name','')).strip(); login=str(d.get('login','')).strip(); password=str(d.get('password','')); role=str(d.get('role','')).upper()
 if not name or not login or len(password)<4 or role not in ROLES:return jsonify(error='Preencha nome, login, senha (minimo 4 caracteres) e perfil valido.'),400
 try:
  with db() as c:cur=c.execute('INSERT INTO users(name,login,password,role) VALUES(?,?,?,?)',(name,login,generate_password_hash(password),role));return jsonify(id=cur.lastrowid,name=name,login=login,role=role),201
 except sqlite3.IntegrityError:return jsonify(error='Este login ja existe.'),409
@app.get('/users/<int:ident>')
@roles('ADMINISTRATIVO')
def user_get(ident):
 with db() as c:r=c.execute('SELECT id,name,login,role,active FROM users WHERE id=?',(ident,)).fetchone()
 if not r:return jsonify(error='Usuario nao encontrado.'),404
 return jsonify(dict(r))
@app.put('/users')
@roles('ADMINISTRATIVO')
def user_update():
 d=data(); ident=d.get('id')
 with db() as c:
  r=c.execute('SELECT * FROM users WHERE id=?',(ident,)).fetchone()
  if not r:return jsonify(error='Usuario nao encontrado.'),404
  c.execute('UPDATE users SET name=?,login=?,role=?,active=? WHERE id=?',(d.get('name',r['name']),d.get('login',r['login']),d.get('role',r['role']),int(d.get('active',r['active'])),ident))
  if d.get('password'):c.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(d['password']),ident))
 return jsonify(ok=True)
@app.delete('/users/<int:ident>')
@roles('ADMINISTRATIVO')
def user_delete(ident):
 if ident==request.user['id']:return jsonify(error='Nao e possivel desativar o usuario conectado.'),400
 with db() as c:c.execute('UPDATE users SET active=0 WHERE id=?',(ident,))
 return jsonify(ok=True)

@app.errorhandler(413)
def too_large(e):return jsonify(error='Arquivo maior que 5 MB.'),413
if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
