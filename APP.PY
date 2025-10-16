# Flask Complaint Management Example
# Contains: app.py (single-file Flask app), templates (as strings), a tiny test runner, and README instructions.
# Save this file as `app.py` and follow the README at the bottom (after the code) to run & deploy.

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import sys

# -----------------------------
# Config
# -----------------------------
# Some sandboxed or interactive environments (e.g. certain notebooks, test runners)
# may not define __file__. Use a safe fallback to the current working directory.
if '__file__' in globals():
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
else:
    BASE_DIR = os.path.abspath(os.getcwd())

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# allow override via env (helpful in hosted environments)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', app.config['SECRET_KEY'])
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', app.config['SQLALCHEMY_DATABASE_URI'])

# Initialize DB extension without requiring immediate app context use elsewhere
db = SQLAlchemy()
db.init_app(app)

# -----------------------------
# Models
# -----------------------------
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    qualification = db.Column(db.String(120))

    def __repr__(self):
        return f'<Employee {self.employee_id} - {self.name}>'

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    qualification = db.Column(db.String(120))
    address = db.Column(db.String(250))
    number = db.Column(db.String(50))

    def __repr__(self):
        return f'<Client {self.client_id} - {self.name}>'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<Product {self.product_id} - {self.name}>'

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.String(64), unique=True, nullable=False)
    problem = db.Column(db.String(500))
    client_id = db.Column(db.String(64), db.ForeignKey('client.client_id'))
    assigned_employee_id = db.Column(db.String(64), db.ForeignKey('employee.employee_id'))
    product_id = db.Column(db.String(64), db.ForeignKey('product.product_id'))
    status = db.Column(db.String(20), default='PENDING')
    response = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    attachment = db.Column(db.String(250))

    def __repr__(self):
        return f'<Complaint {self.complaint_id} - {self.status}>'

# -----------------------------
# Routes (simple CRUD + forms)
# -----------------------------
@app.route('/')
def index():
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    employees = Employee.query.all()
    clients = Client.query.all()
    products = Product.query.all()
    return render_template('index.html', complaints=complaints, employees=employees, clients=clients, products=products)

# Add employee
@app.route('/employees/add', methods=['POST'])
def add_employee():
    eid = request.form.get('employee_id', '').strip()
    name = request.form.get('name', '').strip()
    qual = request.form.get('qualification')
    if not eid or not name:
        flash('Employee ID and Name required')
        return redirect(url_for('index'))
    if Employee.query.filter_by(employee_id=eid).first():
        flash('Employee ID already exists')
        return redirect(url_for('index'))
    emp = Employee(employee_id=eid, name=name, qualification=qual)
    db.session.add(emp)
    db.session.commit()
    flash('Employee added')
    return redirect(url_for('index'))

# Add client
@app.route('/clients/add', methods=['POST'])
def add_client():
    cid = request.form.get('client_id', '').strip()
    name = request.form.get('name', '').strip()
    qual = request.form.get('qualification')
    address = request.form.get('address')
    number = request.form.get('number')
    if not cid or not name:
        flash('Client ID and Name required')
        return redirect(url_for('index'))
    if Client.query.filter_by(client_id=cid).first():
        flash('Client ID already exists')
        return redirect(url_for('index'))
    client = Client(client_id=cid, name=name, qualification=qual, address=address, number=number)
    db.session.add(client)
    db.session.commit()
    flash('Client added')
    return redirect(url_for('index'))

# Add product
@app.route('/products/add', methods=['POST'])
def add_product():
    pid = request.form.get('product_id', '').strip()
    name = request.form.get('name', '').strip()
    if not pid or not name:
        flash('Product ID and Name required')
        return redirect(url_for('index'))
    if Product.query.filter_by(product_id=pid).first():
        flash('Product ID already exists')
        return redirect(url_for('index'))
    product = Product(product_id=pid, name=name)
    db.session.add(product)
    db.session.commit()
    flash('Product added')
    return redirect(url_for('index'))

# Register complaint
@app.route('/complaints/add', methods=['POST'])
def add_complaint():
    cid = request.form.get('complaint_id', '').strip()
    problem = request.form.get('problem')
    client_id = request.form.get('client_id')
    assigned_employee_id = request.form.get('assigned_employee_id')
    product_id = request.form.get('product_id')

    if not cid:
        flash('Complaint ID required')
        return redirect(url_for('index'))
    if Complaint.query.filter_by(complaint_id=cid).first():
        flash('Complaint ID already exists')
        return redirect(url_for('index'))

    attachment = None
    if 'attachment' in request.files:
        f = request.files['attachment']
        if f and f.filename:
            # sanitize filename in production (this example keeps it simple)
            filename = f"{cid}_{f.filename}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            f.save(path)
            attachment = filename

    comp = Complaint(complaint_id=cid, problem=problem, client_id=client_id,
                     assigned_employee_id=assigned_employee_id, product_id=product_id,
                     attachment=attachment)
    db.session.add(comp)
    db.session.commit()
    flash('Complaint registered')
    return redirect(url_for('index'))

