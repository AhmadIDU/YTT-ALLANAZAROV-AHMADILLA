"""
PossKassa — Standalone Server
MySQL (phpMyAdmin) yoki SQLite bilan ishlaydi

Ishga tushirish:
  SQLite:  python server.py 3500
  MySQL:   python server.py 3500 mysql

MySQL sozlash: server.py da DB_CONFIG ni to'ldiring
"""
import http.server
import socketserver
import json
import uuid
import os
import sys
import urllib.parse
from datetime import datetime, timezone

import sys
PORT    = int(sys.argv[1]) if len(sys.argv) > 1 else 3500
DB_MODE = sys.argv[2] if len(sys.argv) > 2 else "sqlite"  # "sqlite" yoki "mysql"
STATIC  = os.path.join(os.path.dirname(__file__), "static")

# ══════════════════════════════════════════════════════════════
# MySQL sozlamalari — shu yerni to'ldiring!
# ══════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     "127.0.0.1",
    "port":     3306,
    "user":     "user",
    "password": "",        # ← parolingiz (bo'sh bo'lsa bo'sh qoldiring)
    "database": "ytt",
    "charset":  "utf8mb4",
}

# SQLite (zaxira)
DB_PATH = os.path.join(os.path.dirname(__file__), "posskassa.db")


# ══════════════════════════════════════════════════════════════
# 1. Ma'lumotlar bazasi
# ══════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
# DB ulanish — MySQL yoki SQLite (wrapper)
# ══════════════════════════════════════════════════════════════
def _db():
    """MySQL yoki SQLite — bir xil interfeys"""
    if DB_MODE == "mysql":
        import mysql.connector
        conn = mysql.connector.connect(**DB_CONFIG)
        return _MySQLWrapper(conn)
    else:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def _rows(cursor):
    return [dict(r) for r in cursor.fetchall()]


class _MySQLWrapper:
    """MySQL ni SQLite interfeysi bilan ishlatatuvchi wrapper"""
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        mysql_sql = sql.replace("?", "%s")
        c = self._conn.cursor(dictionary=True)
        c.execute(mysql_sql, params if params else ())
        return _MySQLCursor(c)

    def commit(self):   self._conn.commit()
    def close(self):    self._conn.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()


class _MySQLCursor:
    def __init__(self, c): self._c = c
    def fetchone(self):
        r = self._c.fetchone()
        return _DictRow(r) if r else None
    def fetchall(self):
        return [_DictRow(r) for r in self._c.fetchall()]
    def __iter__(self):
        return iter(self.fetchall())
    @property
    def lastrowid(self): return self._c.lastrowid


class _DictRow(dict):
    def __getitem__(self, k):
        if isinstance(k, int): return list(self.values())[k]
        return super().__getitem__(k)
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)
    @property
    def _mapping(self): return self

