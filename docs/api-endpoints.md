# PossKassa — REST API Endpointlari

Barcha so'rovlar `Authorization: Bearer <JWT>` sarlavhasi bilan yuboriladi.
Barcha javoblar JSON formatida qaytariladi.

**Asosiy URL:** `https://api.posskassa.uz/api/v1`

---

## 1. Autentifikatsiya (Auth)

| Metod | Endpoint | Tavsif |
|-------|----------|--------|
| POST | `/auth/token` | Login (Keycloak orqali) |
| POST | `/auth/refresh` | Tokenni yangilash |
| POST | `/auth/logout` | Chiqish |
| GET | `/auth/me` | Joriy foydalanuvchi ma'lumotlari |

---

## 2. Smenalar (Shifts)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| POST | `/shifts/open` | Smenani ochish | Kassir+ |
| POST | `/shifts/{id}/close` | Smenani yopish | Kassir+ |
| GET | `/shifts/current` | Joriy smena | Kassir+ |
| GET | `/shifts` | Smena tarixi (sahifalash) | Menejer+ |
| GET | `/shifts/{id}` | Smena tafsilotlari | Menejer+ |
| GET | `/shifts/{id}/summary` | Smena xulosasi (kassa hisoboti) | Menejer+ |

**POST /shifts/open so'rovi:**
```json
{
  "warehouse_id": "uuid",
  "opening_cash": 500000
}
```

---

## 3. Sotuvlar (Sales)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| POST | `/sales` | Yangi sotuv yaratish | Kassir+ |
| POST | `/sales/sync` | Oflayn sotuvlarni sinxronlash | Kassir+ |
| GET | `/sales` | Sotuvlar ro'yxati (filter, sahifalash) | Kassir+ |
| GET | `/sales/{id}` | Sotuv tafsilotlari | Kassir+ |
| POST | `/sales/{id}/refund` | To'liq qaytarish | Menejer+ |
| POST | `/sales/{id}/partial-refund` | Qisman qaytarish | Menejer+ |
| GET | `/sales/{id}/receipt` | Chekni olish (PDF/HTML) | Kassir+ |
| GET | `/sales/{id}/fiscal-receipt` | Fiskal chekni olish | Kassir+ |

**POST /sales so'rovi:**
```json
{
  "shift_id": "uuid",
  "warehouse_id": "uuid",
  "customer_id": "uuid|null",
  "local_id": "terminal_uuid_v4",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 2,
      "unit_price": 15000,
      "discount_amount": 0
    }
  ],
  "payments": [
    { "method": "cash", "amount": 30000 },
    { "method": "payme", "amount": 0 }
  ],
  "discount_amount": 0,
  "sale_time": "2025-01-15T10:30:00Z"
}
```

**POST /sales/sync so'rovi (paketli sinxronlash):**
```json
{
  "sales": [
    { /* sotuv obyekti 1 */ },
    { /* sotuv obyekti 2 */ }
  ]
}
```

---

## 4. Mahsulotlar (Products)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/products` | Mahsulotlar ro'yxati (qidirish, filter) | Kassir+ |
| GET | `/products/{id}` | Mahsulot tafsilotlari | Kassir+ |
| GET | `/products/barcode/{barcode}` | Shtrixkod bo'yicha qidirish | Kassir+ |
| POST | `/products` | Yangi mahsulot yaratish | Menejer+ |
| PUT | `/products/{id}` | Mahsulotni tahrirlash | Menejer+ |
| DELETE | `/products/{id}` | Mahsulotni o'chirish (soft) | Admin+ |
| GET | `/products/{id}/stock` | Mahsulot zaxiralari | Menejer+ |
| POST | `/products/search` | Kengaytirilgan qidirish | Kassir+ |

**GET /products so'rovi parametrlari:**
```
?q=non&category_id=uuid&barcode=8901234&page=1&size=50&active_only=true
```

---

## 5. Kategoriyalar (Categories)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/categories` | Kategoriyalar daraxti | Kassir+ |
| POST | `/categories` | Yangi kategoriya | Menejer+ |
| PUT | `/categories/{id}` | Tahrirlash | Menejer+ |
| DELETE | `/categories/{id}` | O'chirish | Admin+ |

---

## 6. Zaxira (Stock)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/stock` | Zaxira holati (filter) | Menejer+ |
| GET | `/stock/low` | Kam zaxira ogohlantirishlari | Menejer+ |
| POST | `/stock/adjust` | Zaxirani qo'lda moslashtirish | Admin+ |
| GET | `/stock/movements/{product_id}` | Zaxira harakatlari tarixi | Menejer+ |

---

## 7. Omborxonalar (Warehouses)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/warehouses` | Ro'yxat | Kassir+ |
| POST | `/warehouses` | Yaratish | Admin+ |
| PUT | `/warehouses/{id}` | Tahrirlash | Admin+ |

---

## 8. Tovar Qabuli — Kirim (Goods Intake)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| POST | `/intake/photo` | Foto yuklash va OCR boshlash | Menejer+ |
| POST | `/intake/csv` | CSV/Excel yuklash | Menejer+ |
| POST | `/intake/esf` | ESF raqami bo'yicha pull | Menejer+ |
| GET | `/intake/drafts` | Loyiha ro'yxati | Menejer+ |
| GET | `/intake/drafts/{id}` | Loyiha tafsilotlari (tekshiruv) | Menejer+ |
| PUT | `/intake/drafts/{id}/rows` | Tekshiruv vaqtida qatorlarni tahrirlash | Menejer+ |
| POST | `/intake/drafts/{id}/approve` | Tasdiqlash va bazaga saqlash | Menejer+ |
| POST | `/intake/drafts/{id}/reject` | Rad etish | Menejer+ |
| GET | `/intake/receipts` | Tasdiqlangan kirimlar | Menejer+ |
| GET | `/intake/receipts/{id}` | Kirim tafsilotlari | Menejer+ |