# Update complaint status / response
@app.route('/complaints/<complaint_id>/update', methods=['POST'])
def update_complaint(complaint_id):
    comp = Complaint.query.filter_by(complaint_id=complaint_id).first_or_404()
    comp.status = request.form.get('status', comp.status)
    comp.response = request.form.get('response', comp.response)
    db.session.commit()
    flash('Complaint updated')
    return redirect(url_for('index'))

# Download attachment
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # send_from_directory will raise a 404 if file missing
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# -----------------------------
# Minimal templates using Flask's template loader
# For simplicity this example writes templates to a `templates/` directory when first run.
# -----------------------------
TEMPLATES = {
    'base.html': '''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Complaint Manager</title>
    <style>
      body{font-family:Arial,Helvetica,sans-serif;margin:20px}
      .flex{display:flex;gap:10px}
      .card{border:1px solid #ddd;padding:12px;border-radius:6px}
      form{margin-bottom:10px}
    </style>
  </head>
  <body>
    <h1>Complaint Manager</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
        {% for m in messages %}
          <li>{{m}}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
  </body>
</html>
''',
    'index.html': '''
{% extends 'base.html' %}
{% block content %}
<div class="flex">
  <div class="card" style="flex:1">
    <h2>Add Employee</h2>
    <form method="post" action="/employees/add">
      <input name="employee_id" placeholder="ID"><br>
      <input name="name" placeholder="Name"><br>
      <input name="qualification" placeholder="Qualification"><br>
      <button type="submit">Add</button>
    </form>

    <h2>Add Client</h2>
    <form method="post" action="/clients/add">
      <input name="client_id" placeholder="ID"><br>
      <input name="name" placeholder="Name"><br>
      <input name="qualification" placeholder="Qualification"><br>
      <input name="address" placeholder="Address"><br>
      <input name="number" placeholder="Phone"><br>
      <button type="submit">Add</button>
    </form>

    <h2>Add Product</h2>
    <form method="post" action="/products/add">
      <input name="product_id" placeholder="ID"><br>
      <input name="name" placeholder="Name"><br>
      <button type="submit">Add</button>
    </form>
  </div>

  <div class="card" style="flex:2">
    <h2>Register Complaint</h2>
    <form method="post" action="/complaints/add" enctype="multipart/form-data">
      <input name="complaint_id" placeholder="Complaint ID"><br>
      <textarea name="problem" placeholder="Problem description"></textarea><br>
      <select name="client_id">
        <option value="">--Select client--</option>
        {% for c in clients %}
          <option value="{{c.client_id}}">{{c.client_id}} - {{c.name}}</option>
        {% endfor %}
      </select><br>
      <select name="product_id">
        <option value="">--Select product--</option>
        {% for p in products %}
          <option value="{{p.product_id}}">{{p.product_id}} - {{p.name}}</option>
        {% endfor %}
      </select><br>
      <select name="assigned_employee_id">
        <option value="">--Assign Employee--</option>
        {% for e in employees %}
          <option value="{{e.employee_id}}">{{e.employee_id}} - {{e.name}}</option>
        {% endfor %}
      </select><br>
      <label>Attach file: <input type="file" name="attachment"></label><br>
      <button type="submit">Register</button>
    </form>

    <h2>Existing Complaints</h2>
    {% for comp in complaints %}
      <div style="border-bottom:1px solid #eee;padding:8px 0">
        <strong>{{comp.complaint_id}}</strong> — {{comp.problem}}<br>
        Client: {{comp.client_id}} | Product: {{comp.product_id}} | Assigned: {{comp.assigned_employee_id}}<br>
        Status: {{comp.status}} | Created: {{comp.created_at.strftime('%Y-%m-%d %H:%M')}}<br>
        {% if comp.attachment %}
          <a href="/uploads/{{comp.attachment}}">Download attachment</a><br>
        {% endif %}
        <form method="post" action="/complaints/{{comp.complaint_id}}/update">
          <select name="status">
            <option value="PENDING" {% if comp.status=='PENDING' %}selected{% endif %}>PENDING</option>
            <option value="SOLVED" {% if comp.status=='SOLVED' %}selected{% endif %}>SOLVED</option>
            <option value="NOT SOLVED" {% if comp.status=='NOT SOLVED' %}selected{% endif %}>NOT SOLVED</option>
          </select>
          <input name="response" placeholder="Response message" value="{{comp.response or ''}}">
          <button type="submit">Update</button>
        </form>
      </div>
    {% endfor %}
  </div>
</div>
{% endblock %}
'''
}


def ensure_templates_written():
    tpl_dir = os.path.join(BASE_DIR, 'templates')
    os.makedirs(tpl_dir, exist_ok=True)
    for name, content in TEMPLATES.items():
        path = os.path.join(tpl_dir, name)
        # Always overwrite to ensure updates are picked up in ephemeral environments
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