# ══════════════════════════════════════════════════════════════
# 1. Ma'lumotlar bazasini yaratish
# ══════════════════════════════════════════════════════════════
# ── Jadvallar SQL ──────────────────────────────────────────────
_TABLES_SQLITE = """
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
    product_name TEXT, quantity REAL, unit_price REAL, total_price REAL
);
CREATE TABLE IF NOT EXISTS intake_drafts (
    id TEXT PRIMARY KEY, source TEXT,
    status TEXT DEFAULT 'review_pending',
    rows_json TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS debtors (
    id TEXT PRIMARY KEY, full_name TEXT NOT NULL,
    phone TEXT, address TEXT, total_debt REAL DEFAULT 0,
    created_at TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS debts (
    id TEXT PRIMARY KEY, debtor_id TEXT NOT NULL,
    sale_id TEXT, amount REAL NOT NULL,
    paid_amount REAL DEFAULT 0, remaining REAL NOT NULL,
    description TEXT, status TEXT DEFAULT 'active',
    due_date TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS debt_payments (
    id TEXT PRIMARY KEY, debt_id TEXT NOT NULL,
    debtor_id TEXT NOT NULL, amount REAL NOT NULL,
    payment_method TEXT DEFAULT 'cash', note TEXT, paid_at TEXT
);
CREATE TABLE IF NOT EXISTS farms (
    id TEXT PRIMARY KEY, name TEXT NOT NULL,
    owner_name TEXT, phone TEXT, address TEXT, region TEXT,
    farm_type TEXT DEFAULT 'general',
    total_debt REAL DEFAULT 0, total_supplied REAL DEFAULT 0,
    notes TEXT, is_active INTEGER DEFAULT 1, created_at TEXT
);
CREATE TABLE IF NOT EXISTS farm_debts (
    id TEXT PRIMARY KEY, farm_id TEXT NOT NULL,
    amount REAL NOT NULL, paid_amount REAL DEFAULT 0,
    remaining REAL NOT NULL, description TEXT,
    status TEXT DEFAULT 'active', due_date TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS farm_payments (
    id TEXT PRIMARY KEY, farm_id TEXT NOT NULL,
    farm_debt_id TEXT, amount REAL NOT NULL,
    payment_method TEXT DEFAULT 'cash', note TEXT, paid_at TEXT
);
CREATE TABLE IF NOT EXISTS farm_supplies (
    id TEXT PRIMARY KEY, farm_id TEXT NOT NULL,
    supply_number TEXT, total_amount REAL DEFAULT 0,
    payment_type TEXT DEFAULT 'cash', paid_amount REAL DEFAULT 0,
    debt_amount REAL DEFAULT 0, notes TEXT,
    supply_date TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS farm_supply_items (
    id TEXT PRIMARY KEY, supply_id TEXT NOT NULL, farm_id TEXT NOT NULL,
    product_name TEXT, quantity REAL, unit TEXT DEFAULT 'pcs',
    unit_price REAL, total_price REAL
);
"""
_TABLES_MYSQL = """
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(36) PRIMARY KEY, name VARCHAR(255) NOT NULL,
    barcode VARCHAR(100), unit VARCHAR(20) DEFAULT 'pcs',
    price DECIMAL(15,2) DEFAULT 0, cost_price DECIMAL(15,2) DEFAULT 0,
    stock_qty DECIMAL(15,3) DEFAULT 0, is_active TINYINT DEFAULT 1, created_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS sales (
    id VARCHAR(36) PRIMARY KEY, receipt_number VARCHAR(50),
    cashier VARCHAR(100) DEFAULT 'Kassir', total_amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(20) DEFAULT 'cash',
    sync_status VARCHAR(20) DEFAULT 'synced', sale_time VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS sale_items (
    id VARCHAR(36) PRIMARY KEY, sale_id VARCHAR(36), product_id VARCHAR(36),
    product_name VARCHAR(255), quantity DECIMAL(15,3),
    unit_price DECIMAL(15,2), total_price DECIMAL(15,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS intake_drafts (
    id VARCHAR(36) PRIMARY KEY, source VARCHAR(20),
    status VARCHAR(30) DEFAULT 'review_pending',
    rows_json LONGTEXT, created_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS debtors (
    id VARCHAR(36) PRIMARY KEY, full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20), address VARCHAR(255), total_debt DECIMAL(15,2) DEFAULT 0,
    created_at VARCHAR(50), notes TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS debts (
    id VARCHAR(36) PRIMARY KEY, debtor_id VARCHAR(36) NOT NULL,
    sale_id VARCHAR(36), amount DECIMAL(15,2) NOT NULL,
    paid_amount DECIMAL(15,2) DEFAULT 0, remaining DECIMAL(15,2) NOT NULL,
    description VARCHAR(255), status VARCHAR(20) DEFAULT 'active',
    due_date VARCHAR(20), created_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS debt_payments (
    id VARCHAR(36) PRIMARY KEY, debt_id VARCHAR(36) NOT NULL,
    debtor_id VARCHAR(36) NOT NULL, amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(20) DEFAULT 'cash', note TEXT, paid_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS farms (
    id VARCHAR(36) PRIMARY KEY, name VARCHAR(255) NOT NULL,
    owner_name VARCHAR(255), phone VARCHAR(20), address VARCHAR(255), region VARCHAR(100),
    farm_type VARCHAR(50) DEFAULT 'general', total_debt DECIMAL(15,2) DEFAULT 0,
    total_supplied DECIMAL(15,2) DEFAULT 0, notes TEXT,
    is_active TINYINT DEFAULT 1, created_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS farm_debts (
    id VARCHAR(36) PRIMARY KEY, farm_id VARCHAR(36) NOT NULL,
    amount DECIMAL(15,2) NOT NULL, paid_amount DECIMAL(15,2) DEFAULT 0,
    remaining DECIMAL(15,2) NOT NULL, description VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active', due_date VARCHAR(20), created_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS farm_payments (
    id VARCHAR(36) PRIMARY KEY, farm_id VARCHAR(36) NOT NULL,
    farm_debt_id VARCHAR(36), amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(20) DEFAULT 'cash', note TEXT, paid_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS farm_supplies (
    id VARCHAR(36) PRIMARY KEY, farm_id VARCHAR(36) NOT NULL,
    supply_number VARCHAR(50), total_amount DECIMAL(15,2) DEFAULT 0,
    payment_type VARCHAR(20) DEFAULT 'cash', paid_amount DECIMAL(15,2) DEFAULT 0,
    debt_amount DECIMAL(15,2) DEFAULT 0, notes TEXT,
    supply_date VARCHAR(50), created_at VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS farm_supply_items (
    id VARCHAR(36) PRIMARY KEY, supply_id VARCHAR(36) NOT NULL,
    farm_id VARCHAR(36) NOT NULL, product_name VARCHAR(255),
    quantity DECIMAL(15,3), unit VARCHAR(20) DEFAULT 'pcs',
    unit_price DECIMAL(15,2), total_price DECIMAL(15,2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

def init_db():
    if DB_MODE == "mysql":
        _init_mysql()
    else:
        _init_sqlite()


def _init_mysql():
    import mysql.connector
    conn = mysql.connector.connect(**DB_CONFIG)
    c = conn.cursor(dictionary=True)
    # MySQL da har bir CREATE TABLE alohida
    for stmt in _TABLES_MYSQL.split(";"):
        stmt = stmt.strip()
        if stmt:
            try:
                c.execute(stmt)
            except Exception as e:
                if "already exists" in str(e) or "1050" in str(e):
                    pass  # Jadval mavjud — o'tkazib yubor
                else:
                    print(f"  ⚠️  SQL xato: {e}")
    _seed_mysql(c, conn)
    conn.commit()
    conn.close()
    print(f"  DB (MySQL): {DB_CONFIG['host']}/{DB_CONFIG['database']}")


def _init_sqlite():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript(_TABLES_SQLITE)
    _seed_sqlite(c)
    conn.commit()
    conn.close()
    print(f"  DB (SQLite): {DB_PATH}")


def _seed_sqlite(c):
    """SQLite demo ma'lumotlari"""
    import sqlite3
    now = _now()
    if c.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        for p in [
            # ── Oziq-ovqat asosiy ──────────────────────────────────────
            ("Non Obi 500g",          "4600001","pcs",  3500,  2200, 120),
            ("Sut 1L Nestle",          "4600002","l",    9800,  7500,  45),
            ("Shakar 1kg",             "4600003","kg",  12000,  9000,  80),
            ("Tuxum 10 dona",          "4600004","pcs", 22000, 17000,  30),
            ("Coca-Cola 0.5L",         "4600005","pcs",  8500,  6000, 200),
            ("Makaron 500g",           "4600006","pcs",  7000,  5200,  60),
            ("Yog Oltin 1L",           "4600007","l",   28000, 22000,  25),
            ("Guruch 1kg",             "4600008","kg",  14000, 10500,  90),
            ("Mol gusht 1kg",          "4600009","kg",  75000, 60000,  15),
            ("Sabzi 1kg",              "4600010","kg",   6000,  4000, 100),
            ("Piyoz 1kg",              "4600011","kg",   4500,  3000, 150),
            ("Pomidor 1kg",            "4600012","kg",   8000,  5500,  70),
            ("Kartoshka 1kg",          "4600013","kg",   5000,  3500, 200),
            ("Choy Lipton 100g",       "4600014","pcs", 18000, 13000,  40),
            ("Qand 1kg",               "4600015","kg",  16000, 12000,  55),
            # ── Optom tovarlar (Отгрузка №9315) ───────────────────────
            ("Tilton Kachok 0.5l Choy",      "4601001","pcs", 16000, 11000,  10),
            ("APREL KAITA 0.5l Shisha",      "4601002","pcs", 10800,  7500,  12),
            ("Azelit Grass antilit 600ml",   "4601003","pcs", 23000, 16000,   2),
            ("Novot Eryon Shirin tola kg",   "4601004","pcs",142000,100000,   5),
            ("Olivia Sovun 140 gr",          "4601005","pcs",150000,110000,   4),
            ("Flecha Aldar Zira Choy 350g",  "4601006","pcs",  6800,  4800,  18),
            ("Naturella Zelyoniy Garox 400g","4601007","pcs", 24000, 17000,   3),
            ("Oq Qand 10kg",                 "4601008","kg",   7000,  5000,  15),
            ("Bavi 70g",                     "4601009","pcs",  6600,  4500,  24),
            ("Patr Pichin 4kg karobka",      "4601010","box",130000, 95000,   2),
            ("Angel 100gr Xamirturish",      "4601011","box",  5300,  3800,  20),
            ("Orbit Sadich 408g",            "4601012","pcs", 58000, 42000,   1),
            ("Malyuk Standart 2 300g",       "4601013","pcs", 59000, 43000,   2),
            ("Nutriak Kok 300g",             "4601014","pcs", 58000, 42000,   4),
            ("TWO BITE PICHIN 2kg karobka",  "4601015","box", 52000, 38000,   2),
            ("Ole pecheni 3.5kg karobka",    "4601016","box",133000, 98000,   1),
            ("Yubleyni Vafli 3kg assarti",   "4601017","box", 72000, 53000,   2),
            ("Shkoladli Vafli 2kg karobka",  "4601018","box", 96000, 70000,   1),
            ("Tamat orikzor mayda 0.43ml",   "4601019","pcs", 15000, 10500,  20),
            ("BUMAGA 777 arzon",             "4601020","pcs",  3500,  2500,  30),
            ("Kristal Gel 500ml",            "4601021","pcs",  9000,  6500,   2),
            ("Mico food kukuruz 1kg",        "4601022","kg",  38000, 27000, 220),
            ("Chortoq 0.5l Shisha Choy",     "4601023","pcs", 16000, 11000,  10),
            ("Angel Xamirturish 100g yirik", "4601024","pcs",  5300,  3800,  20),
        ]:
            c.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,1,?)",
                (str(uuid.uuid4()),p[0],p[1],p[2],p[3],p[4],p[5],now))

    if c.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 0:
        for total, method in [
            (35000,"cash"),(98500,"payme"),(22000,"cash"),
            (150000,"uzcard"),(47500,"cash"),(63000,"click"),
            (28000,"cash"),(112000,"uzcard"),(18500,"cash"),(75000,"humo"),
        ]:
            c.execute("INSERT INTO sales VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()),_receipt(),"Demo Kassir",total,method,"synced",now))

    if c.execute("SELECT COUNT(*) FROM farms").fetchone()[0] == 0:
        f1,f2,f3 = str(uuid.uuid4()),str(uuid.uuid4()),str(uuid.uuid4())
        for fid,name,owner,phone,address,region,ftype,debt,supplied in [
            (f1,"Bahor Fermer Xo'jaligi","Toshmatov Behruz","+998901112233","Sirdaryo","Sirdaryo","don",320000,1850000),
            (f2,"Yashil Vodiy FX","Rahimov Akbar","+998912223344","Farg'ona","Farg'ona","sabzavot",150000,970000),
            (f3,"Nur Agro FX","Karimov Sanjar","+998923334455","Toshkent","Toshkent","chorva",0,540000),
        ]:
            c.execute("INSERT INTO farms(id,name,owner_name,phone,address,region,farm_type,total_debt,total_supplied,notes,is_active,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,1,?)",
                (fid,name,owner,phone,address,region,ftype,debt,supplied,"",now))
        for fid,amt,paid,desc in [(f1,500000,180000,"Urug' va o'g'it"),(f2,150000,0,"Jihoz")]:
            c.execute("INSERT INTO farm_debts VALUES (?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()),fid,amt,paid,amt-paid,desc,"active",None,now))

    if c.execute("SELECT COUNT(*) FROM debtors").fetchone()[0] == 0:
        d1,d2,d3,d4 = [str(uuid.uuid4()) for _ in range(4)]
        for did,name,phone,addr,debt,note in [
            (d1,"Karimov Botir","+998901234567","Chilonzor 5",150000,"Doimiy mijoz"),
            (d2,"Rahimova Malika","+998912345678","Yunusobod 12",85000,""),
            (d3,"Toshmatov Sardor","+998923456789","Mirzo Ulugbek 3",320000,"Oylik to'laydi"),
            (d4,"Usmonov Jasur","+998934567890","Shayxontohur 7",0,""),
        ]:
            c.execute("INSERT INTO debtors VALUES (?,?,?,?,?,?,?)",
                (did,name,phone,addr,debt,now,note))
        for did,total,paid,desc in [
            (d1,150000,0,"Oziq-ovqat mahsulotlari"),
            (d2,85000,0,"Kunlik xarid"),
            (d3,500000,180000,"Oylik zakaz"),
        ]:
            c.execute("INSERT INTO debts VALUES (?,?,?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()),did,None,total,paid,total-paid,desc,"active",None,now))


def _seed_mysql(c, conn):
    """MySQL demo ma'lumotlari"""
    now = _now()

    # dictionary=True cursor yaratamiz
    c = conn.cursor(dictionary=True)

    c.execute("SELECT COUNT(*) as cnt FROM products")
    r = c.fetchone()
    if (r['cnt'] if isinstance(r, dict) else r[0]) == 0:
        for p in [
            ("Non Obi 500g","4600001","pcs",3500,2200,120),
            ("Sut 1L Nestle","4600002","l",9800,7500,45),
            ("Shakar 1kg","4600003","kg",12000,9000,80),
            ("Coca-Cola 0.5L","4600004","pcs",8500,6000,200),
            ("Makaron 500g","4600005","pcs",7000,5200,60),
            ("Guruch 1kg","4600006","kg",14000,10500,90),
            ("Sabzi 1kg","4600007","kg",6000,4000,100),
            ("Kartoshka 1kg","4600008","kg",5000,3500,200),
            ("Choy Lipton 100g","4600009","pcs",18000,13000,40),
            ("Qand 1kg","4600010","kg",16000,12000,55),
        ]:
            c.execute(
                "INSERT INTO products VALUES (%s,%s,%s,%s,%s,%s,%s,1,%s)",
                (str(uuid.uuid4()),p[0],p[1],p[2],p[3],p[4],p[5],now))

    c.execute("SELECT COUNT(*) as cnt FROM sales")
    if (lambda r: r['cnt'] if isinstance(r,dict) else r[0])(c.fetchone()) == 0:
        for total, method in [(35000,"cash"),(98500,"payme"),(22000,"cash"),
                               (150000,"uzcard"),(47500,"cash"),(63000,"click")]:
            c.execute(
                "INSERT INTO sales VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (str(uuid.uuid4()),_receipt(),"Demo Kassir",total,method,"synced",now))

    c.execute("SELECT COUNT(*) as cnt FROM farms")
    if (lambda r: r['cnt'] if isinstance(r,dict) else r[0])(c.fetchone()) == 0:
        f1,f2 = str(uuid.uuid4()),str(uuid.uuid4())
        for fid,name,owner,phone,addr,region,ftype,debt,supplied in [
            (f1,"Bahor Fermer Xo'jaligi","Toshmatov Behruz","+998901112233","Sirdaryo","Sirdaryo","don",320000,1850000),
            (f2,"Yashil Vodiy FX","Rahimov Akbar","+998912223344","Farg'ona","Farg'ona","sabzavot",150000,970000),
        ]:
            c.execute(
                "INSERT INTO farms(id,name,owner_name,phone,address,region,farm_type,total_debt,total_supplied,notes,is_active,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (fid,name,owner,phone,addr,region,ftype,debt,supplied,"",1,now))

    c.execute("SELECT COUNT(*) as cnt FROM debtors")
    if (lambda r: r['cnt'] if isinstance(r,dict) else r[0])(c.fetchone()) == 0:
        d1,d2 = str(uuid.uuid4()),str(uuid.uuid4())
        for did,name,phone,addr,debt,note in [
            (d1,"Karimov Botir","+998901234567","Chilonzor 5",150000,"Doimiy mijoz"),
            (d2,"Rahimova Malika","+998912345678","Yunusobod 12",85000,""),
        ]:
            c.execute(
                "INSERT INTO debtors VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (did,name,phone,addr,debt,now,note))
    conn.commit()






# ── Yordamchi funksiyalar ────────────────────────────────────
def _now():
    return datetime.now(timezone.utc).isoformat()

def _receipt():
    d = datetime.now().strftime("%Y%m%d")
    return f"PK-{d}-{str(uuid.uuid4())[:4].upper()}"

def _ok(data, st=200):   return st, data
def _err(msg, st=400):   return st, {"error": msg}


# ══════════════════════════════════════════════════════════════
# Claude Vision OCR — yetkazuvchi ro'yxatini rasmdan o'qish
# ══════════════════════════════════════════════════════════════
def _ocr_with_claude(image_base64: str, media_type: str = "image/jpeg") -> list:
    """
    Rasm base64 → Claude Vision → mahsulot qatorlari JSON

    Qaytaradi:
    [{"name":"...", "qty":10, "unit":"pcs", "unit_cost":5000,
      "total_cost":50000, "barcode":null, "vat_rate":12,
      "approved":True, "_match":{"action":"create_new",...}}]
    """
    import urllib.request
    import json as _json

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY topilmadi")

    prompt = """Bu rasm yetkazuvchining tovar ro'yxati yoki hisob-fakturasi.
Rasmdan barcha tovar qatorlarini ajratib, FAQAT JSON array qaytardir.

Har bir element:
{
  "name": "tovar nomi (xuddi rasmdagi kabi, o'zbek/rus tilida)",
  "barcode": null,
  "qty": miqdor_soni (raqam),
  "unit": "pcs yoki kg yoki l yoki box",
  "unit_cost": birlik_narxi_somda (raqam, vergulsiz),
  "total_cost": jami_narx (qty * unit_cost, raqam),
  "vat_rate": 12
}

QOIDALAR:
- Faqat JSON array qaytardir, hech qanday izoh yoki markdown yo'q
- Raqamlar faqat son (masalan: 5000 emas "5 000")
- O'qib bo'lmaydigan qatorlarni o'tkazib yuboring

JSON:"""

    payload = _json.dumps({
        "model": "claude-opus-4-5",
        "max_tokens": 4096,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64
                    }
                },
                {"type": "text", "text": prompt}
            ]
        }]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data    = payload,
        headers = {
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        method = "POST"
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        result = _json.loads(resp.read())

    raw_text = result["content"][0]["text"].strip()

    # JSON tozalash
    import re
    raw_text = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`")
    start = raw_text.find("[")
    end   = raw_text.rfind("]")
    if start != -1 and end != -1:
        rows = _json.loads(raw_text[start:end+1])
    else:
        rows = _json.loads(raw_text)

    # Har bir qatorni standartlashtirish
    result_rows = []
    for r in rows:
        if not isinstance(r, dict): continue
        name = str(r.get("name","")).strip()
        if not name: continue
        def _num(v, d=0):
            try: return float(str(v).replace(" ","").replace(",","."))
            except: return d
        qty       = max(0.001, _num(r.get("qty",1), 1))
        unit_cost = _num(r.get("unit_cost",0))
        total     = _num(r.get("total_cost",0)) or qty * unit_cost
        result_rows.append({
            "name":       name[:200],
            "barcode":    None,
            "qty":        qty,
            "unit":       str(r.get("unit","pcs")).lower()[:10],
            "unit_cost":  unit_cost,
            "total_cost": total,
            "vat_rate":   _num(r.get("vat_rate",12), 12),
            "approved":   True,
            "_match":     {"action":"create_new","candidates":[]}
        })
    return result_rows




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

            # ── HAQIQIY CLAUDE VISION OCR ─────────────────────
            if sub == "photo" and body.get("image_base64"):
                try:
                    rows = _ocr_with_claude(body["image_base64"], body.get("media_type","image/jpeg"))
                    conn.execute("INSERT INTO intake_drafts VALUES (?,?,?,?,?)",
                        (did, "photo", "review_pending", json.dumps(rows), _now()))
                    conn.commit(); conn.close()
                    return _ok({"draft_id":did,"status":"review_pending",
                                "rows_count":len(rows),
                                "message":f"Claude Vision {len(rows)} ta tovar aniqladi!"}, 201)
                except Exception as e:
                    # API kalit yo'q yoki xato — mock ga o'tish
                    pass

            # ── MOCK (API kalit yo'q bo'lsa) ──────────────────
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

    # ══════════════════════════════════════════════════════════
    # 🏭 FERMALAR MODULI
    # ══════════════════════════════════════════════════════════
    if res == "farms":
        conn = _db()

        # GET /api/v1/farms — ro'yxat
        if method == "GET" and len(parts) == 3:
            q = params.get("q","")
            if q:
                rows = _rows(conn.execute(
                    "SELECT * FROM farms WHERE is_active=1 AND (name LIKE ? OR owner_name LIKE ? OR phone LIKE ?)",
                    (f"%{q}%",f"%{q}%",f"%{q}%")
                ))
            else:
                rows = _rows(conn.execute(
                    "SELECT * FROM farms WHERE is_active=1 ORDER BY total_debt DESC"
                ))
            for r in rows:
                r["active_debts"] = conn.execute(
                    "SELECT COUNT(*) FROM farm_debts WHERE farm_id=? AND status='active'",(r["id"],)
                ).fetchone()[0]
                r["supply_count"] = conn.execute(
                    "SELECT COUNT(*) FROM farm_supplies WHERE farm_id=?",(r["id"],)
                ).fetchone()[0]
            conn.close(); return _ok(rows)

        # POST /api/v1/farms — yangi ferma
        if method == "POST" and len(parts) == 3:
            fid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO farms(id,name,owner_name,phone,address,region,farm_type,total_debt,total_supplied,notes,is_active,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,1,?)",
                (fid, body.get("name",""), body.get("owner_name",""),
                 body.get("phone",""), body.get("address",""),
                 body.get("region",""), body.get("farm_type","general"),
                 0, 0, body.get("notes",""), _now())
            )
            conn.commit()
            row = dict(conn.execute("SELECT * FROM farms WHERE id=?",(fid,)).fetchone())
            conn.close(); return _ok(row, 201)

        # GET /api/v1/farms/{id} — tafsilot
        if method == "GET" and len(parts) == 4:
            fid = parts[3]
            farm = conn.execute("SELECT * FROM farms WHERE id=?",(fid,)).fetchone()
            if not farm: conn.close(); return _err("Ferma topilmadi",404)
            data = dict(farm)
            data["debts"]    = _rows(conn.execute(
                "SELECT * FROM farm_debts WHERE farm_id=? ORDER BY created_at DESC",(fid,)))
            data["supplies"] = _rows(conn.execute(
                "SELECT * FROM farm_supplies WHERE farm_id=? ORDER BY supply_date DESC LIMIT 10",(fid,)))
            data["payments"] = _rows(conn.execute(
                "SELECT * FROM farm_payments WHERE farm_id=? ORDER BY paid_at DESC LIMIT 10",(fid,)))
            # Yetkazma elementlari
            for s in data["supplies"]:
                s["items"] = _rows(conn.execute(
                    "SELECT * FROM farm_supply_items WHERE supply_id=?",(s["id"],)))
            conn.close(); return _ok(data)

        # PUT /api/v1/farms/{id} — tahrirlash
        if method == "PUT" and len(parts) == 4:
            fid = parts[3]
            fields, vals = [], []
            for f in ("name","owner_name","phone","address","region","farm_type","notes"):
                if f in body: fields.append(f"{f}=?"); vals.append(body[f])
            if fields:
                conn.execute(f"UPDATE farms SET {','.join(fields)} WHERE id=?",(*vals,fid))
                conn.commit()
            row = conn.execute("SELECT * FROM farms WHERE id=?",(fid,)).fetchone()
            conn.close(); return _ok(dict(row)) if row else _err("Topilmadi",404)

        # DELETE /api/v1/farms/{id}
        if method == "DELETE" and len(parts) == 4:
            conn.execute("UPDATE farms SET is_active=0 WHERE id=?",(parts[3],))
            conn.commit(); conn.close(); return _ok({"message":"O'chirildi"})

        conn.close()

    # ── Ferma qarzlari ────────────────────────────────────────
    if res == "farm-debts":
        conn = _db()

        # POST /api/v1/farm-debts — yangi qarz
        if method == "POST" and len(parts) == 3:
            did   = str(uuid.uuid4())
            fid   = body.get("farm_id","")
            amt   = float(body.get("amount",0))
            paid  = float(body.get("paid_amount",0))
            conn.execute(
                "INSERT INTO farm_debts VALUES (?,?,?,?,?,?,?,?,?)",
                (did, fid, amt, paid, amt-paid,
                 body.get("description","Nasiya"), "active",
                 body.get("due_date"), _now())
            )
            conn.execute(
                "UPDATE farms SET total_debt=total_debt+? WHERE id=?",
                (amt-paid, fid)
            )
            conn.commit()
            row = dict(conn.execute("SELECT * FROM farm_debts WHERE id=?",(did,)).fetchone())
            conn.close(); return _ok(row, 201)

        # POST /api/v1/farm-debts/{id}/pay — to'lov
        if method == "POST" and len(parts) == 5 and parts[4] == "pay":
            did      = parts[3]
            pay_amt  = float(body.get("amount",0))
            debt     = conn.execute("SELECT * FROM farm_debts WHERE id=?",(did,)).fetchone()
            if not debt: conn.close(); return _err("Qarz topilmadi",404)
            debt = dict(debt)

            actual   = min(pay_amt, debt["remaining"])
            new_paid = debt["paid_amount"] + actual
            new_rem  = debt["remaining"]   - actual
            new_st   = "paid" if new_rem <= 0 else "active"

            conn.execute(
                "UPDATE farm_debts SET paid_amount=?,remaining=?,status=? WHERE id=?",
                (new_paid, new_rem, new_st, did)
            )
            conn.execute(
                "INSERT INTO farm_payments VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), debt["farm_id"], did,
                 actual, body.get("payment_method","cash"),
                 body.get("note",""), _now())
            )
            conn.execute(
                "UPDATE farms SET total_debt=MAX(0,total_debt-?) WHERE id=?",
                (actual, debt["farm_id"])
            )
            conn.commit()
            updated = dict(conn.execute("SELECT * FROM farm_debts WHERE id=?",(did,)).fetchone())
            farm    = dict(conn.execute("SELECT * FROM farms WHERE id=?",(debt["farm_id"],)).fetchone())
            conn.close()
            return _ok({
                "debt":     updated,
                "farm":     farm,
                "paid":     actual,
                "receipt_number": _receipt().replace("PK-","FM-"),
                "message":  "To'liq yopildi ✅" if new_st=="paid" else f"Qoldiq: {int(new_rem):,} so'm"
            })


        # POST /api/v1/farm-debts/{farm_id}/pay-all — BARCHA QARZNI YOPISH
        if method == "POST" and len(parts) == 5 and parts[4] == "pay-all":
            fid     = parts[3]  # bu holda farm_id
            pay_amt = float(body.get("amount", 0))
            method_p= body.get("payment_method","cash")
            note    = body.get("note","Barcha qarz to'landi")

            active_debts = _rows(conn.execute(
                "SELECT * FROM farm_debts WHERE farm_id=? AND status='active' ORDER BY created_at",
                (fid,)
            ))
            remaining_pay = pay_amt
            total_paid    = 0
            paid_count    = 0

            for debt in active_debts:
                if remaining_pay <= 0: break
                actual   = min(remaining_pay, debt["remaining"])
                new_paid = debt["paid_amount"] + actual
                new_rem  = debt["remaining"]   - actual
                new_st   = "paid" if new_rem <= 0 else "active"
                conn.execute(
                    "UPDATE farm_debts SET paid_amount=?,remaining=?,status=? WHERE id=?",
                    (new_paid, new_rem, new_st, debt["id"])
                )
                conn.execute(
                    "INSERT INTO farm_payments VALUES (?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), fid, debt["id"], actual, method_p, note, _now())
                )
                remaining_pay -= actual
                total_paid    += actual
                paid_count    += 1

            conn.execute(
                "UPDATE farms SET total_debt=MAX(0,total_debt-?) WHERE id=?",
                (total_paid, fid)
            )
            conn.commit()
            farm = dict(conn.execute("SELECT * FROM farms WHERE id=?",(fid,)).fetchone())
            conn.close()
            return _ok({
                "farm":           farm,
                "total_paid":     total_paid,
                "paid_count":     paid_count,
                "receipt_number": _receipt().replace("PK-","FM-"),
                "message":        f"{paid_count} ta qarz yopildi, jami {int(total_paid):,} so'm"
            })

        conn.close()

    # ── Ferma statistikasi ────────────────────────────────────
    if res == "farm-stats":
        conn = _db()
        row = conn.execute("""
            SELECT
                COUNT(*) as total_farms,
                SUM(total_debt) as total_debt,
                SUM(total_supplied) as total_supplied,
                (SELECT COUNT(*) FROM farm_debts WHERE status='active') as active_debts,
                (SELECT COALESCE(SUM(amount),0) FROM farm_payments) as total_collected
            FROM farms WHERE is_active=1
        """).fetchone()
        conn.close(); return _ok(dict(row))

    # ── Audit log ─────────────────────────────────────────────
    if res == "audit-log":        return _ok([
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


    if res == "farm-supplies":
        conn = _db()

        # POST /api/v1/farm-supplies — yangi yetkazma
        if method == "POST" and len(parts) == 3:
            sid     = str(uuid.uuid4())
            fid     = body.get("farm_id","")
            total   = float(body.get("total_amount",0))
            paid    = float(body.get("paid_amount",0))
            debt_a  = total - paid
            ptype   = body.get("payment_type","cash")
            snum    = body.get("supply_number") or _receipt().replace("PK-","YT-")

            conn.execute(
                "INSERT INTO farm_supplies VALUES (?,?,?,?,?,?,?,?,?,?)",
                (sid, fid, snum, total, ptype, paid, debt_a,
                 body.get("notes",""), _now(), _now())
            )
            # Yetkazma elementlari
            for item in body.get("items",[]):
                conn.execute(
                    "INSERT INTO farm_supply_items VALUES (?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), sid, fid,
                     item.get("product_name",""),
                     item.get("quantity",1),
                     item.get("unit","pcs"),
                     item.get("unit_price",0),
                     item.get("total_price",0))
                )
            # Ferma statistikasini yangilash
            conn.execute(
                "UPDATE farms SET total_supplied=total_supplied+?, total_debt=total_debt+? WHERE id=?",
                (total, debt_a, fid)
            )
            # Agar nasiya bo'lsa — farm_debt ham yarat
            if debt_a > 0:
                conn.execute(
                    "INSERT INTO farm_debts VALUES (?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), fid, debt_a, 0, debt_a,
                     f"Yetkazma {snum}", "active", None, _now())
                )
            conn.commit()
            row = dict(conn.execute("SELECT * FROM farm_supplies WHERE id=?",(sid,)).fetchone())
            row["items"] = _rows(conn.execute(
                "SELECT * FROM farm_supply_items WHERE supply_id=?",(sid,)))
            conn.close(); return _ok(row, 201)

        # GET /api/v1/farm-supplies?farm_id=xxx
        if method == "GET" and len(parts) == 3:
            fid = params.get("farm_id","")
            if fid:
                rows = _rows(conn.execute(
                    "SELECT * FROM farm_supplies WHERE farm_id=? ORDER BY supply_date DESC",(fid,)))
            else:
                rows = _rows(conn.execute(
                    "SELECT fs.*, f.name as farm_name FROM farm_supplies fs "
                    "JOIN farms f ON fs.farm_id=f.id ORDER BY fs.supply_date DESC LIMIT 50"))
            for r in rows:
                r["items"] = _rows(conn.execute(
                    "SELECT * FROM farm_supply_items WHERE supply_id=?",(r["id"],)))
            conn.close(); return _ok(rows)



# ══════════════════════════════════════════════════════════════
# 4. Main
# ══════════════════════════════════════════════════════════════
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



    # ── Ferma yetkazmalari ────────────────────────────────────

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
