# app.py
from __future__ import annotations
from datetime import date
import sqlite3
from pathlib import Path
from flask import Flask, request, redirect, url_for, render_template_string, g, flash

APP_DB = Path("expenses.db")

# ---------- "Gasto diário" ----------
CATEGORIES = {
    "helper": "helper",
    "gasolina": "gasolina",
    "consumivel": "consumivel",
    "manutencao_do_carro": "manutencao_do_carro",
    "gasto_de_pedra": "gasto_de_pedra",
    "pedagio": "pedagio",
}

# ---------- HTML ----------
HTML = r"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Controle</title>
  <style>
    :root { --g:#eee }
    body{font-family:system-ui,Arial,sans-serif;margin:24px}
    h1{margin:0 0 12px}
    a{color:inherit;text-decoration:none}
    .tabs{display:flex;gap:8px;border-bottom:2px solid var(--g);margin-bottom:16px}
    .tab{padding:10px 14px;border:1px solid #ddd;border-bottom:none;border-radius:10px 10px 0 0;background:#fafafa}
    .tab.active{background:white;border-color:#ddd #ddd white #ddd;font-weight:600}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
    form.box{border:1px solid #ddd;border-radius:10px;padding:16px}
    label{display:block;font-size:14px;margin:6px 0 4px}
    input[type="number"],input[type="date"],input[type="text"],select{width:100%;padding:8px;box-sizing:border-box}
    button{margin-top:10px;padding:8px 12px;cursor:pointer}
    .msg{color:#0a7;margin-bottom:12px}
    .err{color:#c00;margin-bottom:12px}
    table{width:100%;border-collapse:collapse;margin-top:16px}
    th,td{padding:8px;border:1px solid #ddd;vertical-align:top}
    th{text-align:left;background:#fafafa}
    .muted{color:#666;font-size:12px}
    .row{display:flex;gap:8px;align-items:end;flex-wrap:wrap}
    .pill{background:#eef;border:1px solid #dde;border-radius:999px;padding:2px 8px;font-size:12px}
    .sticky{position:sticky;top:0;background:#fafafa}
    .hidden{display:none}
  </style>
</head>
<body>
  <h1>Controle</h1>
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat, msg in messages %}
        <div class="{{ 'err' if cat == 'error' else 'msg' }}">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  <div class="tabs">
    <a class="tab {{ 'active' if active_tab=='gasto' else '' }}" href="{{ url_for('index', tab='gasto') }}">Gasto diário</a>
    <a class="tab {{ 'active' if active_tab=='projetos' else '' }}" href="{{ url_for('index', tab='projetos') }}">Projetos de casa</a>
  </div>

  {% if active_tab=='gasto' %}
  <!-- ======================= GASTO DIÁRIO ======================= -->
  <p>Preencha o valor, data e uma observação opcional. Cada bloco salva na tabela da própria categoria.</p>
  <div class="grid">
    {% for key, label in labels %}
    <form class="box" method="post" action="{{ url_for('add_entry', category=key) }}">
      <h3 style="margin-top:0">{{ label }}</h3>
      <label for="{{ key }}_valor">Valor</label>
      <input id="{{ key }}_valor" name="amount" type="number" step="0.01" min="0" required>
      <label for="{{ key }}_data">Data</label>
      <input id="{{ key }}_data" name="date" type="date" value="{{ today }}" required>
      <label for="{{ key }}_obs">Observação</label>
      <input id="{{ key }}_obs" name="notes" type="text" placeholder="opcional">
      <button type="submit">Salvar {{ label }}</button>
    </form>
    {% endfor %}
  </div>

  <hr style="margin:28px 0">
  <h2>Relatório por Período</h2>
  <form method="get" action="{{ url_for('report') }}">
    <input type="hidden" name="tab" value="gasto">
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));">
      <div>
        <label for="start">Início</label>
        <input id="start" name="start" type="date" required value="{{ request.args.get('start','') }}">
      </div>
      <div>
        <label for="end">Fim</label>
        <input id="end" name="end" type="date" required value="{{ request.args.get('end','') }}">
      </div>
      <div style="align-self:end">
        <button type="submit">Ver relatório</button>
      </div>
    </div>
  </form>

  {% if gasto_summary %}
    <h3>Resumo {{ gasto_summary.start }} → {{ gasto_summary.end }}</h3>
    <table>
      <thead><tr class="sticky"><th>Categoria</th><th style="text-align:right">Total</th><th>Entradas</th></tr></thead>
      <tbody>
        {% for row in gasto_summary.rows %}
          <tr><td>{{ row.label }}</td><td style="text-align:right">{{ "%.2f"|format(row.total or 0) }}</td><td>{{ row.count }}</td></tr>
        {% endfor %}
      </tbody>
      <tfoot>
        <tr><th>Total Geral</th><th style="text-align:right">{{ "%.2f"|format(gasto_summary.grand_total) }}</th><th>{{ gasto_summary.grand_count }}</th></tr>
      </tfoot>
    </table>

    <h3 style="margin-top:28px">Excluir entradas no período</h3>
    <form method="post" action="{{ url_for('delete_selected') }}">
      <input type="hidden" name="start" value="{{ gasto_summary.start }}">
      <input type="hidden" name="end" value="{{ gasto_summary.end }}">
      <input type="hidden" name="tab" value="gasto">
      <table>
        <thead>
          <tr class="sticky">
            <th>Categoria</th><th>Data</th><th style="text-align:right">Valor</th><th>Observação</th><th class="muted">ID</th><th>Excluir</th>
          </tr>
        </thead>
        <tbody>
          {% for x in gasto_details %}
            <tr>
              <td>{{ x.label }}</td>
              <td>{{ x.entry_date }}</td>
              <td style="text-align:right">{{ "%.2f"|format(x.amount) }}</td>
              <td>{{ x.notes or "" }}</td>
              <td class="muted">{{ x.id }}</td>
              <td style="text-align:center"><input type="checkbox" name="sel" value="{{ x.table }}:{{ x.id }}"></td>
            </tr>
          {% endfor %}
          {% if not gasto_details %}
            <tr><td colspan="6" class="muted">Nenhuma entrada no período.</td></tr>
          {% endif %}
        </tbody>
      </table>
      <button type="submit">Excluir selecionadas</button>
    </form>
  {% endif %}
  {% endif %}

  {% if active_tab=='projetos' %}
  <!-- ======================= PROJETOS DE CASA ======================= -->
  <form class="box" method="post" action="{{ url_for('save_avulsa_or_projeto') }}" id="projForm">
    <h3>Cadastro</h3>
    <label>Tipo</label>
    <div class="row">
      <label class="pill"><input type="radio" name="tipo" value="avulsa" {{ 'checked' if proj_defaults.tipo=='avulsa' else '' }}> instalação avulsa</label>
      <label class="pill"><input type="radio" name="tipo" value="projeto" {{ 'checked' if proj_defaults.tipo=='projeto' else '' }}> projeto da casa</label>
    </div>

    <div id="avulsaFields" class="{{ '' if proj_defaults.tipo=='avulsa' else 'hidden' }}">
      <label for="av_valor">Valor a receber</label>
      <input id="av_valor" name="av_valor" type="number" step="0.01" min="0">
      <label for="av_data">Data</label>
      <input id="av_data" name="av_data" type="date" value="{{ today }}">
    </div>

    <div id="projFields" class="{{ '' if proj_defaults.tipo=='projeto' else 'hidden' }}">
      <label for="endereco">Endereço</label>
      <input id="endereco" name="endereco" type="text">

      <div class="row">
        <div style="flex:1 1 220px">
          <label for="sqt_total">Square feet total (sqt)</label>
          <input id="sqt_total" name="sqt_total" type="number" step="0.01" min="0">
        </div>
        <div>
          <label>&nbsp;</label>
          <button type="button" id="addSub">+ adicionar subárea</button>
        </div>
      </div>

      <div id="subAreas"></div>

      <label for="shop_nome">Nome do shop</label>
      <input id="shop_nome" name="shop_nome" type="text" value="UNNIT">

      <label for="n_invoices">Número de invoices (máx. 10)</label>
      <input id="n_invoices" name="n_invoices" type="number" min="1" max="10" value="1">

      <div id="invoiceNums" style="margin-top:8px"></div>

      <label for="p_data">Data do cadastro</label>
      <input id="p_data" name="p_data" type="date" value="{{ today }}">
    </div>

    <button type="submit">Salvar</button>
  </form>

  <hr style="margin:28px 0">
  <h3>Relatório por período</h3>
  <form method="get" action="{{ url_for('report_projetos') }}">
    <input type="hidden" name="tab" value="projetos">
    <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));">
      <div>
        <label for="p_start">Início</label>
        <input id="p_start" name="start" type="date" required value="{{ request.args.get('start','') }}">
      </div>
      <div>
        <label for="p_end">Fim</label>
        <input id="p_end" name="end" type="date" required value="{{ request.args.get('end','') }}">
      </div>
      <div>
        <label for="tipo_filtro">Tipo</label>
        <select id="tipo_filtro" name="tipo">
          <option value="">(ambos)</option>
          <option value="avulsa" {{ 'selected' if request.args.get('tipo')=='avulsa' else '' }}>avulsa</option>
          <option value="projeto" {{ 'selected' if request.args.get('tipo')=='projeto' else '' }}>projeto da casa</option>
        </select>
      </div>
      <div style="align-self:end"><button type="submit">Ver relatório</button></div>
    </div>
  </form>

  {% if proj_report %}
    <h4>Resultados {{ proj_report.start }} → {{ proj_report.end }} {% if proj_report.tipo %}<span class="pill">{{ proj_report.tipo }}</span>{% endif %}</h4>

    <form method="post" action="{{ url_for('delete_proj_selected') }}">
      <input type="hidden" name="start" value="{{ proj_report.start }}">
      <input type="hidden" name="end" value="{{ proj_report.end }}">
      <input type="hidden" name="tipo" value="{{ request.args.get('tipo','') }}">

      {% if proj_report.avulsas %}
        <h5>Instalações avulsas</h5>
        <table>
          <thead>
            <tr class="sticky"><th>Data</th><th style="text-align:right">Valor</th><th class="muted">ID</th><th>Excluir</th></tr>
          </thead>
          <tbody>
            {% for r in proj_report.avulsas %}
              <tr>
                <td>{{ r.entry_date }}</td>
                <td style="text-align:right">{{ "%.2f"|format(r.amount) }}</td>
                <td class="muted">{{ r.id }}</td>
                <td style="text-align:center"><input type="checkbox" name="del" value="avulsa:{{ r.id }}"></td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      {% endif %}

      {% if proj_report.projetos %}
        <h5>Projetos</h5>
        <table>
          <thead>
            <tr class="sticky">
              <th>Recebido</th><th>Data recebido</th><th>Projeto</th><th>Cadastro</th>
              <th>Endereço</th><th>Shop</th>
              <th>#Invoice</th><th>SQT total</th><th>Subáreas</th><th class="muted">IDs</th><th>Excluir</th>
            </tr>
          </thead>
          <tbody>
            {% for p in proj_report.projetos %}
              {% for inv in p.invoices %}
              <tr>
                <td style="text-align:center">
                  <input type="checkbox" form="payForm" name="inv" value="{{ inv.id }}" {{ 'checked' if inv.paid else '' }}>
                </td>
                <td>{{ inv.paid_date or '' }}</td>
                <td>Projeto #{{ p.id }}</td>
                <td>{{ p.created_date }}</td>
                <td>{{ p.endereco }}</td>
                <td>{{ p.shop_nome }}</td>
                <td>{{ inv.invoice_no or ('INV' ~ inv.idx) }}</td>
                <td style="text-align:right">{{ "%.2f"|format(p.sqt_total or 0) }}</td>
                <td>
                  {% for s in p.subs %}
                    <div>{{ s.material }} — {{ s.sqft }} sqt — dono: {{ s.dono_pedra or '—' }}</div>
                  {% endfor %}
                </td>
                <td class="muted">proj={{ p.id }} · inv={{ inv.idx }}</td>
                <td style="text-align:center"><input type="checkbox" name="del" value="invoice:{{ inv.id }}"></td>
              </tr>
              {% endfor %}
            {% endfor %}
          </tbody>
        </table>
      {% endif %}

      {% if proj_report.avulsas or proj_report.projetos %}
        <button type="submit">Excluir selecionadas</button>
      {% endif %}
    </form>

    {% if proj_report.projetos %}
      <form id="payForm" method="post" action="{{ url_for('update_invoice_paid') }}">
        <input type="hidden" name="start" value="{{ proj_report.start }}">
        <input type="hidden" name="end" value="{{ proj_report.end }}">
        <input type="hidden" name="tipo" value="{{ request.args.get('tipo','') }}">
        <button type="submit" style="margin-top:10px">Atualizar pagamentos</button>
      </form>
    {% endif %}

    {% if not proj_report.avulsas and not proj_report.projetos %}
      <p class="muted">Sem registros no período.</p>
    {% endif %}
  {% endif %}
  {% endif %}

  <script>
    const rs = (id)=>document.getElementById(id);

    // toggle tipo
    document.addEventListener('change', e=>{
      if(e.target.name==='tipo'){
        const isAv = e.target.value==='avulsa';
        rs('avulsaFields').classList.toggle('hidden', !isAv);
        rs('projFields').classList.toggle('hidden', isAv);
      }
    });

    // subáreas (cada uma com "Dono da pedra")
    const materials = ["Pure white","Sparkling white","Pisa","Rome","Ubatuba","Dallas white","Taj Mahal"];
    const subAreasDiv = document.getElementById('subAreas');
    const addBtn = document.getElementById('addSub');
    function subareaRow(){
      return `
        <div class="row" style="border:1px dashed #ddd;padding:8px;border-radius:8px">
          <div style="flex:2 1 220px">
            <label>Material</label>
            <select name="sub_material_select">
              ${materials.map(m=>`<option value="${m}">${m}</option>`).join('')}
              <option value="__custom__">-- nome manual --</option>
            </select>
          </div>
          <div style="flex:2 1 220px">
            <label>Nome manual</label>
            <input type="text" name="sub_material_custom" placeholder="preencha se escolheu nome manual">
          </div>
          <div style="flex:1 1 160px">
            <label>Square feet</label>
            <input type="number" step="0.01" min="0" name="sub_sqft">
          </div>
          <div style="flex:1 1 160px">
            <label>Dono da pedra</label>
            <select name="sub_dono">
              <option value="">(não definido)</option>
              <option value="minha">minha</option>
              <option value="shop">shop</option>
            </select>
          </div>
        </div>`;
    }
    if(addBtn){ addBtn.addEventListener('click', ()=>{ subAreasDiv.insertAdjacentHTML('beforeend', subareaRow()); }); }

    // invoices: render inputs, cap at 10
    const nInvInput = document.getElementById('n_invoices');
    const invNumsDiv = document.getElementById('invoiceNums');
    function renderInvoiceInputs(){
      let n = parseInt(nInvInput.value || '1', 10);
      if (isNaN(n) || n < 1) n = 1;
      if (n > 10) n = 10;
      nInvInput.value = n; // reflect cap in UI
      invNumsDiv.innerHTML = '';
      for(let i=1;i<=n;i++){
        invNumsDiv.insertAdjacentHTML('beforeend', `
          <div class="row">
            <div style="flex:1 1 260px">
              <label>Nº da invoice #${i}</label>
              <input type="text" name="invoice_no" placeholder="ex: 2025-00${i}">
            </div>
          </div>
        `);
      }
    }
    if(nInvInput){ nInvInput.addEventListener('input', renderInvoiceInputs); renderInvoiceInputs(); }
  </script>
</body>
</html>
"""

# ---------- App ----------
app = Flask(__name__)
app.secret_key = "change-me"

# ---------- DB ----------
def get_db() -> sqlite3.Connection:
    db = getattr(g, "_db", None)
    if db is None:
        db = sqlite3.connect(APP_DB)
        db.execute("PRAGMA foreign_keys = ON;")
        db.row_factory = sqlite3.Row
        g._db = db
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    # gasto diário
    for tbl in CATEGORIES.values():
        db.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {tbl} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL CHECK(amount >= 0),
                entry_date TEXT NOT NULL,
                notes TEXT
            )
            """
        )
    # projetos
    db.execute("""
        CREATE TABLE IF NOT EXISTS avulsa_instalacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL CHECK(amount >= 0),
            entry_date TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_date TEXT NOT NULL,
            endereco TEXT,
            sqt_total REAL,
            dono_pedra TEXT,        -- legacy, unused
            shop_nome TEXT,
            n_invoices INTEGER NOT NULL CHECK(n_invoices>=1)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS project_subfeet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            material TEXT,
            sqft REAL,
            dono_pedra TEXT,
            FOREIGN KEY(project_id) REFERENCES project(id) ON DELETE CASCADE
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS invoice (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            idx INTEGER NOT NULL,
            invoice_no TEXT,
            paid INTEGER NOT NULL DEFAULT 0,
            paid_date TEXT,
            FOREIGN KEY(project_id) REFERENCES project(id) ON DELETE CASCADE,
            UNIQUE(project_id, idx)
        )
    """)
    # migrations (ignore if already applied)
    try: db.execute("ALTER TABLE project_subfeet ADD COLUMN dono_pedra TEXT")
    except Exception: pass
    try: db.execute("ALTER TABLE invoice ADD COLUMN invoice_no TEXT")
    except Exception: pass
    db.commit()

@app.before_request
def _ensure_db():
    init_db()

# ---------- Routes: index ----------
@app.route("/", methods=["GET"])
def index():
    tab = request.args.get("tab", "gasto")
    labels = [
        ("helper", "Helper"),
        ("gasolina", "Gasolina"),
        ("consumivel", "Consumível"),
        ("manutencao_do_carro", "Manutenção do Carro"),
        ("gasto_de_pedra", "Gasto de Pedra"),
        ("pedagio", "Pedágio"),
    ]
    return render_template_string(
        HTML,
        active_tab="gasto" if tab!="projetos" else "projetos",
        labels=labels,
        today=date.today().isoformat(),
        gasto_summary=None,
        gasto_details=[],
        proj_defaults={"tipo": "avulsa"},
        proj_report=None,
    )

# ---------- Gasto diário ----------
@app.route("/add/<category>", methods=["POST"])
def add_entry(category: str):
    key = category.strip().lower()
    if key not in CATEGORIES:
        flash("Categoria inválida.", "error")
        return redirect(url_for("index", tab="gasto"))
    try:
        amount_raw = request.form.get("amount", "").strip()
        entry_date = request.form.get("date", "").strip()
        notes = request.form.get("notes", "").strip() or None
        if not amount_raw or not entry_date:
            raise ValueError("Valor e data são obrigatórios.")
        amount = float(amount_raw)
        parts = entry_date.split("-")
        if len(parts) != 3 or len(parts[0]) != 4:
            raise ValueError("Data inválida. Use YYYY-MM-DD.")
        db = get_db()
        db.execute(
            f"INSERT INTO {CATEGORIES[key]} (amount, entry_date, notes) VALUES (?,?,?)",
            (amount, entry_date, notes),
        )
        db.commit()
        flash(f"Salvo em {key}.", "info")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("index", tab="gasto"))

@app.route("/report", methods=["GET"])
def report():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        flash("Informe início e fim.", "error")
        return redirect(url_for("index", tab="gasto"))

    db = get_db()
    rows, grand_total, grand_count = [], 0.0, 0
    label_map = {
        "helper": "Helper","gasolina":"Gasolina","consumivel":"Consumível",
        "manutencao_do_carro":"Manutenção do Carro","gasto_de_pedra":"Gasto de Pedra","pedagio":"Pedágio",
    }

    for key, table in CATEGORIES.items():
        cur = db.execute(
            f"""SELECT COALESCE(SUM(amount),0) AS total, COUNT(*) AS cnt
                FROM {table}
                WHERE entry_date BETWEEN ? AND ?""",(start, end))
        res = cur.fetchone()
        total = res["total"] or 0.0
        cnt = res["cnt"] or 0
        rows.append({"label": label_map[key], "total": total, "count": cnt})
        grand_total += float(total); grand_count += int(cnt)

    details = []
    for key, table in CATEGORIES.items():
        cur = db.execute(
            f"""SELECT id, amount, entry_date, COALESCE(notes,'') AS notes
                FROM {table}
                WHERE entry_date BETWEEN ? AND ?
                ORDER BY entry_date ASC, id ASC""",(start, end))
        for r in cur.fetchall():
            details.append({"table": table,"label": label_map[key],"id": r["id"],
                            "amount": float(r["amount"]),"entry_date": r["entry_date"],"notes": r["notes"]})

    labels = [(k, v) for k, v in label_map.items()]
    return render_template_string(
        HTML,
        active_tab="gasto",
        labels=labels,
        today=date.today().isoformat(),
        gasto_summary={"start": start,"end": end,"rows": rows,"grand_total": grand_total,"grand_count": grand_count},
        gasto_details=details,
        proj_defaults={"tipo": "avulsa"},
        proj_report=None,
    )

@app.route("/delete_selected", methods=["POST"])
def delete_selected():
    selected = request.form.getlist("sel")
    start = request.form.get("start")
    end = request.form.get("end")
    if not selected:
        flash("Nenhuma linha selecionada.", "error")
        return redirect(url_for("index", tab="gasto"))
    db = get_db()
    deleted = 0
    for item in selected:
        try:
            table, sid = item.split(":", 1)
            if table not in CATEGORIES.values(): continue
            _id = int(sid)
            db.execute(f"DELETE FROM {table} WHERE id=?", (_id,))
            deleted += 1
        except Exception:
            continue
    db.commit()
    flash(f"{deleted} entrad(as) apagadas.", "info")
    return redirect(url_for("report", start=start, end=end, tab="gasto"))

# ---------- Projetos ----------
@app.route("/projetos/save", methods=["POST"])
def save_avulsa_or_projeto():
    tipo = request.form.get("tipo")
    db = get_db()
    if tipo == "avulsa":
        try:
            amount = float(request.form.get("av_valor") or "0")
            entry_date = request.form.get("av_data") or date.today().isoformat()
            db.execute("INSERT INTO avulsa_instalacao (amount, entry_date) VALUES (?,?)", (amount, entry_date))
            db.commit()
            flash("Instalação avulsa salva.", "info")
        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("index", tab="projetos"))

    if tipo == "projeto":
        try:
            endereco = (request.form.get("endereco") or "").strip()
            sqt_total = float(request.form.get("sqt_total") or "0")
            shop_nome = (request.form.get("shop_nome") or "UNNIT").strip()
            n_invoices = max(1, min(10, int(request.form.get("n_invoices") or "1")))  # cap 10
            created_date = request.form.get("p_data") or date.today().isoformat()

            cur = db.execute(
                "INSERT INTO project (created_date, endereco, sqt_total, dono_pedra, shop_nome, n_invoices) VALUES (?,?,?,?,?,?)",
                (created_date, endereco, sqt_total, None, shop_nome, n_invoices)
            )
            pid = cur.lastrowid

            # subáreas
            mats_sel = request.form.getlist("sub_material_select")
            mats_custom = request.form.getlist("sub_material_custom")
            sqfts = request.form.getlist("sub_sqft")
            donos = request.form.getlist("sub_dono")
            for sel, custom, sqft, dono in zip(mats_sel, mats_custom, sqfts, donos):
                mat = (custom.strip() if sel == "__custom__" and (custom or "").strip() else sel)
                try: sqft_v = float(sqft or "0")
                except ValueError: sqft_v = 0.0
                dono_final = dono if dono in ("minha","shop") else None
                if sqft_v > 0 or mat:
                    db.execute(
                        "INSERT INTO project_subfeet (project_id, material, sqft, dono_pedra) VALUES (?,?,?,?)",
                        (pid, mat, sqft_v, dono_final)
                    )

            # invoices
            inv_numbers = request.form.getlist("invoice_no")
            inv_numbers = (inv_numbers + [""] * n_invoices)[:n_invoices]
            for i in range(1, n_invoices + 1):
                db.execute(
                    "INSERT INTO invoice (project_id, idx, invoice_no, paid, paid_date) VALUES (?,?,?,?,NULL)",
                    (pid, i, (inv_numbers[i-1].strip() or None), 0)
                )

            db.commit()
            flash(f"Projeto #{pid} salvo.", "info")
        except Exception as e:
            flash(f"Erro: {e}", "error")
        return redirect(url_for("index", tab="projetos"))

    flash("Tipo inválido.", "error")
    return redirect(url_for("index", tab="projetos"))

@app.route("/projetos/report", methods=["GET"])
def report_projetos():
    start = request.args.get("start")
    end = request.args.get("end")
    tipo = request.args.get("tipo", "").strip()
    if not start or not end:
        flash("Informe início e fim.", "error")
        return redirect(url_for("index", tab="projetos"))

    db = get_db()
    result = {"start": start, "end": end, "tipo": tipo, "avulsas": [], "projetos": []}

    if tipo in ("", "avulsa"):
        cur = db.execute(
            """SELECT id, amount, entry_date
               FROM avulsa_instalacao
               WHERE entry_date BETWEEN ? AND ?
               ORDER BY entry_date, id""",(start, end))
        result["avulsas"] = [dict(r) for r in cur.fetchall()]

    if tipo in ("", "projeto"):
        cur = db.execute(
            """SELECT id, created_date, endereco, sqt_total, shop_nome, n_invoices
               FROM project
               WHERE created_date BETWEEN ? AND ?
               ORDER BY created_date, id""",(start, end))
        projects = [dict(r) for r in cur.fetchall()]
        for p in projects:
            subs = db.execute(
                "SELECT material, sqft, dono_pedra FROM project_subfeet WHERE project_id=? ORDER BY id",
                (p["id"],)
            ).fetchall()
            invs = db.execute(
                "SELECT id, idx, invoice_no, paid, paid_date FROM invoice WHERE project_id=? ORDER BY idx",
                (p["id"],)
            ).fetchall()
            p["subs"] = [dict(s) for s in subs]
            p["invoices"] = [dict(i) for i in invs]
        result["projetos"] = projects

    return render_template_string(
        HTML,
        active_tab="projetos",
        labels=[(k, v) for k, v in {"helper":"Helper","gasolina":"Gasolina","consumivel":"Consumível","manutencao_do_carro":"Manutenção do Carro","gasto_de_pedra":"Gasto de Pedra","pedagio":"Pedágio"}.items()],
        today=date.today().isoformat(),
        gasto_summary=None,
        gasto_details=[],
        proj_defaults={"tipo": "avulsa"},
        proj_report=result,
    )

@app.route("/projetos/invoices/update", methods=["POST"])
def update_invoice_paid():
    checked_ids = set(request.form.getlist("inv"))
    start = request.form.get("start"); end = request.form.get("end"); tipo = request.form.get("tipo","")
    db = get_db()
    invs = db.execute("""
        SELECT invoice.id AS id
        FROM invoice
        JOIN project ON project.id = invoice.project_id
        WHERE project.created_date BETWEEN ? AND ?
        ORDER BY project.id, invoice.idx
    """,(start, end)).fetchall()
    today_s = date.today().isoformat()
    for r in invs:
        inv_id = str(r["id"])
        if inv_id in checked_ids:
            db.execute("UPDATE invoice SET paid=1, paid_date=COALESCE(paid_date, ?) WHERE id=?", (today_s, inv_id))
        else:
            db.execute("UPDATE invoice SET paid=0, paid_date=NULL WHERE id=?", (inv_id,))
    db.commit()
    flash("Pagamentos atualizados.", "info")
    return redirect(url_for("report_projetos", start=start, end=end, tipo=tipo, tab="projetos"))

@app.route("/projetos/delete", methods=["POST"])
def delete_proj_selected():
    to_del = request.form.getlist("del")
    start = request.form.get("start"); end = request.form.get("end"); tipo = request.form.get("tipo","")
    if not to_del:
        flash("Nenhuma linha selecionada.", "error")
        return redirect(url_for("report_projetos", start=start, end=end, tipo=tipo, tab="projetos"))
    db = get_db()
    deleted = 0
    for token in to_del:
        try:
            kind, sid = token.split(":", 1)
            _id = int(sid)
            if kind == "avulsa":
                db.execute("DELETE FROM avulsa_instalacao WHERE id=?", (_id,))
                deleted += 1
            elif kind == "invoice":
                db.execute("DELETE FROM invoice WHERE id=?", (_id,))
                deleted += 1
        except Exception:
            continue
    db.commit()
    flash(f"{deleted} linha(s) apagadas.", "info")
    return redirect(url_for("report_projetos", start=start, end=end, tipo=tipo, tab="projetos"))

# ---------- Main ----------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