**POST /intake/photo javobi:**
```json
{
  "draft_id": "uuid",
  "status": "extracting",
  "message": "Rasm qayta ishlanmoqda, natijani /intake/drafts/{id} dan oling"
}
```

**GET /intake/drafts/{id} javobi (tekshiruv uchun):**
```json
{
  "id": "uuid",
  "status": "review_pending",
  "source": "photo",
  "rows": [
    {
      "row_index": 0,
      "name": "Non \"Obi\"",
      "barcode": "4600000123456",
      "qty": 24,
      "unit": "pcs",
      "unit_cost": 3500,
      "matched_product": {
        "id": "uuid",
        "name": "Non Obi 500g",
        "confidence": 0.97
      },
      "action": "update_stock"
    }
  ]
}
```

---

## 9. Yetkazuvchilar (Suppliers)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/suppliers` | Ro'yxat | Menejer+ |
| POST | `/suppliers` | Yaratish | Menejer+ |
| PUT | `/suppliers/{id}` | Tahrirlash | Menejer+ |
| PUT | `/suppliers/{id}/column-mapping` | CSV shablonini saqlash | Menejer+ |

---

## 10. Mijozlar (Customers)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/customers` | Ro'yxat | Menejer+ |
| GET | `/customers/{id}` | Tafsilotlar | Kassir+ |
| GET | `/customers/phone/{phone}` | Telefon bo'yicha qidirish | Kassir+ |
| POST | `/customers` | Yangi mijoz | Kassir+ |
| PUT | `/customers/{id}` | Tahrirlash | Menejer+ |
| GET | `/customers/{id}/sales` | Mijoz sotuvlari | Menejer+ |

---

## 11. Chegirmalar (Discounts)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/discounts` | Ro'yxat | Menejer+ |
| POST | `/discounts` | Yaratish | Admin+ |
| PUT | `/discounts/{id}` | Tahrirlash | Admin+ |
| DELETE | `/discounts/{id}` | O'chirish | Admin+ |
| POST | `/discounts/calculate` | Chegirmani hisoblash | Kassir+ |

---

## 12. Hisobotlar (Analytics)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/reports/sales-summary` | Sotuv xulosasi (kunlik/oylik) | Menejer+ |
| GET | `/reports/top-products` | Eng ko'p sotiladigan mahsulotlar | Menejer+ |
| GET | `/reports/revenue` | Daromad grafigi | Menejer+ |
| GET | `/reports/abc-analysis` | ABC tahlil (tovarlar bo'yicha) | Menejer+ |
| GET | `/reports/margin` | Marjinallik hisoboti | Menejer+ |
| GET | `/reports/stock-value` | Ombor qiymati hisoboti | Menejer+ |
| GET | `/reports/cashier-performance` | Kassirlar samaradorligi | Admin+ |
| POST | `/reports/export` | Excel/PDF eksport | Menejer+ |

**GET /reports/sales-summary parametrlari:**
```
?from=2025-01-01&to=2025-01-31&warehouse_id=uuid&cashier_id=uuid&group_by=day
```

---

## 13. Foydalanuvchilar (Users)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/users` | Ro'yxat | Admin+ |
| POST | `/users` | Yangi foydalanuvchi | Admin+ |
| PUT | `/users/{id}` | Tahrirlash | Admin+ |
| PUT | `/users/{id}/role` | Rolni o'zgartirish | Owner |
| POST | `/users/{id}/deactivate` | Faolsizlashtirish | Admin+ |
| GET | `/users/{id}/audit-log` | Foydalanuvchi audit jurnali | Admin+ |

---

## 14. Audit Jurnali (Audit Log)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| GET | `/audit-log` | Audit jurnali (filter) | Admin+ |
| GET | `/audit-log/{id}` | Yozuv tafsilotlari | Admin+ |

**GET /audit-log parametrlari:**
```
?entity_type=sale&entity_id=uuid&user_id=uuid&from=2025-01-01&to=2025-01-31&page=1
```

---

## 15. Fiskallashtirish (Compliance)

| Metod | Endpoint | Tavsif | Ruxsat |
|-------|----------|--------|--------|
| POST | `/compliance/fiscalize` | Chekni fiskallash | Ichki xizmat |
| GET | `/compliance/receipts/{sale_id}` | Fiskal chek holati | Kassir+ |
| POST | `/compliance/esf/create` | ESF yaratish | Menejer+ |
| GET | `/compliance/esf/{id}` | ESF holati | Menejer+ |
| POST | `/compliance/eimzo/sign` | Hujjatni imzolash | Admin+ |

---

## Xato Javoblar Formati

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Mahsulot topilmadi",
    "details": { "product_id": "uuid" }
  }
}
```

## Standart Xato Kodlari

| HTTP | Kod | Ma'no |
|------|-----|-------|
| 400 | VALIDATION_ERROR | Kiritish ma'lumotlari noto'g'ri |
| 401 | UNAUTHORIZED | Autentifikatsiya talab etiladi |
| 403 | FORBIDDEN | Ruxsat yo'q |
| 404 | NOT_FOUND | Resurs topilmadi |
| 409 | DUPLICATE_ENTRY | Takroriy yozuv (idempotency) |
| 422 | BUSINESS_RULE_ERROR | Biznes qoidasi buzildi |
| 503 | OFD_UNAVAILABLE | Fiskal server mavjud emas (oflayn rejimda saqlash) |
