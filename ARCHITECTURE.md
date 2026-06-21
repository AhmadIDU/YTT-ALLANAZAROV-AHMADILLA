# PossKassa — Tizim Arxitekturasi

## 1. Umumiy Ko'rinish

```
┌─────────────────────────────────────────────────────────────┐
│                     MIJOZ QATLAMI                           │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────────────────┐   │
│  │  Kassa Terminali │    │    Backoffice / Manager      │   │
│  │  (POS)           │    │    Web Panel                 │   │
│  │  localhost:3500  │    │    localhost:3500            │   │
│  │                  │    │                              │   │
│  │  • Oflayn-birinchi    │  • Dashboard                │   │
│  │  • SQLite local  │    │  • Mahsulotlar CRUD         │   │
│  │  • Sinxronizatsiya    │  • Fermalar moduli          │   │
│  │  • Chek chop etish    │  • Qarzdorlar               │   │
│  └──────────────────┘    │  • Tovar qabuli (OCR)       │   │
│                          │  • Hisobotlar               │   │
│                          └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API QATLAMI                              │
│              server.py (Python HTTP)                        │
│              Port: 3500                                     │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
        ┌───────────────────┐  ┌─────────────────────┐
        │   SQLite (lokal)  │  │   MySQL (server)    │
        │   posskassa.db    │  │   phpMyAdmin / ytt  │
        └───────────────────┘  └─────────────────────┘
```

---

## 2. Jadvallar (ERD)

| Jadval | Tavsif |
|--------|--------|
| `products` | Mahsulotlar katalogi |
| `sales` | Sotuvlar |
| `sale_items` | Sotuv qatorlari |
| `debtors` | Qarzdorlar |
| `debts` | Qarzlar |
| `debt_payments` | Qarz to'lovlari |
| `farms` | Fermer xo'jaliklari |
| `farm_debts` | Ferma qarzlari |
| `farm_payments` | Ferma to'lovlari |
| `farm_supplies` | Ferma yetkazmalari |
| `farm_supply_items` | Yetkazma qatorlari |
| `intake_drafts` | Tovar qabuli loyihalari |

---

## 3. API Endpointlar

### Autentifikatsiya
- `POST /api/v1/auth/token`

### Mahsulotlar
- `GET /api/v1/products`
- `POST /api/v1/products`
- `PUT /api/v1/products/{id}`
- `DELETE /api/v1/products/{id}`
- `GET /api/v1/products/barcode/{code}`
- `GET /api/v1/products/low-stock`

### Sotuvlar
- `GET /api/v1/sales`
- `POST /api/v1/sales`
- `POST /api/v1/sales/sync` (oflayn sinxronizatsiya)

### Qarzdorlar
- `GET /api/v1/debtors`
- `POST /api/v1/debtors`
- `GET /api/v1/debtors/{id}`
- `POST /api/v1/debts`
- `POST /api/v1/debts/{id}/pay`
- `GET /api/v1/debt-stats`

### Fermalar
- `GET /api/v1/farms`
- `POST /api/v1/farms`
- `GET /api/v1/farms/{id}`
- `POST /api/v1/farm-debts`
- `POST /api/v1/farm-debts/{id}/pay`
- `POST /api/v1/farm-debts/{farm_id}/pay-all` ⭐ Barcha qarzni yopish
- `POST /api/v1/farm-supplies`
- `GET /api/v1/farm-stats`

### Tovar Qabuli
- `POST /api/v1/intake/photo` (Claude Vision OCR)
- `POST /api/v1/intake/csv`
- `POST /api/v1/intake/esf`
- `GET /api/v1/intake/drafts`
- `POST /api/v1/intake/drafts/{id}/approve`
- `POST /api/v1/intake/drafts/{id}/reject`

### Hisobotlar
- `GET /api/v1/dashboard`
- `GET /api/v1/reports/sales-summary`
- `GET /api/v1/reports/top-products`
- `GET /api/v1/reports/abc-analysis`
- `GET /api/v1/reports/margin`
- `GET /api/v1/reports/cashier-performance`
- `GET /api/v1/reports/stock-value`
- `GET /api/v1/audit-log`

---

## 4. Asosiy Ma'lumotlar Oqimi

### Sotuv
```
Kassir → Mahsulot qidirish → Savatcha → To'lov →
completeSale() → POST /api/v1/sales → DB → Chek ✅
```

### Nasiya
```
Kassir → "Nasiya" tugmasi → Qarzdor tanlash →
POST /api/v1/sales + POST /api/v1/debts → Nasiya cheki ✅
```

### Ferma Hisob-kitobi
```
POST /api/v1/farm-supplies → Yetkazma yoziladi →
POST /farm-debts/{id}/pay-all → Barcha qarz yopiladi → Chek ✅
```

### Tovar Qabuli (OCR)
```
Rasm → base64 → Claude Vision API → JSON →
Inson tekshiruvi → Tasdiqlash → Mahsulotlar DB ga ✅
```

---

## 5. Texnologiyalar

| Qatlam | Texnologiya |
|--------|-------------|
| Backend | Python 3.14, http.server |
| Frontend | HTML5, CSS3, Vanilla JS |
| DB (lokal) | SQLite (posskassa.db) |
| DB (server) | MySQL + phpMyAdmin |
| OCR | Claude Vision API |
| Deployment | localhost:3500 |

---

## 6. Ishga Tushirish

```bash
# SQLite bilan (oddiy, tavsiya etiladi):
py -3.14 server.py 3500

# MySQL bilan:
py -3.14 server.py 3500 mysql

# Brauzerda:
http://localhost:3500
```

---

## 7. Fayl Tuzilmasi

```
YTT-ALLANAZAROV-AHMADILLA/
├── server.py          # Backend + API (Python)
├── static/
│   └── index.html     # Frontend UI (HTML/CSS/JS)
├── posskassa.db       # SQLite database (avtomatik)
├── ARCHITECTURE.md    # Shu hujjat
└── .gitignore
```
