import os
from flask import Flask, render_template_string, request, jsonify, session, redirect
import psycopg
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "medvault-secret-2024")

ACCESS_PASSWORD = os.environ.get("ACCESS_PASSWORD", "medvault123")

def get_db():
    conn = psycopg.connect(os.environ["DATABASE_URL"], sslmode="require")
    return conn

def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS medicines (
                    id        SERIAL PRIMARY KEY,
                    name      TEXT    NOT NULL,
                    dosage    TEXT    NOT NULL,
                    frequency TEXT    NOT NULL,
                    stock     INTEGER NOT NULL DEFAULT 0,
                    expiry    TEXT,
                    notes     TEXT,
                    added_by  TEXT,
                    created   TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()

LOGIN_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MedVault – Login</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0f1a;--card:#111827;--border:#1e2d45;--accent:#00d4aa;--text:#e8edf5;--muted:#6b7fa3}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:2.5rem;width:360px}
h1{font-size:1.8rem;font-weight:800;margin-bottom:0.3rem}h1 span{color:var(--accent)}
.sub{color:var(--muted);font-family:'DM Mono',monospace;font-size:0.75rem;margin-bottom:2rem}
label{display:block;font-size:0.7rem;color:var(--muted);font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:1px;margin-bottom:0.3rem;margin-top:1rem}
input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:0.7rem 0.9rem;font-family:'DM Mono',monospace;font-size:0.85rem;outline:none}
input:focus{border-color:var(--accent)}
.btn{width:100%;margin-top:1.5rem;padding:0.85rem;border:none;border-radius:8px;background:var(--accent);color:#0a0f1a;font-family:'Syne',sans-serif;font-weight:700;font-size:0.95rem;cursor:pointer}
.err{color:#ff6b6b;font-size:0.8rem;margin-top:0.8rem;font-family:'DM Mono',monospace}
</style></head><body>
<div class="box">
  <h1>Med<span>Vault</span></h1>
  <div class="sub">// enter password to access</div>
  {% if error %}<div class="err">{{ error }}</div>{% endif %}
  <form method="POST" action="/login">
    <label>Your Name</label><input name="username" placeholder="e.g. Nisha" required />
    <label>Password</label><input name="password" type="password" placeholder="Enter access password" required />
    <button class="btn" type="submit">Enter MedVault →</button>
  </form>
</div></body></html>
"""

MAIN_HTML = """
<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MedVault</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0f1a;--surface:#111827;--card:#1a2235;--border:#1e2d45;--accent:#00d4aa;--accent2:#ff6b6b;--accent3:#ffd166;--text:#e8edf5;--muted:#6b7fa3}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh}
header{background:linear-gradient(135deg,#0d1b2e,#0a2540);border-bottom:1px solid var(--border);padding:1.2rem 2rem;display:flex;align-items:center;justify-content:space-between}
.logo{font-size:1.5rem;font-weight:800}.logo span{color:var(--accent)}
.user-info{font-family:'DM Mono',monospace;font-size:0.75rem;color:var(--muted)}
.user-info strong{color:var(--accent)}
.logout{background:none;border:1px solid var(--border);color:var(--muted);padding:0.3rem 0.7rem;border-radius:6px;cursor:pointer;font-size:0.75rem;margin-left:1rem;font-family:'DM Mono',monospace}
.logout:hover{border-color:var(--accent2);color:var(--accent2)}
.stats{display:flex;gap:1rem;padding:1.2rem 2rem;border-bottom:1px solid var(--border)}
.stat{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:0.8rem 1.2rem;flex:1;text-align:center}
.stat-num{font-size:1.8rem;font-weight:800;color:var(--accent)}
.stat-label{font-size:0.68rem;color:var(--muted);font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:1px}
.main{display:grid;grid-template-columns:320px 1fr;gap:1.5rem;padding:1.5rem 2rem}
.form-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.4rem;position:sticky;top:1rem;height:fit-content}
.form-title{font-size:0.78rem;font-weight:600;color:var(--accent);text-transform:uppercase;letter-spacing:1px;margin-bottom:1.2rem}
label{display:block;font-size:0.68rem;color:var(--muted);font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:0.3rem;margin-top:0.85rem}
input,select,textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);padding:0.6rem 0.8rem;font-family:'DM Mono',monospace;font-size:0.83rem;outline:none;transition:border-color 0.2s}
input:focus,select:focus,textarea:focus{border-color:var(--accent)}
select option{background:var(--surface)}textarea{resize:vertical;min-height:55px}
.btn{width:100%;margin-top:1.2rem;padding:0.8rem;border:none;border-radius:8px;background:var(--accent);color:#0a0f1a;font-family:'Syne',sans-serif;font-weight:700;font-size:0.88rem;cursor:pointer;transition:opacity 0.2s,transform 0.1s}
.btn:hover{opacity:0.88;transform:translateY(-1px)}
.table-area{display:flex;flex-direction:column;gap:1rem}
.search-row{display:flex;gap:0.8rem}.search-row input{flex:1}
.medicine-grid{display:flex;flex-direction:column;gap:0.6rem}
.med-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1rem 1.2rem;display:grid;grid-template-columns:1fr auto;gap:0.5rem;align-items:start;transition:border-color 0.2s;animation:slideIn 0.3s ease}
@keyframes slideIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.med-card:hover{border-color:var(--accent)}.med-card.low-stock{border-left:3px solid var(--accent2)}
.med-name{font-size:0.95rem;font-weight:700}
.med-meta{font-family:'DM Mono',monospace;font-size:0.73rem;color:var(--muted);margin-top:0.3rem}
.med-meta span{margin-right:0.8rem}
.badges{display:flex;gap:0.4rem;margin-top:0.5rem;flex-wrap:wrap}
.badge{font-family:'DM Mono',monospace;font-size:0.63rem;padding:0.18rem 0.45rem;border-radius:20px;font-weight:500;border:1px solid}
.badge-green{background:#00d4aa18;border-color:var(--accent);color:var(--accent)}
.badge-red{background:#ff6b6b18;border-color:var(--accent2);color:var(--accent2)}
.badge-yellow{background:#ffd16618;border-color:var(--accent3);color:var(--accent3)}
.badge-blue{background:#60a5fa18;border-color:#60a5fa;color:#60a5fa}
.card-actions{display:flex;gap:0.4rem}
.icon-btn{background:var(--border);border:none;border-radius:6px;color:var(--muted);width:30px;height:30px;cursor:pointer;font-size:0.82rem;display:flex;align-items:center;justify-content:center;transition:all 0.2s}
.icon-btn:hover{background:var(--accent);color:#0a0f1a}.icon-btn.del:hover{background:var(--accent2);color:white}
.notes-text{font-size:0.73rem;color:var(--muted);margin-top:0.4rem;font-style:italic}
.empty{text-align:center;color:var(--muted);padding:3rem;font-family:'DM Mono',monospace;font-size:0.83rem}
.toast{position:fixed;bottom:1.5rem;right:1.5rem;background:var(--accent);color:#0a0f1a;padding:0.8rem 1.2rem;border-radius:10px;font-weight:600;font-size:0.83rem;opacity:0;transition:opacity 0.3s;pointer-events:none;z-index:999}
.toast.show{opacity:1}
@media(max-width:768px){.main{grid-template-columns:1fr}.stats{flex-wrap:wrap}}
</style></head><body>
<header>
  <div class="logo">Med<span>Vault</span></div>
  <div style="display:flex;align-items:center;">
    <div class="user-info">logged in as <strong>{{ username }}</strong></div>
    <form method="POST" action="/logout" style="display:inline;">
      <button class="logout" type="submit">Log out</button>
    </form>
  </div>
</header>
<div class="stats">
  <div class="stat"><div class="stat-num" id="s-total">0</div><div class="stat-label">Total Medicines</div></div>
  <div class="stat"><div class="stat-num" id="s-low" style="color:var(--accent2)">0</div><div class="stat-label">Low Stock</div></div>
  <div class="stat"><div class="stat-num" id="s-expiring" style="color:var(--accent3)">0</div><div class="stat-label">Expiring Soon</div></div>
  <div class="stat"><div class="stat-num" id="s-units">0</div><div class="stat-label">Total Units</div></div>
</div>
<div class="main">
  <div class="form-card">
    <div class="form-title">➕ Add Medicine</div>
    <label>Medicine Name *</label><input id="f-name" placeholder="e.g. Paracetamol 500mg" />
    <label>Dosage *</label><input id="f-dosage" placeholder="e.g. 500mg" />
    <label>Frequency *</label>
    <select id="f-freq"><option>Once daily</option><option>Twice daily</option><option>Three times daily</option><option>Every 4 hours</option><option>As needed</option><option>Weekly</option></select>
    <label>Stock (units) *</label><input id="f-stock" type="number" min="0" placeholder="e.g. 30" />
    <label>Expiry Date</label><input id="f-expiry" type="date" />
    <label>Notes</label><textarea id="f-notes" placeholder="e.g. Take with food..."></textarea>
    <button class="btn" onclick="addMedicine()">Add to Vault</button>
  </div>
  <div class="table-area">
    <div class="search-row"><input id="search" placeholder="🔍  Search medicines..." oninput="renderMedicines()" /></div>
    <div class="medicine-grid" id="med-grid"><div class="empty">Loading...</div></div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let medicines=[];
async function fetchMedicines(){
  const res=await fetch('/api/medicines');
  medicines=await res.json();
  renderMedicines();updateStats();
}
function renderMedicines(){
  const q=document.getElementById('search').value.toLowerCase();
  const grid=document.getElementById('med-grid');
  const filtered=medicines.filter(m=>m.name.toLowerCase().includes(q)||m.dosage.toLowerCase().includes(q));
  if(!filtered.length){grid.innerHTML='<div class="empty">No medicines found.</div>';return;}
  grid.innerHTML=filtered.map(m=>{
    const today=new Date();
    const exp=m.expiry?new Date(m.expiry):null;
    const daysLeft=exp?Math.ceil((exp-today)/86400000):null;
    const isLow=m.stock<10;
    const isExpired=daysLeft!==null&&daysLeft<0;
    const isExpiringSoon=daysLeft!==null&&daysLeft>=0&&daysLeft<=30;
    let expiryBadge='';
    if(isExpired)expiryBadge=`<span class="badge badge-red">Expired</span>`;
    else if(isExpiringSoon)expiryBadge=`<span class="badge badge-yellow">Expires in ${daysLeft}d</span>`;
    else if(exp)expiryBadge=`<span class="badge badge-green">Exp: ${m.expiry}</span>`;
    return`<div class="med-card ${isLow?'low-stock':''}">
      <div>
        <div class="med-name">${m.name}</div>
        <div class="med-meta"><span>💊 ${m.dosage}</span><span>🔁 ${m.frequency}</span><span>📦 ${m.stock} units</span></div>
        <div class="badges">
          ${isLow?'<span class="badge badge-red">Low Stock</span>':'<span class="badge badge-green">In Stock</span>'}
          ${expiryBadge}
          ${m.added_by?`<span class="badge badge-blue">by ${m.added_by}</span>`:''}
        </div>
        ${m.notes?`<div class="notes-text">📝 ${m.notes}</div>`:''}
      </div>
      <div class="card-actions">
        <button class="icon-btn" onclick="restock(${m.id},'${m.name}')">+</button>
        <button class="icon-btn del" onclick="deleteMedicine(${m.id},'${m.name}')">✕</button>
      </div>
    </div>`;
  }).join('');
}
function updateStats(){
  const today=new Date();
  document.getElementById('s-total').textContent=medicines.length;
  document.getElementById('s-low').textContent=medicines.filter(m=>m.stock<10).length;
  document.getElementById('s-expiring').textContent=medicines.filter(m=>{
    if(!m.expiry)return false;
    const d=Math.ceil((new Date(m.expiry)-today)/86400000);
    return d>=0&&d<=30;
  }).length;
  document.getElementById('s-units').textContent=medicines.reduce((a,m)=>a+m.stock,0);
}
async function addMedicine(){
  const name=document.getElementById('f-name').value.trim();
  const dosage=document.getElementById('f-dosage').value.trim();
  const stock=parseInt(document.getElementById('f-stock').value);
  if(!name||!dosage||isNaN(stock)){showToast('Fill in required fields!',true);return;}
  await fetch('/api/medicines',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({name,dosage,frequency:document.getElementById('f-freq').value,
      stock,expiry:document.getElementById('f-expiry').value||null,
      notes:document.getElementById('f-notes').value.trim()})});
  ['f-name','f-dosage','f-stock','f-expiry','f-notes'].forEach(id=>document.getElementById(id).value='');
  showToast(`${name} added ✓`);fetchMedicines();
}
async function deleteMedicine(id,name){
  if(!confirm(`Delete ${name}?`))return;
  await fetch(`/api/medicines/${id}`,{method:'DELETE'});
  showToast(`${name} removed`);fetchMedicines();
}
async function restock(id,name){
  const qty=prompt(`Add how many units to ${name}?`);
  if(!qty||isNaN(parseInt(qty)))return;
  await fetch(`/api/medicines/${id}/restock`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({qty:parseInt(qty)})});
  showToast(`+${qty} units added`);fetchMedicines();
}
function showToast(msg,err=false){
  const t=document.getElementById('toast');t.textContent=msg;
  t.style.background=err?'var(--accent2)':'var(--accent)';
  t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2500);
}
setInterval(fetchMedicines,10000);
fetchMedicines();
</script></body></html>
"""

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form.get("password")==ACCESS_PASSWORD:
            session["username"]=request.form.get("username","User")
            return redirect("/")
        return render_template_string(LOGIN_HTML,error="Wrong password. Try again.")
    return render_template_string(LOGIN_HTML,error=None)

@app.route("/logout",methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def index():
    if "username" not in session:
        return redirect("/login")
    return render_template_string(MAIN_HTML,username=session["username"])

@app.route("/api/medicines",methods=["GET"])
def get_medicines():
    if "username" not in session:
        return jsonify({"error":"Unauthorized"}),401
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM medicines ORDER BY name")
            rows=cur.fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/medicines",methods=["POST"])
def add_medicine():
    if "username" not in session:
        return jsonify({"error":"Unauthorized"}),401
    d=request.json
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO medicines (name,dosage,frequency,stock,expiry,notes,added_by) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (d["name"],d["dosage"],d["frequency"],d["stock"],d.get("expiry"),d.get("notes"),session.get("username")))
        conn.commit()
    return jsonify({"ok":True}),201

@app.route("/api/medicines/<int:mid>",methods=["DELETE"])
def delete_medicine(mid):
    if "username" not in session:
        return jsonify({"error":"Unauthorized"}),401
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM medicines WHERE id=%s",(mid,))
        conn.commit()
    return jsonify({"ok":True})

@app.route("/api/medicines/<int:mid>/restock",methods=["POST"])
def restock(mid):
    if "username" not in session:
        return jsonify({"error":"Unauthorized"}),401
    qty=request.json.get("qty",0)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE medicines SET stock=stock+%s WHERE id=%s",(qty,mid))
        conn.commit()
    return jsonify({"ok":True})

if __name__=="__main__":
    init_db()
    print("\n✅  MedVault running at http://127.0.0.1:5000\n")
    app.run(debug=False)
