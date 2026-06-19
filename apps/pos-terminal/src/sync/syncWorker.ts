/**
 * PossKassa Sinxronizatsiya Ishchisi
 * Oflayn saqlangan sotuvlarni serverga yuboradi
 * Fon jarayoni sifatida ishlaydi
 */
import { db } from '../db/localDatabase';
import { apiClient } from '../utils/apiClient';
import type { LocalSale } from '../types';

const SYNC_INTERVAL_MS = 15_000;   // har 15 soniyada
const MAX_BATCH_SIZE   = 50;        // bir paketda max sotuv soni
const MAX_ATTEMPTS     = 5;         // maksimal qayta urinish

let syncTimer: ReturnType<typeof setInterval> | null = null;
let isSyncing = false;

// -------------------------------------------------------
// Asosiy sinxronizatsiya funksiyasi
// -------------------------------------------------------
export async function runSync(): Promise<{ synced: number; failed: number }> {
  if (isSyncing) return { synced: 0, failed: 0 };
  if (!navigator.onLine) return { synced: 0, failed: 0 };

  isSyncing = true;
  let synced = 0;
  let failed = 0;

  try {
    // Sinxronlanmagan sotuvlarni olish
    const pendingSales = await db.getPendingSales();
    if (pendingSales.length === 0) return { synced: 0, failed: 0 };

    // Paketlarga bo'lish
    const batches = chunkArray(pendingSales, MAX_BATCH_SIZE);

    for (const batch of batches) {
      try {
        const result = await apiClient.post<SyncBatchResponse>(
          '/sales/sync',
          { sales: batch.map(mapSaleForServer) }
        );

        // Muvaffaqiyatli sinxronlanganlarni yangilash
        for (const syncResult of result.data.results) {
          if (syncResult.success) {
            await db.markSaleSynced(
              syncResult.local_id,
              syncResult.remote_id,
              syncResult.fiscal_url
            );
            synced++;
          } else {
            await handleSyncFailure(syncResult.local_id, batch);
            failed++;
          }
        }
      } catch (err) {
        // Butun paket muvaffaqiyatsiz bo'ldi
        for (const sale of batch) {
          await handleSyncFailure(sale.id, batch);
          failed++;
        }
        console.error('[PossKassa Sync] Paket sinxronlanmadi:', err);
      }
    }

    // Mahsulot delta sinxronizatsiyasi (server > lokal)
    await syncProductsFromServer();

  } finally {
    isSyncing = false;
  }

  return { synced, failed };
}

// -------------------------------------------------------
// Mahsulotlarni serverdan yangilash
// -------------------------------------------------------
async function syncProductsFromServer(): Promise<void> {
  try {
    const lastSync = localStorage.getItem('products_last_sync');
    const params = lastSync ? `?updated_after=${lastSync}` : '';
    const response = await apiClient.get(`/products/sync${params}`);

    if (response.data.products?.length > 0) {
      await db.bulkUpsertProducts(response.data.products);
      localStorage.setItem('products_last_sync', new Date().toISOString());
    }
  } catch {
    // Mahsulot sinxronizatsiyasi ixtiyoriy — xato bo'lsa o'tkazib yuborish
  }
}

// -------------------------------------------------------
// Yordamchi funksiyalar
// -------------------------------------------------------
async function handleSyncFailure(localId: string, batch: LocalSale[]): Promise<void> {
  const queueId = `sale_${localId}`;
  const item = await db.syncQueue.get(queueId);

  if (item && item.attempts >= MAX_ATTEMPTS) {
    // Maksimal urinishdan oshdi — failed deb belgilash
    await db.markSaleFailed(localId);
  } else {
    await db.incrementSyncAttempt(queueId);
  }
}

function mapSaleForServer(sale: LocalSale) {
  return {
    local_id:        sale.id,
    shift_id:        sale.shiftId,
    cashier_id:      sale.cashierId,
    warehouse_id:    sale.warehouseId,
    customer_id:     sale.customerId,
    receipt_number:  sale.receiptNumber,
    items:           sale.items.map(item => ({
      product_id:      item.product.id,
      quantity:        item.quantity,
      unit_price:      item.unitPrice,
      discount_amount: item.discountAmount,
      total_price:     item.totalPrice,
    })),
    payments:        sale.payments,
    subtotal:        sale.subtotal,
    discount_amount: sale.discountAmount,
    vat_amount:      sale.vatAmount,
    total_amount:    sale.totalAmount,
    sale_time:       sale.saleTime,
  };
}

function chunkArray<T>(arr: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < arr.length; i += size) {
    chunks.push(arr.slice(i, i + size));
  }
  return chunks;
}

// -------------------------------------------------------
// Sinxronizatsiya ishchisini boshqarish
// -------------------------------------------------------
export function startSyncWorker(): void {
  if (syncTimer) return;

  // Darhol bir marta ishga tushirish
  runSync();

  // Keyin davriy ravishda
  syncTimer = setInterval(runSync, SYNC_INTERVAL_MS);

  // Onlayn holatiga o'tganda darhol sinxronlash
  window.addEventListener('online', runSync);

  console.log('[PossKassa Sync] Sinxronizatsiya ishchisi boshlandi');
}

export function stopSyncWorker(): void {
  if (syncTimer) {
    clearInterval(syncTimer);
    syncTimer = null;
  }
  window.removeEventListener('online', runSync);
}

// -------------------------------------------------------
// Tip aniqlashlari
// -------------------------------------------------------
interface SyncBatchResponse {
  results: Array<{
    local_id: string;
    remote_id: string;
    success: boolean;
    fiscal_url?: string;
    error?: string;
  }>;
}
