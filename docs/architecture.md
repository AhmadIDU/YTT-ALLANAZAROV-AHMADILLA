# PossKassa — Tizim Arxitekturasi

## 1. Yuqori Darajadagi Komponent Diagrammasi

```mermaid
graph TB
    subgraph "Mijoz Qatlami (Client Layer)"
        POS["Kassa Terminali\n(React/TS + SQLite)\nOflayn-birinchi"]
        BO["Backoffice Paneli\n(React/TS)\nMenejer/Admin"]
        OA["Egasi Ilovasi\n(React Native)\nReal-vaqt ko'rsatkichlar"]
        CFD["Mijoz Displeyi\n(2-ekran)\nJami + QR to'lov"]
    end

    subgraph "API Gateway / BFF"
        GW["API Gateway\n(FastAPI)\n• JWT tekshirish\n• Tenant aniqlash\n• Tezlik cheklash\n• Yo'naltirish"]
    end

    subgraph "Asosiy Xizmatlar (Core Services)"
        SVC_SALES["Sotuv va To'lovlar\n• Kassada sotish\n• Qaytarish/Refund\n• Smena boshqaruvi\n• To'lov usullari"]
        SVC_INV["Tovar va Ombor\n• Mahsulot katalogi\n• Zaxira darajalari\n• Ko'p omborxona\n• Xarid buyurtmalari"]
        SVC_INTAKE["Tovar Qabuli (Kirim)\n• Foto OCR (LLM)\n• CSV/Excel import\n• ESF pull\n• Inson tekshiruvi"]
        SVC_COMP["Muvofiqlik\n• OFD/soliq.uz\n• ESF didox.uz\n• E-IMZO imzolash"]
        SVC_ANALYTICS["Tahlil va Admin\n• Hisobotlar\n• Foydalanuvchilar/RBAC\n• Chegirmalar/Aksiyalar\n• Audit jurnali"]
        SVC_NOTIF["Bildirishnomalar\n• SMS (Eskiz)\n• Telegram Bot\n• Push (FCM)"]
    end

    subgraph "Ma'lumotlar Qatlami (Data Layer)"
        PG[("PostgreSQL 16\nAsosiy OLTP")]
        RD[("Redis 7\nKesh + Sessiyalar")]
        CH[("ClickHouse 24\nTahlil / Hisobotlar")]
        MQ["RabbitMQ 3.13\nAsinxron voqealar\n+ Oflayn sinxronizatsiya"]
        S3["MinIO / S3\nCheklar, Rasmlar\nExportlar"]
        SQLITE[("SQLite\nKassa lokal bazasi")]
    end

    subgraph "Tashqi Integratsiyalar (O'zbekiston)"
        OFD["OFD / soliq.uz\n(Fiskallashtirish)"]
        PAYME["Payme / Click\n/ Uzum QR"]
        UZCARD["Uzcard / Humo\n(Ekvayring)"]
        DIDOX["didox.uz / Faktura.uz\n(ESF)"]
        EIMZO["E-IMZO\n(Raqamli imzo)"]
        ESKIZ["Eskiz / Play Mobile\n(SMS)"]
        TG["Telegram Bot API"]
    end

    POS -->|HTTPS + sinxron navbat| GW
    BO --> GW
    OA --> GW
    POS <-->|lokal| SQLITE

    GW --> SVC_SALES
    GW --> SVC_INV
    GW --> SVC_INTAKE
    GW --> SVC_COMP
    GW --> SVC_ANALYTICS
    GW --> SVC_NOTIF

    SVC_SALES --> PG
    SVC_SALES --> RD
    SVC_SALES --> MQ
    SVC_INV --> PG
    SVC_INV --> RD
    SVC_INTAKE --> PG
    SVC_INTAKE --> S3
    SVC_COMP --> PG
    SVC_COMP --> S3
    SVC_ANALYTICS --> PG
    SVC_ANALYTICS --> CH
    SVC_NOTIF --> RD

    SVC_COMP --> OFD
    SVC_SALES --> PAYME
    SVC_SALES --> UZCARD
    SVC_INTAKE --> DIDOX
    SVC_COMP --> DIDOX
    SVC_COMP --> EIMZO
    SVC_NOTIF --> ESKIZ
    SVC_NOTIF --> TG

    MQ -->|sinxron voqealar| SVC_SALES
    MQ -->|sinxron voqealar| SVC_INV
```

---

## 2. Oflayn-Birinchi Sinxronizatsiya Arxitekturasi

```mermaid
sequenceDiagram
    participant Kassir as Kassa Terminali
    participant LocalDB as SQLite (lokal)
    participant SyncWorker as Sinxron Ishchi (fon)
    participant MQ as RabbitMQ
    participant Server as Sotuv Xizmati

    Note over Kassir,LocalDB: OFLAYN REJIM
    Kassir->>LocalDB: Sotuvni yoz (holat=sinxron_kutmoqda)
    LocalDB-->>Kassir: Tasdiqlash (darhol)
    Kassir->>Kassir: Lokal shablondan chek chiqar

    Note over SyncWorker,Server: INTERNET QAYTA ULANDI
    SyncWorker->>LocalDB: Sinxron_kutmoqda yozuvlarni tekshir
    LocalDB-->>SyncWorker: Sinxronlanmagan sotuvlar to'plami
    SyncWorker->>MQ: sinxron_paket voqeasini yuborish
    MQ->>Server: sinxron_paketni qabul qilish
    Server->>Server: Tekshirish + takrorlanishni oldini olish (idempotency kalit)
    Server->>Server: OFD orqali fiskallash
    Server-->>MQ: Tasdiqlash + fiskal chek
    MQ-->>SyncWorker: Chek + masofaviy_id
    SyncWorker->>LocalDB: Holatni yangilash=sinxronlandi, masofaviy_id saqlash
```