# -----------------------------
# CLI helpers
# -----------------------------
@app.cli.command('initdb')
def initdb_command():
    """Initialize the database and create some sample data."""
    with app.app_context():
        db.create_all()
        print('Initialized the database.')

        # create some sample employees/clients/products if none exist
        if not Employee.query.first():
            e = Employee(employee_id='EMP001', name='Admin1', qualification='B.Tech')
            db.session.add(e)
        if not Client.query.first():
            c = Client(client_id='CL001', name='Client A', qualification='---', address='Addr 1', number='9999999999')
            db.session.add(c)
        if not Product.query.first():
            p = Product(product_id='P001', name='Widget 1')
            db.session.add(p)
        db.session.commit()
        print('Added sample data.')

# -----------------------------
# Simple tests (run: python app.py test)
# -----------------------------
def run_quick_tests():
    print('\nRunning quick smoke tests...')
    # Create DB and templates for testing
    ensure_templates_written()
    if not os.path.exists(os.path.join(BASE_DIR, 'data.db')):
        with app.app_context():
            db.create_all()
    # Use Flask test client
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200, f'Expected 200 from index, got {resp.status_code}'
    print('GET / -> 200 OK')

    # Add an employee via POST
    resp = client.post('/employees/add', data={'employee_id': 'T001', 'name': 'Test User'})
    assert resp.status_code in (302, 200), 'Employee add should redirect or return 200'
    print('POST /employees/add -> OK (redirect or 200)')

    # Verify employee exists in DB
    with app.app_context():
        emp = Employee.query.filter_by(employee_id='T001').first()
        assert emp is not None and emp.name == 'Test User', 'Employee should be present in database'
    print('DB check: Employee present')

    # Add a client and product
    resp = client.post('/clients/add', data={'client_id': 'C001', 'name': 'Client Test'})
    assert resp.status_code in (302, 200)
    resp = client.post('/products/add', data={'product_id': 'PR001', 'name': 'Prod Test'})
    assert resp.status_code in (302, 200)
    print('Added client and product via POST')

    # Register a complaint
    resp = client.post('/complaints/add', data={'complaint_id': 'CMP001', 'problem': 'Broken', 'client_id': 'C001', 'product_id': 'PR001', 'assigned_employee_id': 'T001'})
    assert resp.status_code in (302, 200)
    print('Registered complaint via POST')

    # Update complaint status
    resp = client.post('/complaints/CMP001/update', data={'status': 'SOLVED', 'response': 'Fixed'})
    assert resp.status_code in (302, 200)
    with app.app_context():
        comp = Complaint.query.filter_by(complaint_id='CMP001').first()
        assert comp is not None and comp.status == 'SOLVED' and comp.response == 'Fixed', 'Complaint should be updated in DB'
    print('Complaint update verified in DB')

    # Final check
    resp = client.get('/')
    assert resp.status_code == 200
    print('After POSTs, GET / -> 200 OK')
    print('All quick tests passed!')

# -----------------------------
# App runner
# -----------------------------
if __name__ == '__main__':
    # special shortcut: `python app.py test` will run small smoke tests instead of starting server
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_quick_tests()
        sys.exit(0)

    ensure_templates_written()
    # if DB not initialized, create it inside app context
    if not os.path.exists(os.path.join(BASE_DIR, 'data.db')):
        with app.app_context():
            db.create_all()
    # Bind to 0.0.0.0 so other devices on the LAN can reach it. In production, use gunicorn or a platform.
    app.run(host='0.0.0.0', port=5000, debug=True)

# -----------------------------
# README (run & deploy) - follow these steps
# -----------------------------
README = """
Quick start (local):
1. Install Python 3.10+ and pip.
2. Create & activate venv:
   python -m venv venv
   source venv/bin/activate   (Linux/Mac) or venv\Scripts\activate (Windows)
3. Install dependencies:
   pip install flask flask-sqlalchemy
4. Run once to write templates and create DB:
   python app.py
   OR use the CLI helper:
   flask --app app initdb

Quick smoke tests:
   python app.py test

5. Open http://127.0.0.1:5000 on your computer or phone on the same network.

To access from ANYWHERE (production hosting options):
- Option A (recommended for production): Deploy to Render or Railway. Both have clear guides for Flask and integrate with GitHub. See Render docs and Railway docs.
- Option B (quick testing / share while developing): Use ngrok to expose local server to the internet (useful for mobile testing): `ngrok http 5000`.
- Option C (beginner friendly): PythonAnywhere can host small Flask apps and is easy to set up.

Files to add for deployment:
- requirements.txt (pip freeze > requirements.txt)
- Procfile (for some platforms): web: gunicorn app:app
- runtime.txt (optional): e.g. python-3.11.3

Production notes:
- Replace SECRET_KEY with a secure random value from env vars.
- Use PostgreSQL or MySQL on production (not SQLite) for reliability.
- Store uploaded files on cloud storage (S3, DigitalOcean Spaces) if needed.

Helpful docs (official):
- Render: https://render.com/docs/deploy-flask
- Railway: https://docs.railway.com/guides/flask
- ngrok: https://ngrok.com/docs/using-ngrok-with/flask
- PythonAnywhere help pages

"""

# write README to disk
with open(os.path.join(BASE_DIR, 'README_DEPLOY.txt'), 'w', encoding='utf-8') as f:
    f.write(README)

print('Wrote README_DEPLOY.txt alongside app.py')
