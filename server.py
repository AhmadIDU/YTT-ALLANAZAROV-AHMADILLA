"""
PossKassa — Standalone Demo Server
Faqat Python stdlib: http.server, sqlite3, json, uuid, datetime
Hech qanday pip paketi kerak emas!

Ishga tushirish: python3 server.py
API:  http://localhost:8000/api/v1/...
UI:   http://localhost:8000/
"""
import http.server
import socketserver
import sqlite3
import json
import uuid
import os
import sys
import urllib.parse
from datetime import datetime, timezone

import sys
PORT    = int(sys.argv[1]) if len(sys.argv) > 1 else 3500
DB_PATH = os.path.join(os.path.dirname(__file__), "posskassa.db")
STATIC  = os.path.join(os.path.dirname(__file__), "static")

# ══════════════════════════════════════════════════════════════
# 1. Ma'lumotlar bazasi
# ══════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, barcode TEXT,
        unit TEXT DEFAULT 'pcs', price REAL DEFAULT 0,
        cost_price REAL DEFAULT 0, stock_qty REAL DEFAULT 0,
        is_active INTEGER DEFAULT 1, created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS sales (
        id TEXT PRIMARY KEY, receipt_number TEXT,
        cashier TEXT DEFAULT 'Kassir', total_amount REAL NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        sync_status TEXT DEFAULT 'synced', sale_time TEXT
    );
    CREATE TABLE IF NOT EXISTS sale_items (
        id TEXT PRIMARY KEY, sale_id TEXT, product_id TEXT,
        product_name TEXT, quantity REAL,
        unit_price REAL, total_price REAL
    );
    CREATE TABLE IF NOT EXISTS intake_drafts (
        id TEXT PRIMARY KEY, source TEXT,
        status TEXT DEFAULT 'review_pending',
        rows_json TEXT, created_at TEXT
    );

    -- ── NASIYA / QARZ MODULI ─────────────────────────────
    CREATE TABLE IF NOT EXISTS debtors (
        id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        total_debt REAL DEFAULT 0,
        created_at TEXT,
        notes TEXT
    );

    CREATE TABLE IF NOT EXISTS debts (
        id TEXT PRIMARY KEY,
        debtor_id TEXT NOT NULL,
        sale_id TEXT,
        amount REAL NOT NULL,
        paid_amount REAL DEFAULT 0,
        remaining REAL NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'active',
        due_date TEXT,
        created_at TEXT,
        FOREIGN KEY(debtor_id) REFERENCES debtors(id)
    );

    CREATE TABLE IF NOT EXISTS debt_payments (
        id TEXT PRIMARY KEY,
        debt_id TEXT NOT NULL,
        debtor_id TEXT NOT NULL,
        amount REAL NOT NULL,
        payment_method TEXT DEFAULT 'cash',
        note TEXT,
        paid_at TEXT,
        FOREIGN KEY(debt_id) REFERENCES debts(id)
    );
    """)

    # Demo mahsulotlar — faqat bo'sh bo'lsa qo'shiladi
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        now = _now()
        for p in [
            ("Non Obi 500g",         "4600001", "pcs",  3500,  2200, 120),
            ("Sut 1L Nestle",         "4600002", "l",    9800,  7500,  45),
            ("Shakar 1kg",            "4600003", "kg",  12000,  9000,  80),
            ("Tuxum 10 dona",         "4600004", "pcs", 22000, 17000,  30),
            ("Coca-Cola 0.5L",        "4600005", "pcs",  8500,  6000, 200),
            ("Makaron 500g",          "4600006", "pcs",  7000,  5200,  60),
            ("Yog' Oltin 1L",         "4600007", "l",   28000, 22000,  25),
            ("Guruch 1kg",            "4600008", "kg",  14000, 10500,  90),
            ("Mol gusht 1kg",         "4600009", "kg",  75000, 60000,  15),
            ("Sabzi 1kg",             "4600010", "kg",   6000,  4000, 100),
            ("Piyoz 1kg",             "4600011", "kg",   4500,  3000, 150),
            ("Pomidor 1kg",           "4600012", "kg",   8000,  5500,  70),
            ("Kartoshka 1kg",         "4600013", "kg",   5000,  3500, 200),
            ("Choy Lipton 100g",      "4600014", "pcs", 18000, 13000,  40),
            ("Qand 1kg",              "4600015", "kg",  16000, 12000,  55),
        ]:
            c.execute(
                "INSERT INTO products VALUES (?,?,?,?,?,?,?,1,?)",
                (str(uuid.uuid4()), p[0], p[1], p[2], p[3], p[4], p[5], now)
            )

    # Demo sotuvlar — faqat bo'sh bo'lsa
    if c.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0:
        now = _now()
        for total, method in [
            (35000,"cash"), (98500,"payme"), (22000,"cash"),
            (150000,"uzcard"), (47500,"cash"), (63000,"click"),
            (28000,"cash"), (112000,"uzcard"), (18500,"cash"), (75000,"humo"),
        ]:
            sid = str(uuid.uuid4())
            c.execute("INSERT INTO sales VALUES (?,?,?,?,?,?,?)",
                      (sid, _receipt(), "Demo Kassir", total, method, "synced", now))

    # Demo qarzdorlar — faqat bo'sh bo'lsa
    if c.execute("SELECT COUNT(*) FROM debtors").fetchone()[0] == 0:
        now = _now()
        d1 = str(uuid.uuid4())
        d2 = str(uuid.uuid4())
        d3 = str(uuid.uuid4())
        d4 = str(uuid.uuid4())
        for did, name, phone, addr, debt, note in [
            (d1, "Karimov Botir",    "+998901234567", "Chilonzor 5",      150000, "Doimiy mijoz"),
            (d2, "Rahimova Malika",  "+998912345678", "Yunusobod 12",      85000, ""),
            (d3, "Toshmatov Sardor", "+998923456789", "Mirzo Ulugbek 3",  320000, "Oylik to'laydi"),
            (d4, "Usmonov Jasur",    "+998934567890", "Shayxontohur 7",        0, ""),
        ]:
            c.execute("INSERT INTO debtors VALUES (?,?,?,?,?,?,?)",
                      (did, name, phone, addr, debt, now, note))
        # Demo qarzlar
        for did, total, paid, desc in [
            (d1, 150000,      0, "Oziq-ovqat mahsulotlari"),
            (d2,  85000,      0, "Kunlik xarid"),
            (d3, 500000, 180000, "Oylik zakaz"),
        ]:
            c.execute("INSERT INTO debts VALUES (?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), did, None, total, paid, total-paid,
                 desc, "active", None, now))

    conn.commit()
    conn.close()
    print(f"  DB: {DB_PATH}")

def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _now():
    return datetime.now(timezone.utc).isoformat()

def _receipt():
    d = datetime.now().strftime("%Y%m%d")
    return f"PK-{d}-{str(uuid.uuid4())[:4].upper()}"

def _rows(cursor):
    return [dict(r) for r in cursor.fetchall()]

def _ok(data, st=200):   return st, data
def _err(msg, st=400):   return st, {"error": msg}



# ══════════════════════════════════════════════════════════════
# 2. API Router
# ══════════════════════════════════════════════════════════════
def handle_api(method, path, body, params):
    parts = [p for p in path.strip("/").split("/") if p]
    # parts: ["api","v1","resource",...]
    res = parts[2] if len(parts) > 2 else ""

    # ── Auth ─────────────────────────────────────────────────
    if res == "auth":
        return _ok({
            "access_token": "demo-jwt-posskassa", "refresh_token": "demo-refresh",
            "token_type": "bearer", "expires_in": 86400,
            "tenant_id": "demo-tenant-001",
            "user": {"id": "u-001", "full_name": "Demo Menejer",
                     "phone": "+998901234567", "role": "manager"}
        })

    # ── Health ────────────────────────────────────────────────
    if res == "health" or path == "/health":
        return _ok({"status": "ok", "service": "posskassa-demo"})

    # ── Products ──────────────────────────────────────────────
    if res == "products":
        conn = _db()
        # barcode lookup
        if len(parts) >= 5 and parts[3] == "barcode":
            row = conn.execute(
                "SELECT * FROM products WHERE barcode=? AND is_active=1", (parts[4],)
            ).fetchone()
            conn.close()
            if row:
                d = dict(row)
                d["margin_pct"] = round((d["price"]-d["cost_price"])/d["price"]*100,1) if d["price"] else 0
                return _ok(d)
            return _err("Topilmadi", 404)

        # low-stock
        if len(parts) == 4 and parts[3] == "low-stock" and method == "GET":
            rows = _rows(conn.execute(
                "SELECT name as product_name, stock_qty as quantity, 'Asosiy ombor' as warehouse "
                "FROM products WHERE is_active=1 AND stock_qty < 20 ORDER BY stock_qty"
            ))
            conn.close()
            return _ok(rows)

        # list
        if method == "GET" and len(parts) == 3:
            q = params.get("q","")
            if q:
                rows = _rows(conn.execute(
                    "SELECT * FROM products WHERE is_active=1 AND (name LIKE ? OR barcode LIKE ?)",
                    (f"%{q}%", f"%{q}%")
                ))
            else:
                rows = _rows(conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY name"))
            conn.close()
            for r in rows:
                r["margin_pct"] = round((r["price"]-r["cost_price"])/r["price"]*100,1) if r["price"] else 0
                r["stock_levels"] = [{"warehouse_id":"wh-001","warehouse_name":"Asosiy ombor",
                                       "quantity":r["stock_qty"],"reserved_quantity":0,
                                       "available":r["stock_qty"],"low_stock_threshold":20,
                                       "is_low": r["stock_qty"] < 20}]
            return _ok(rows)

        # single
        if method == "GET" and len(parts) == 4:
            row = conn.execute("SELECT * FROM products WHERE id=? AND is_active=1",(parts[3],)).fetchone()
            conn.close()
            if row: return _ok(dict(row))
            return _err("Topilmadi", 404)

        # create
        if method == "POST" and len(parts) == 3:
            pid = str(uuid.uuid4())
            conn.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,1,?)",
                (pid, body.get("name",""), body.get("barcode",""),
                 body.get("unit","pcs"), body.get("price",0),
                 body.get("cost_price",0), 0, _now()))
            conn.commit()
            row = dict(conn.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone())
            conn.close()
            return _ok(row, 201)

        # update
        if method == "PUT" and len(parts) == 4:
            pid = parts[3]
            fields, vals = [], []
            for f in ("name","price","cost_price","barcode","unit","is_active"):
                if f in body:
                    fields.append(f"{f}=?"); vals.append(body[f])
            if fields:
                conn.execute(f"UPDATE products SET {','.join(fields)} WHERE id=?",(*vals,pid))
                conn.commit()
            row = conn.execute("SELECT * FROM products WHERE id=?",(pid,)).fetchone()
            conn.close()
            if row: return _ok(dict(row))
            return _err("Topilmadi", 404)

        # delete (soft)
        if method == "DELETE" and len(parts) == 4:
            conn.execute("UPDATE products SET is_active=0 WHERE id=?",(parts[3],))
            conn.commit(); conn.close()
            return _ok({"message": "O'chirildi"}, 204)

        conn.close()



    # ── Sales ─────────────────────────────────────────────────
    if res == "sales":
        conn = _db()

        if method == "POST" and len(parts) == 3:
            sid   = str(uuid.uuid4())
            items = body.get("items", [])
            total = body.get("total_amount", sum(i.get("total_price",0) for i in items))
            conn.execute("INSERT INTO sales VALUES (?,?,?,?,?,?,?)",
                (sid, _receipt(), "Kassir", total,
                 body.get("payments",[{}])[0].get("method","cash") if body.get("payments") else "cash",
                 "synced", _now()))
            for it in items:
                conn.execute("INSERT INTO sale_items VALUES (?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), sid, it.get("product_id",""),
                     it.get("product_name", it.get("name","")),
                     it.get("quantity",1), it.get("unit_price",0), it.get("total_price",0)))
                conn.execute("UPDATE products SET stock_qty=MAX(0,stock_qty-?) WHERE id=?",
                    (it.get("quantity",1), it.get("product_id","")))
            conn.commit()
            row = dict(conn.execute("SELECT * FROM sales WHERE id=?",(sid,)).fetchone())
            row["items"] = items
            row["fiscal_url"] = f"https://ofd.soliq.uz/check/{sid[:8]}"
            conn.close()
            return _ok(row, 201)

        if method == "POST" and len(parts) == 4 and parts[3] == "sync":
            results = []
            for s in body.get("sales", []):
                sid = str(uuid.uuid4())
                conn.execute("INSERT OR IGNORE INTO sales VALUES (?,?,?,?,?,?,?)",
                    (sid, _receipt(), "Kassir", s.get("total_amount",0), "cash", "synced", s.get("sale_time",_now())))
                conn.commit()
                results.append({"local_id": s.get("local_id",""), "remote_id": sid,
                                 "success": True, "fiscal_url": f"https://ofd.soliq.uz/check/{sid[:8]}"})
            conn.close()
            return _ok({"results": results, "synced": len(results), "failed": 0})

        if method == "GET" and len(parts) == 3:
            sales = _rows(conn.execute("SELECT * FROM sales ORDER BY sale_time DESC LIMIT 50"))
            for s in sales:
                s["items"] = _rows(conn.execute("SELECT * FROM sale_items WHERE sale_id=?",(s["id"],)))
            conn.close()
            return _ok(sales)

        if method == "GET" and len(parts) == 4:
            row = conn.execute("SELECT * FROM sales WHERE id=?",(parts[3],)).fetchone()
            conn.close()
            if row:
                d = dict(row)
                d["items"] = _rows(conn.execute("SELECT * FROM sale_items WHERE sale_id=?",(d["id"],))) if False else []
                return _ok(d)
            return _err("Topilmadi", 404)

        conn.close()

    # ── Reports ───────────────────────────────────────────────
    if res == "reports":
        sub = parts[3] if len(parts) > 3 else ""
        conn = _db()

        if sub == "sales-summary":
            row = conn.execute("""
                SELECT COUNT(*) as total_sales,
                       COALESCE(SUM(total_amount),0) as total_revenue,
                       COALESCE(AVG(total_amount),0) as avg_check
                FROM sales""").fetchone()
            by_day = _rows(conn.execute("""
                SELECT substr(sale_time,1,10) as period, COUNT(*) as sales_count,
                       SUM(total_amount) as revenue, AVG(total_amount) as avg_check
                FROM sales GROUP BY period ORDER BY period DESC LIMIT 30"""))
            conn.close()
            return _ok({"total_sales": row[0], "total_revenue": round(row[1],0),
                         "avg_check": round(row[2],0), "series": by_day,
                         "payment_breakdown": []})

        if sub == "top-products":
            rows = _rows(conn.execute("""
                SELECT product_name, SUM(quantity) as total_qty,
                       SUM(total_price) as total_revenue,
                       COUNT(DISTINCT sale_id) as sale_count, 'pcs' as unit,
                       SUM(total_price)*0.3 as gross_profit
                FROM sale_items GROUP BY product_name
                ORDER BY total_revenue DESC LIMIT 20"""))
            conn.close()
            return _ok(rows)

        if sub == "abc-analysis":
            rows = _rows(conn.execute("""
                SELECT product_name as product_name, SUM(total_price) as total_revenue
                FROM sale_items GROUP BY product_name ORDER BY total_revenue DESC"""))
            total = sum(r["total_revenue"] for r in rows) or 1
            cum, A, B, C = 0, [], [], []
            for r in rows:
                cum += r["total_revenue"]
                pct = cum / total * 100
                r["revenue_pct"] = round(r["total_revenue"]/total*100,2)
                r["cumulative_pct"] = round(pct,2)
                (A if pct<=80 else B if pct<=95 else C).append(r)
            conn.close()
            return _ok({"A":{"count":len(A),"items":A}, "B":{"count":len(B),"items":B},
                         "C":{"count":len(C),"items":C}, "total_revenue": round(total,0)})

        if sub == "margin":
            rows = _rows(conn.execute("""
                SELECT si.product_name, SUM(si.total_price) as revenue,
                       SUM(si.quantity*p.cost_price) as cost,
                       SUM(si.total_price)-SUM(si.quantity*p.cost_price) as profit,
                       ROUND((SUM(si.total_price)-SUM(si.quantity*p.cost_price))/SUM(si.total_price)*100,2) as margin_pct
                FROM sale_items si
                LEFT JOIN products p ON si.product_id=p.id
                GROUP BY si.product_name ORDER BY margin_pct DESC"""))
            total_rev  = sum(r["revenue"] for r in rows)
            total_cost = sum((r["cost"] or 0) for r in rows)
            conn.close()
            return _ok({"summary":{"total_revenue":round(total_rev,0),"total_cost":round(total_cost,0),
                                    "total_profit":round(total_rev-total_cost,0),
                                    "avg_margin_pct":round((total_rev-total_cost)/total_rev*100,2) if total_rev else 0},
                         "items": rows})

        if sub == "cashier-performance":
            rows = _rows(conn.execute("""
                SELECT cashier as cashier_name, COUNT(*) as total_sales,
                       SUM(total_amount) as total_revenue, AVG(total_amount) as avg_check,
                       COUNT(DISTINCT substr(sale_time,1,10)) as working_days
                FROM sales GROUP BY cashier ORDER BY total_revenue DESC"""))
            conn.close()
            return _ok(rows)

        if sub == "stock-value":
            rows = _rows(conn.execute("""
                SELECT id as product_id, name as product_name, unit,
                       stock_qty as quantity, cost_price, price as selling_price,
                       stock_qty*cost_price as stock_cost_value,
                       stock_qty*price as stock_retail_value,
                       (price-cost_price)*stock_qty as potential_profit,
                       'Asosiy ombor' as warehouse_name
                FROM products WHERE is_active=1 AND stock_qty>0
                ORDER BY stock_cost_value DESC"""))
            tc = sum(r["stock_cost_value"] for r in rows)
            tr = sum(r["stock_retail_value"] for r in rows)
            conn.close()
            return _ok({"summary":{"total_items":len(rows),"total_cost_value":round(tc,0),
                                    "total_retail_value":round(tr,0),"potential_profit":round(tr-tc,0)},
                         "items": rows})

        conn.close()



    # ── Dashboard ─────────────────────────────────────────────
    if res == "dashboard":
        conn = _db()
        row = conn.execute("""
            SELECT COUNT(*) as sales_count,
                   COALESCE(SUM(total_amount),0) as revenue,
                   COALESCE(AVG(total_amount),0) as avg_check
            FROM sales""").fetchone()
        top = _rows(conn.execute("""
            SELECT product_name, SUM(quantity) as total_qty,
                   SUM(total_price) as total_revenue
            FROM sale_items GROUP BY product_name
            ORDER BY total_revenue DESC LIMIT 5"""))
        pay = _rows(conn.execute("""
            SELECT payment_method as method, COUNT(*) as count,
                   SUM(total_amount) as total
            FROM sales GROUP BY payment_method"""))
        conn.close()
        return _ok({
            "today": {"sales_count": row[0], "revenue": round(row[1],0),
                      "avg_check": round(row[2],0), "top_products": top},
            "payment_breakdown": pay
        })

    # ── Warehouses ────────────────────────────────────────────
    if res == "warehouses":
        return _ok([{"id":"wh-001","name":"Asosiy ombor","is_default":True,"address":"Demo manzil"}])

    # ── Categories ────────────────────────────────────────────
    if res == "categories":
        return _ok([
            {"id":"cat-1","name":"Oziq-ovqat",       "icon":"🥕","children":[]},
            {"id":"cat-2","name":"Ichimliklar",        "icon":"🥤","children":[]},
            {"id":"cat-3","name":"Non mahsulotlari",   "icon":"🍞","children":[]},
            {"id":"cat-4","name":"Sut mahsulotlari",   "icon":"🥛","children":[]},
            {"id":"cat-5","name":"Go'sht",             "icon":"🥩","children":[]},
        ])

    # ── Intake ────────────────────────────────────────────────
    if res == "intake":
        sub = parts[3] if len(parts) > 3 else ""
        conn = _db()

        if sub in ("photo","csv","esf") and method == "POST":
            did = str(uuid.uuid4())
            mock = [
                {"name":"Demo tovar 1","barcode":"9900001","qty":10,"unit":"pcs",
                 "unit_cost":5000,"total_cost":50000,"vat_rate":12,"approved":True,
                 "_match":{"action":"create_new","candidates":[]}},
                {"name":"Demo tovar 2","barcode":"9900002","qty":5,"unit":"kg",
                 "unit_cost":8000,"total_cost":40000,"vat_rate":12,"approved":True,
                 "_match":{"action":"create_new","candidates":[]}},
            ]
            conn.execute("INSERT INTO intake_drafts VALUES (?,?,?,?,?)",
                (did, sub, "review_pending", json.dumps(mock), _now()))
            conn.commit(); conn.close()
            return _ok({"draft_id":did,"status":"review_pending","rows_count":len(mock),
                         "message":"Tahlil qilindi. Tekshiruv uchun tayyor."}, 201)

        if sub == "drafts":
            if method == "GET" and len(parts) == 4:
                drafts = _rows(conn.execute("SELECT * FROM intake_drafts ORDER BY created_at DESC"))
                conn.close()
                for d in drafts:
                    d["rows_count"] = len(json.loads(d.get("rows_json") or "[]"))
                return _ok(drafts)

            if len(parts) == 5:
                did = parts[4]
                if method == "GET":
                    row = conn.execute("SELECT * FROM intake_drafts WHERE id=?",(did,)).fetchone()
                    conn.close()
                    if not row: return _err("Topilmadi",404)
                    d = dict(row); d["rows"] = json.loads(d.get("rows_json") or "[]")
                    return _ok(d)
                if method == "PUT":
                    conn.execute("UPDATE intake_drafts SET rows_json=? WHERE id=?",
                        (json.dumps(body), did))
                    conn.commit(); conn.close()
                    return _ok({"draft_id":did,"rows_count":len(body),"status":"review_pending"})

            if len(parts) == 6:
                did = parts[4]; action = parts[5]
                if action == "approve":
                    rows = body.get("reviewed_rows",[])
                    for r in rows:
                        if not r.get("approved",True): continue
                        pid = str(uuid.uuid4())
                        conn.execute("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?,?,?,1,?)",
                            (pid, r.get("name",""), r.get("barcode",""), r.get("unit","pcs"),
                             round(r.get("unit_cost",0)*1.3,0), r.get("unit_cost",0),
                             r.get("qty",0), _now()))
                    conn.execute("UPDATE intake_drafts SET status='approved' WHERE id=?", (did,))
                    conn.commit(); conn.close()
                    return _ok({"receipt_number":_receipt(),"items_count":len(rows),
                                 "total_cost":sum(r.get("total_cost",0) for r in rows),
                                 "message":"Kirim tasdiqlandi va zaxira yangilandi!"}, 201)
                if action == "reject":
                    conn.execute("UPDATE intake_drafts SET status='rejected' WHERE id=?",(did,))
                    conn.commit(); conn.close()
                    return _ok({"message":"Rad etildi"})

        if sub == "suppliers":
            conn.close()
            return _ok([{"id":"sup-1","name":"Demo Yetkazuvchi MCHJ","inn":"123456789","phone":"+998901234567"}])

        conn.close()

    # ── Audit log ─────────────────────────────────────────────
    if res == "audit-log":
        return _ok([
            {"id":"a-1","user_name":"Demo Kassir","entity_type":"sale","action":"created",
             "after_state":{"total":"50000"},"created_at":_now()},
            {"id":"a-2","user_name":"Demo Menejer","entity_type":"product","action":"updated",
             "after_state":{"price":"15000"},"created_at":_now()},
        ])

    # ══════════════════════════════════════════════════════════
    # ── NASIYA / QARZ MODULI ──────────────────────────────────
    # ══════════════════════════════════════════════════════════
    if res == "debtors":
        conn = _db()

        # GET /api/v1/debtors — ro'yxat
        if method == "GET" and len(parts) == 3:
            q = params.get("q","")
            if q:
                rows = _rows(conn.execute(
                    "SELECT * FROM debtors WHERE name LIKE ? OR phone LIKE ? ORDER BY total_debt DESC",
                    (f"%{q}%", f"%{q}%")
                ))
            else:
                rows = _rows(conn.execute(
                    "SELECT * FROM debtors ORDER BY total_debt DESC"
                ))
            # Har bir qarzdor uchun qarzlar sonini qo'shamiz
            for r in rows:
                r["debt_count"] = conn.execute(
                    "SELECT COUNT(*) FROM debts WHERE debtor_id=? AND status='active'",
                    (r["id"],)
                ).fetchone()[0]
            conn.close()
            return _ok(rows)

        # POST /api/v1/debtors — yangi qarzdor
        if method == "POST" and len(parts) == 3:
            did = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO debtors VALUES (?,?,?,?,?,?,?)",
                (did, body.get("full_name",""), body.get("phone",""),
                 body.get("address",""), 0, _now(), body.get("notes",""))
            )
            conn.commit()
            row = dict(conn.execute("SELECT * FROM debtors WHERE id=?",(did,)).fetchone())
            conn.close()
            return _ok(row, 201)

        # GET /api/v1/debtors/{id} — tafsilot
        if method == "GET" and len(parts) == 4:
            did = parts[3]
            row = conn.execute("SELECT * FROM debtors WHERE id=?",(did,)).fetchone()
            if not row: conn.close(); return _err("Topilmadi", 404)
            data = dict(row)
            data["debts"] = _rows(conn.execute(
                "SELECT * FROM debts WHERE debtor_id=? ORDER BY created_at DESC",(did,)
            ))
            data["payments"] = _rows(conn.execute(
                "SELECT * FROM debt_payments WHERE debtor_id=? ORDER BY paid_at DESC LIMIT 20",(did,)
            ))
            conn.close()
            return _ok(data)

        # PUT /api/v1/debtors/{id} — tahrirlash
        if method == "PUT" and len(parts) == 4:
            did = parts[3]
            fields, vals = [], []
            for f in ("full_name","phone","address","notes"):
                if f in body:
                    fields.append(f"{f}=?"); vals.append(body[f])
            if fields:
                conn.execute(f"UPDATE debtors SET {','.join(fields)} WHERE id=?",(*vals,did))
                conn.commit()
            row = conn.execute("SELECT * FROM debtors WHERE id=?",(did,)).fetchone()
            conn.close()
            return _ok(dict(row)) if row else _err("Topilmadi",404)

        # DELETE /api/v1/debtors/{id}
        if method == "DELETE" and len(parts) == 4:
            did = parts[3]
            conn.execute("UPDATE debts SET status='cancelled' WHERE debtor_id=? AND status='active'",(did,))
            conn.execute("DELETE FROM debtors WHERE id=?",(did,))
            conn.commit(); conn.close()
            return _ok({"message":"O'chirildi"})

        conn.close()

    # ── Qarzlar ──────────────────────────────────────────────
    if res == "debts":
        conn = _db()

        # POST /api/v1/debts — yangi qarz qo'shish
        if method == "POST" and len(parts) == 3:
            debt_id  = str(uuid.uuid4())
            debtor_id = body.get("debtor_id","")
            amount   = float(body.get("amount", 0))
            paid     = float(body.get("paid_amount", 0))
            conn.execute(
                "INSERT INTO debts VALUES (?,?,?,?,?,?,?,?,?,?)",
                (debt_id, debtor_id, body.get("sale_id"), amount, paid,
                 amount - paid, body.get("description","Nasiya"),
                 "active", body.get("due_date"), _now())
            )
            # Qarzdorning umumiy qarzini yangilash
            conn.execute(
                "UPDATE debtors SET total_debt = total_debt + ? WHERE id=?",
                (amount - paid, debtor_id)
            )
            conn.commit()
            row = dict(conn.execute("SELECT * FROM debts WHERE id=?",(debt_id,)).fetchone())
            conn.close()
            return _ok(row, 201)

        # GET /api/v1/debts — barcha faol qarzlar
        if method == "GET" and len(parts) == 3:
            status_filter = params.get("status","active")
            rows = _rows(conn.execute("""
                SELECT d.*, dr.full_name as debtor_name, dr.phone as debtor_phone
                FROM debts d
                JOIN debtors dr ON d.debtor_id = dr.id
                WHERE d.status = ?
                ORDER BY d.created_at DESC
            """, (status_filter,)))
            conn.close()
            return _ok(rows)

        # POST /api/v1/debts/{id}/pay — qarzni to'lash
        if method == "POST" and len(parts) == 5 and parts[4] == "pay":
            debt_id = parts[3]
            pay_amount = float(body.get("amount", 0))
            note   = body.get("note","")
            pmethod = body.get("payment_method","cash")

            debt = conn.execute("SELECT * FROM debts WHERE id=?",(debt_id,)).fetchone()
            if not debt: conn.close(); return _err("Qarz topilmadi",404)
            debt = dict(debt)

            # To'lov miqdori qarzdan oshmasin
            actual_pay = min(pay_amount, debt["remaining"])
            new_paid   = debt["paid_amount"] + actual_pay
            new_remain = debt["remaining"]   - actual_pay
            new_status = "paid" if new_remain <= 0 else "active"

            conn.execute(
                "UPDATE debts SET paid_amount=?, remaining=?, status=? WHERE id=?",
                (new_paid, new_remain, new_status, debt_id)
            )
            # To'lov tarixi
            conn.execute(
                "INSERT INTO debt_payments VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), debt_id, debt["debtor_id"],
                 actual_pay, pmethod, note, _now())
            )
            # Qarzdorning umumiy qarzini kamaytirish
            conn.execute(
                "UPDATE debtors SET total_debt = MAX(0, total_debt - ?) WHERE id=?",
                (actual_pay, debt["debtor_id"])
            )
            conn.commit()

            updated = dict(conn.execute("SELECT * FROM debts WHERE id=?",(debt_id,)).fetchone())
            debtor  = dict(conn.execute("SELECT * FROM debtors WHERE id=?",(debt["debtor_id"],)).fetchone())
            conn.close()

            receipt_num = _receipt().replace("PK-","NAS-")
            return _ok({
                "debt":       updated,
                "debtor":     debtor,
                "paid":       actual_pay,
                "receipt_number": receipt_num,
                "message":    "Qarz to'liq yopildi ✅" if new_status == "paid" else f"Qoldiq: {int(new_remain):,} so'm"
            })

        conn.close()

    # ── Statistika ────────────────────────────────────────────
    if res == "debt-stats":
        conn = _db()
        row = conn.execute("""
            SELECT
                COUNT(*) as total_debtors,
                SUM(total_debt) as total_debt_amount,
                (SELECT COUNT(*) FROM debts WHERE status='active') as active_debts,
                (SELECT COUNT(*) FROM debts WHERE status='paid') as paid_debts,
                (SELECT COALESCE(SUM(amount),0) FROM debt_payments) as total_collected
            FROM debtors WHERE total_debt > 0
        """).fetchone()
        conn.close()
        return _ok(dict(row))

    return _err(f"'{path}' topilmadi", 404)



# ══════════════════════════════════════════════════════════════
# 3. HTTP Handler
# ══════════════════════════════════════════════════════════════
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {self.command:6} {self.path}  →  {fmt%args}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,PATCH,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization,X-Tenant-ID")

    def _send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, content: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._cors()
        self.end_headers()
        self.wfile.write(content)

    def _parse(self):
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))
        body   = {}
        n = int(self.headers.get("Content-Length", 0))
        if n:
            try: body = json.loads(self.rfile.read(n))
            except Exception: body = {}
        return parsed.path, params, body

    def _dispatch(self, method):
        path, params, body = self._parse()

        # UI sahifalar
        if path in ("/", "/pos", "/admin", "/login"):
            idx = os.path.join(STATIC, "index.html")
            with open(idx, "rb") as f:
                self._send_html(f.read())
            return

        # API
        if path.startswith("/api/") or path == "/health":
            try:
                status, data = handle_api(method, path, body, params)
            except Exception as e:
                import traceback; traceback.print_exc()
                status, data = 500, {"error": str(e)}
            self._send_json(status, data)
            return

        self._send_json(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):    self._dispatch("GET")
    def do_POST(self):   self._dispatch("POST")
    def do_PUT(self):    self._dispatch("PUT")
    def do_DELETE(self): self._dispatch("DELETE")
    def do_PATCH(self):  self._dispatch("PATCH")



# ══════════════════════════════════════════════════════════════
# 4. Main
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("━" * 55)
    print("  PossKassa Demo Server — ishga tushmoqda")
    print("━" * 55)

    os.makedirs(STATIC, exist_ok=True)
    init_db()

    # Port band bo'lsa, avtomatik keyingi bo'sh portni topish
    actual_port = PORT
    for try_port in range(PORT, PORT + 20):
        try:
            socketserver.TCPServer.allow_reuse_address = True
            test_srv = socketserver.TCPServer(("", try_port), Handler)
            actual_port = try_port
            break
        except OSError:
            print(f"  ⚠️  Port {try_port} band, {try_port+1} sinab ko'rilmoqda...")
            continue
    else:
        print("❌ Hech qanday port bo'sh emas!"); sys.exit(1)

    with test_srv as srv:
        print(f"  UI:  http://localhost:{actual_port}/")
        print(f"  API: http://localhost:{actual_port}/api/v1/")
        print(f"  Foydalanish endpointlari:")
        print(f"    GET  /api/v1/products")
        print(f"    POST /api/v1/products")
        print(f"    POST /api/v1/sales")
        print(f"    GET  /api/v1/dashboard")
        print(f"    GET  /api/v1/reports/sales-summary")
        print(f"    GET  /api/v1/reports/top-products")
        print(f"    GET  /api/v1/reports/abc-analysis")
        print(f"    GET  /api/v1/reports/margin")
        print(f"    POST /api/v1/intake/csv")
        print(f"    POST /api/v1/auth/token")
        print("━" * 55)
        print("  To'xtatish: Ctrl+C")
        print()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server to'xtatildi.")


# ══════════════════════════════════════════════════════════════
# 4. Main
