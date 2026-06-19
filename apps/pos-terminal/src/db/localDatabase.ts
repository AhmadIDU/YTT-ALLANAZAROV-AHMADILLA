/**
 * PossKassa Lokal Ma'lumotlar Bazasi
 * Dexie.js (IndexedDB wrapper) orqali oflayn saqlash
 */
import Dexie, { Table } from 'dexie';
import type { LocalSale, Product, Category, Shift, Customer, SyncQueueItem, Warehouse } from '../types';

export class PossKassaDatabase extends Dexie {
  // Jadvallar
  sales!: Table<LocalSale>;
  products!: Table<Product>;
  categories!: Table<Category>;
  shifts!: Table<Shift>;
  customers!: Table<Customer>;
  warehouses!: Table<Warehouse>;
  syncQueue!: Table<SyncQueueItem>;

  constructor() {
    super('PossKassaDB');

    this.version(1).stores({
      // Asosiy indekslar
      sales: 'id, syncStatus, saleTime, shiftId, cashierId',
      products: 'id, barcode, sku, tenantId, isActive',
      categories: 'id, parentId, tenantId',
      shifts: 'id, status, cashierId, tenantId',
      customers: 'id, phone, tenantId',
      warehouses: 'id, tenantId, isDefault',
      syncQueue: 'id, type, createdAt',
    });
  }

  // -------------------------------------------------------
  // Mahsulot usullari
  // -------------------------------------------------------

  /** Barcode bo'yicha mahsulot topish */
  async findProductByBarcode(barcode: string): Promise<Product | undefined> {
    return this.products.where('barcode').equals(barcode).first();
  }

  /** Qidirish: nom yoki barcode */
  async searchProducts(query: string, limit = 30): Promise<Product[]> {
    const q = query.toLowerCase();
    return this.products
      .filter(p =>
        p.isActive &&
        (p.name.toLowerCase().includes(q) ||
          (p.barcode?.includes(q) ?? false) ||
          (p.sku?.toLowerCase().includes(q) ?? false))
      )
      .limit(limit)
      .toArray();
  }

  /** Serverdan mahsulotlarni sinxronlash (to'liq yoki delta) */
  async bulkUpsertProducts(products: Product[]): Promise<void> {
    await this.products.bulkPut(products);
  }

  // -------------------------------------------------------
  // Sotuv usullari
  // -------------------------------------------------------

  /** Yangi sotuv saqlash */
  async saveSale(sale: LocalSale): Promise<void> {
    await this.sales.add(sale);
    // Sinxron navbatiga qo'shish
    await this.syncQueue.add({
      id: `sale_${sale.id}`,
      type: 'sale',
      payload: sale,
      attempts: 0,
      createdAt: new Date().toISOString(),
    });
  }

  /** Sinxronlanmagan sotuvlarni olish */
  async getPendingSales(): Promise<LocalSale[]> {
    return this.sales.where('syncStatus').equals('pending').toArray();
  }

  /** Sotuvni sinxronlandi deb belgilash */
  async markSaleSynced(localId: string, remoteId: string, fiscalUrl?: string): Promise<void> {
    await this.sales.update(localId, {
      syncStatus: 'synced',
      remoteId,
      fiscalUrl,
      syncedAt: new Date().toISOString(),
    });
    await this.syncQueue.delete(`sale_${localId}`);
  }

  /** Sotuv sinxronlanmadi (xato) */
  async markSaleFailed(localId: string): Promise<void> {
    await this.sales.update(localId, { syncStatus: 'failed' });
  }

  // -------------------------------------------------------
  // Smena usullari
  // -------------------------------------------------------

  /** Joriy ochiq smenani olish */
  async getOpenShift(): Promise<Shift | undefined> {
    return this.shifts.where('status').equals('open').first();
  }

  // -------------------------------------------------------
  // Sinxron navbat usullari
  // -------------------------------------------------------

  async getPendingSyncItems(): Promise<SyncQueueItem[]> {
    return this.syncQueue.orderBy('createdAt').toArray();
  }

  async removeSyncItem(id: string): Promise<void> {
    await this.syncQueue.delete(id);
  }

  async incrementSyncAttempt(id: string): Promise<void> {
    const item = await this.syncQueue.get(id);
    if (item) {
      await this.syncQueue.update(id, {
        attempts: item.attempts + 1,
        lastAttemptAt: new Date().toISOString(),
      });
    }
  }

  // -------------------------------------------------------
  // Statistika
  // -------------------------------------------------------
  async getPendingSyncCount(): Promise<number> {
    return this.sales.where('syncStatus').equals('pending').count();
  }
}

// Singleton instance
export const db = new PossKassaDatabase();
