// ============================================================
// PossKassa — Asosiy TypeScript Turlari
// ============================================================

export type Role = 'cashier' | 'manager' | 'admin' | 'owner';
export type PaymentMethod = 'cash' | 'uzcard' | 'humo' | 'payme' | 'click' | 'uzum' | 'credit';
export type SyncStatus = 'pending' | 'synced' | 'failed';
export type SaleStatus = 'completed' | 'refunded' | 'partial_refund';
export type Unit = 'pcs' | 'kg' | 'l' | 'm' | 'box';

// --- Foydalanuvchi ---
export interface User {
  id: string;
  tenantId: string;
  fullName: string;
  phone: string;
  role: Role;
}

// --- Mahsulot ---
export interface Product {
  id: string;
  tenantId: string;
  categoryId?: string;
  name: string;
  nameUz?: string;
  nameRu?: string;
  sku?: string;
  barcode?: string;
  unit: Unit;
  price: number;
  costPrice: number;
  vatRate: number;
  isActive: boolean;
  trackStock: boolean;
  imageUrl?: string;
  stockQuantity?: number; // lokal keshda
}

// --- Kategoriya ---
export interface Category {
  id: string;
  tenantId: string;
  parentId?: string;
  name: string;
  icon?: string;
  children?: Category[];
}

// --- Savatcha elementi ---
export interface CartItem {
  product: Product;
  quantity: number;
  unitPrice: number;
  discountAmount: number;
  totalPrice: number;
}

// --- To'lov ---
export interface PaymentEntry {
  method: PaymentMethod;
  amount: number;
  transactionId?: string;
}

// --- Sotuv (lokal SQLite) ---
export interface LocalSale {
  id: string;              // UUID — idempotency kaliti
  tenantId: string;
  shiftId: string;
  cashierId: string;
  warehouseId: string;
  customerId?: string;
  receiptNumber: string;
  items: CartItem[];
  payments: PaymentEntry[];
  subtotal: number;
  discountAmount: number;
  vatAmount: number;
  totalAmount: number;
  status: SaleStatus;
  syncStatus: SyncStatus;
  saleTime: string;        // ISO 8601
  syncedAt?: string;
  remoteId?: string;       // Serverdan kelgan ID
  fiscalUrl?: string;
}

// --- Smena ---
export interface Shift {
  id: string;
  tenantId: string;
  cashierId: string;
  warehouseId: string;
  openingCash: number;
  closingCash?: number;
  expectedCash?: number;
  status: 'open' | 'closed';
  openedAt: string;
  closedAt?: string;
}

// --- Mijoz ---
export interface Customer {
  id: string;
  tenantId: string;
  fullName?: string;
  phone: string;
  loyaltyBalance: number;
  totalSpent: number;
}

// --- Ombor ---
export interface Warehouse {
  id: string;
  tenantId: string;
  name: string;
  isDefault: boolean;
}

// --- Sinxron navbat elementi ---
export interface SyncQueueItem {
  id: string;
  type: 'sale' | 'shift_open' | 'shift_close';
  payload: unknown;
  attempts: number;
  lastAttemptAt?: string;
  createdAt: string;
}

// --- Kassa holati ---
export interface PosState {
  cart: CartItem[];
  activeShift: Shift | null;
  currentUser: User | null;
  selectedWarehouse: Warehouse | null;
  isOnline: boolean;
  pendingSyncCount: number;
}
