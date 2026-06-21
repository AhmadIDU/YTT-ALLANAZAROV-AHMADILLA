-- ============================================================
-- PossKassa — MySQL ma'lumotlarini tozalash va qayta yuklash
-- phpMyAdmin da SQL tabiga kiriting va Execute bosing
-- ============================================================

-- Eski ma'lumotlarni o'chirish
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE sale_items;
TRUNCATE TABLE sales;
TRUNCATE TABLE intake_drafts;
TRUNCATE TABLE debt_payments;
TRUNCATE TABLE debts;
TRUNCATE TABLE debtors;
TRUNCATE TABLE farm_supply_items;
TRUNCATE TABLE farm_supplies;
TRUNCATE TABLE farm_payments;
TRUNCATE TABLE farm_debts;
TRUNCATE TABLE farms;
TRUNCATE TABLE products;
SET FOREIGN_KEY_CHECKS = 1;

-- Real tovarlar — Отгрузка №9315 dan (12-06-2026)
-- UUID() MySQL da ishlaydi
INSERT INTO products (id, name, barcode, unit, price, cost_price, stock_qty, is_active, created_at) VALUES
(UUID(), 'Tilton/Kachok 0.5l Choy',         '4601001', 'pcs',  16000,  12000,  10, 1, NOW()),
(UUID(), 'APREL KAITA 0.5l Shisha',          '4601002', 'pcs',  10800,   8000,  12, 1, NOW()),
(UUID(), 'Azelit Grass antilit 600ml',        '4601003', 'pcs',  23000,  17000,   2, 1, NOW()),
(UUID(), 'Novot Eryon Shirin tola 1kg',       '4601004', 'kg',  142000, 100000,   5, 1, NOW()),
(UUID(), 'Olivia Sovun 140gr',                '4601005', 'pcs', 150000, 110000,   4, 1, NOW()),
(UUID(), 'Chortoq 0.5l Shisha',               '4601006', 'pcs',  16000,  11000,  18, 1, NOW()),
(UUID(), 'APREL KAITA 900G',                  '4601007', 'pcs',  23000,  17000,   5, 1, NOW()),
(UUID(), 'Azelit Grass 600ml',                '4601008', 'pcs',  23000,  16000,   2, 1, NOW()),
(UUID(), 'Novot Eryon 1kg',                   '4601009', 'kg',  142000,  99000,   5, 1, NOW()),
(UUID(), 'Olivia Aldar Zira Choy 350g',       '4601010', 'pcs',   6800,   4800,  18, 1, NOW()),
(UUID(), 'Naturella Zelyoniy Garox 400g',     '4601011', 'pcs',  24000,  17000,   3, 1, NOW()),
(UUID(), 'Oq Qand 10kg',                      '4601012', 'kg',    7000,   5000,  15, 1, NOW()),
(UUID(), 'Bavi 70g',                          '4601013', 'pcs',   6600,   4500,  24, 1, NOW()),
(UUID(), 'Patr Pichin 4kg (karobka)',         '4601014', 'box', 130000,  95000,   2, 1, NOW()),
(UUID(), 'Angel 100gr Xamirturish (10talik)', '4601015', 'box',   5300,   3800,  20, 1, NOW()),
(UUID(), 'Orbit Sadich 408g',                 '4601016', 'pcs',  58000,  42000,   1, 1, NOW()),
(UUID(), 'Malyuk Standart 2 300g',            '4601017', 'pcs',  59000,  43000,   2, 1, NOW()),
(UUID(), 'Nutriak Kok 300g 2',               '4601018', 'pcs',  58000,  42000,   4, 1, NOW()),
(UUID(), 'TWO BITE PICHIN 2kg (karobka)',     '4601019', 'box',  52000,  38000,   2, 1, NOW()),
(UUID(), 'Ole pecheni 3.5kg (karobka)',       '4601020', 'box', 133000,  98000,   1, 1, NOW()),
(UUID(), 'Yubleyni Vafli 3kg assarti',        '4601021', 'box',  72000,  53000,   2, 1, NOW()),
(UUID(), '5+ Shkoladli Vafli 2kg (karobka)', '4601022', 'box',  96000,  70000,   1, 1, NOW()),
(UUID(), 'Tamat o\'rikzor mayda 0.43ml',      '4601023', 'pcs',  15000,  10500,  20, 1, NOW()),
(UUID(), 'BUMAGA 777 arzon',                  '4601024', 'pcs',   3500,   2500,  30, 1, NOW()),
(UUID(), 'Kristal Gel 500ml Qimmat',          '4601025', 'pcs',   9000,   6500,   2, 1, NOW()),
(UUID(), 'Mico food kukuruz 1kg',             '4601026', 'kg',   38000,  27000, 220, 1, NOW());

SELECT CONCAT('✅ Yuklandi: ', COUNT(*), ' ta mahsulot') AS natija FROM products;
SELECT CONCAT('💰 Ombor qiymati: ', FORMAT(SUM(cost_price * stock_qty), 0), ' so''m') AS qiymat FROM products;
