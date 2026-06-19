# PossKassa — Kassa va ERP Tizimi

**PossKassa** — O'zbekiston va Markaziy Osiyo uchun yaratilgan, oflayn-birinchi (offline-first), bulutli kassa va yengil ERP tizimi. Mini-marketlar, oziq-ovqat do'konlari, kafe va dorixonalar uchun mo'ljallangan.

---

## Tez Ishga Tushirish

```bash
# Klonlash va boshlash
git clone https://github.com/your-org/posskassa.git
cd posskassa
cp .env.example .env          # maxfiy kalitlarni to'ldiring
docker compose up -d          # infratuzilmani ishga tushiring (postgres, redis, clickhouse, rabbitmq, minio, keycloak)
make migrate                  # ma'lumotlar bazasi migratsiyalarini ishga tushiring
make dev                      # barcha xizmatlarni ishga tushiring
```

---

## Monorepo Tuzilmasi

```
posskassa/
├── apps/
│   ├── pos-terminal/       # Kassir terminali (React + TypeScript, oflayn-birinchi)
│   ├── backoffice/         # Menejer/Admin veb paneli (React + TypeScript)
│   └── owner-app/          # Egasi uchun mobil ilova (React Native)
├── services/
│   ├── gateway/            # API Gateway / BFF (FastAPI)
│   ├── sales/              # Sotuv va To'lovlar xizmati (FastAPI)
│   ├── inventory/          # Tovar va Ombor xizmati (FastAPI)
│   ├── compliance/         # Fiskallashtirish, ESF, E-IMZO (FastAPI)
│   ├── intake/             # Tovar qabul qilish moduli (FastAPI)
│   ├── analytics/          # Hisobotlar va Tahlil (FastAPI)
│   └── notifications/      # SMS, Telegram, Push (FastAPI)
├── shared/
│   ├── python/             # Umumiy Python kutubxonalari (auth, modellar, db, voqealar)
│   └── types/              # Umumiy TypeScript turlari
├── infra/
│   ├── docker/             # Har bir xizmat uchun Dockerfile
│   ├── k8s/                # Kubernetes manifestlari
│   └── nginx/              # Teskari proksi konfiguratsiyasi
├── docs/                   # Arxitektura, ERD, API hujjatlari
└── scripts/                # Dev, migratsiya, seed skriptlari
```

---

## Asosiy Imkoniyatlar

| Imkoniyat | Tavsif |
|-----------|--------|
| 🔌 **Oflayn-birinchi kassa** | Internet yo'q bo'lganda ham sotuv amalga oshiriladi, internet kelganda sinxronlanadi |
| 🏢 **Ko'p ijarachilik (Multi-tenant)** | Bir tizimda ko'p do'kon, qat'iy ma'lumotlar izolyatsiyasi |
| 🧾 **O'zbekiston qonunchiligi** | OFD/soliq.uz fiskal cheklar, ESF didox.uz, E-IMZO raqamli imzo |
| 👥 **Rol asosida huquqlar (RBAC)** | Kassir / Menejer / Admin / Egasi rollari |
| 📦 **Tovar qabuli (Kirim)** | Foto OCR, CSV/Excel import, ESF pull → inson tekshiruvi → tasdiqlash |
| 💳 **To'lov usullari** | Naqd, Uzcard/Humo, Payme/Click/Uzum QR |
| 📊 **Tahlil va Hisobotlar** | Kunlik/oylik daromad, ABC tahlil, marjinallik, eng ko'p sotiladigan tovarlar |
| 🔔 **Bildirishnomalar** | SMS (Eskiz), Telegram Bot, Push xabarnomalar |

---

## Texnologiyalar To'plami

| Qatlam | Texnologiya |
|--------|-------------|
| Kassa / Backoffice Frontend | React 18 + TypeScript + Vite + Zustand |
| Oflayn saqlash (Kassa) | SQLite (sql.js) + Dexie.js (IndexedDB) |
| Backend xizmatlar | Python 3.12 + FastAPI + SQLAlchemy 2.0 |
| Autentifikatsiya | Keycloak 23 + JWT |
| Asosiy ma'lumotlar bazasi | PostgreSQL 16 |
| Kesh / Sessiyalar | Redis 7 |
| Tahlil bazasi | ClickHouse 24 |
| Fayl saqlash | MinIO (S3 mos) |
| Xabar navbati | RabbitMQ 3.13 |
| Infratuzilma | Docker + Kubernetes (Helm) |
| Vizual OCR LLM | Claude claude-opus-4-5 Vision API |

---

## Xizmatlar Portlari (lokal ishlab chiqish)

| Xizmat | Port |
|--------|------|
| API Gateway | :8000 |
| Sotuv xizmati | :8001 |
| Tovar xizmati | :8002 |
| Compliance xizmati | :8003 |
| Tovar qabuli | :8004 |
| Tahlil xizmati | :8005 |
| Bildirishnomalar | :8006 |
| Kassa terminali | :3000 |
| Backoffice panel | :3001 |
| Keycloak | :8080 |
| PostgreSQL | :5432 |
| Redis | :6379 |
| ClickHouse | :8123 |
| RabbitMQ UI | :15672 |
| MinIO Console | :9001 |