---

## 3. Tovar Qabuli (Kirim) Quvuri

```mermaid
flowchart TD
    A([Kirimni Boshlash]) --> B{Kiritish Usuli}
    B -->|📷 Foto| C[Rasmni S3 ga yuklash]
    B -->|📊 CSV/Excel| D[pandas/openpyxl bilan tahlil]
    B -->|🧾 ESF/didox| E[didox API orqali olish]

    C --> F[Claude Vision LLM\nqatorlarni JSON ga aylantirish]
    D --> G[Ustun moslash\nyetkazuvchi shabloni]
    E --> H[Tayyor tuzilmali ma'lumot\nOCR shart emas]

    F --> I[Standart formatga\nnormalizatsiya]
    G --> I
    H --> I

    I --> J[Mahsulot Moslashtirish Mexanizmi]
    J -->|Shtrixkod topildi| K[Mavjud SKU ga moslashtirish]
    J -->|Yangi shtrixkod| L[Yangi mahsulot loyihasi yaratish]
    J -->|Shtrixkod yo'q| M[Nom bo'yicha fuzzy qidirish\nvariantlar taklif etish]

    K --> N[Inson Tekshiruvi Interfeysi\n📋 Jadval ko'rinishida tekshirish]
    L --> N
    M --> N[Inson tanlaydi yoki yaratadi]

    N -->|❌ Rad etish| O[O'chirish / tuzatib qayta yuborish]
    N -->|✅ Tasdiqlash| P[Ma'lumotlar bazasiga saqlash]

    P --> Q[stock_receipt yaratish\nkirim hujjati]
    Q --> R[Inventarizatsiyani yangilash\nzaxira darajalari]
    R --> S[Tannarxni belgilash\nmarjinallikni hisoblash]
    S --> T([Bajarildi ✅])

    style N fill:#ff9,stroke:#f90,color:#000
    style P fill:#9f9,stroke:#090,color:#000
```

---

## 4. Ko'p Ijarachilik (Multi-Tenant) Arxitekturasi

Har bir so'rov quyidagilarni o'z ichiga oladi:
1. **JWT** (Keycloak dan) — `tenant_id`, `user_id`, `rollar` mavjud
2. **API Gateway** tenant ni JWT dan aniqlaydi, `X-Tenant-ID` sarlavhasini qo'shadi
3. **Barcha DB so'rovlari** SQLAlchemy event hook orqali `WHERE tenant_id = :tid` sharti bilan amalga oshiriladi
4. **PostgreSQL RLS (Qator Darajasida Xavfsizlik)** — ikkinchi qatlam himoyasi

```sql
-- Misol RLS siyosati
CREATE POLICY tenant_isolation ON sales
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

---

## 5. RBAC Rollari va Ruxsatlar

| Amal | Kassir | Menejer | Admin | Egasi |
|------|--------|---------|-------|-------|
| Sotuv yaratish | ✅ | ✅ | ✅ | ✅ |
| Qaytarish/Refund | ❌ | ✅ | ✅ | ✅ |
| Smenani ochish/yopish | ✅ | ✅ | ✅ | ✅ |
| Hisobotlarni ko'rish | ❌ | ✅ | ✅ | ✅ |
| Mahsulotlarni boshqarish | ❌ | ✅ | ✅ | ✅ |
| Tovar qabuli (kirim) | ❌ | ✅ | ✅ | ✅ |
| Foydalanuvchilarni boshqarish | ❌ | ❌ | ✅ | ✅ |
| Tenant boshqarish | ❌ | ❌ | ❌ | ✅ |
| Audit jurnalini ko'rish | ❌ | ❌ | ✅ | ✅ |
| Integratsiyalarni sozlash | ❌ | ❌ | ✅ | ✅ |

---

## 6. Ma'lumotlar Oqimi — Sotuv Amali

```mermaid
sequenceDiagram
    participant K as Kassir
    participant POS as Kassa Terminali
    participant GW as API Gateway
    participant SS as Sotuv Xizmati
    participant IS as Tovar Xizmati
    participant CS as Muvofiqlik
    participant OFD as OFD/soliq.uz
    participant NS as Bildirishnomalar

    K->>POS: Mahsulot qo'shish (shtrixkod)
    POS->>POS: Lokal DB dan mahsulot olish
    K->>POS: To'lovni tasdiqlash
    POS->>LocalDB: Sotuvni lokal saqlash
    POS->>GW: POST /api/v1/sales (JWT bilan)
    GW->>SS: So'rovni yo'naltirish
    SS->>IS: Zaxirani kamaytirish
    SS->>CS: Fiskal chek so'rash
    CS->>OFD: Chekni ro'yxatdan o'tkazish
    OFD-->>CS: Fiskal raqam
    CS-->>SS: Fiskal tasdiqlash
    SS-->>GW: Sotuv yaratildi + fiskal chek URL
    GW-->>POS: 201 Created
    POS->>POS: Chekni chop etish
    SS->>NS: sotuv_yaratildi voqeasi
    NS->>K: SMS/Telegram tasdiq
```
