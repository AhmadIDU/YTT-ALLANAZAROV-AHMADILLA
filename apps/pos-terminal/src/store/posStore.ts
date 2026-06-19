/**
 * PossKassa — Asosiy Kassa Holat Boshqaruvi (Zustand)
 */
import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import { db } from '../db/localDatabase';
import type {
  CartItem, Product, PaymentEntry, LocalSale,
  Shift, User, Customer, Warehouse, PosState
} from '../types';

interface PosStore extends PosState {
  // Savatcha amallari
  addToCart:         (product: Product, quantity?: number) => void;
  removeFromCart:    (productId: string) => void;
  updateQuantity:    (productId: string, quantity: number) => void;
  updateDiscount:    (productId: string, discount: number) => void;
  clearCart:         () => void;

  // Sotuv amallari
  completeSale:      (payments: PaymentEntry[], customerId?: string) => Promise<LocalSale>;
  setActiveShift:    (shift: Shift | null) => void;
  setCurrentUser:    (user: User | null) => void;
  setWarehouse:      (warehouse: Warehouse | null) => void;
  setOnlineStatus:   (online: boolean) => void;
  refreshPendingCount: () => Promise<void>;

  // Hisob-kitob
  getSubtotal:       () => number;
  getDiscountTotal:  () => number;
  getVatTotal:       () => number;
  getTotal:          () => number;
}

// Chek raqamini yaratish
function generateReceiptNumber(): string {
  const now = new Date();
  const date = now.toISOString().slice(0, 10).replace(/-/g, '');
  const rand = Math.floor(Math.random() * 9000) + 1000;
  return `PK-${date}-${rand}`;
}

export const usePosStore = create<PosStore>((set, get) => ({
  cart:              [],
  activeShift:       null,
  currentUser:       null,
  selectedWarehouse: null,
  isOnline:          navigator.onLine,
  pendingSyncCount:  0,

  // -------------------------------------------------------
  // Savatcha amallari
  // -------------------------------------------------------
  addToCart: (product: Product, quantity = 1) => {
    set(state => {
      const existing = state.cart.find(i => i.product.id === product.id);
      if (existing) {
        return {
          cart: state.cart.map(i =>
            i.product.id === product.id
              ? {
                  ...i,
                  quantity: i.quantity + quantity,
                  totalPrice: (i.quantity + quantity) * i.unitPrice - i.discountAmount,
                }
              : i
          ),
        };
      }
      const newItem: CartItem = {
        product,
        quantity,
        unitPrice:      product.price,
        discountAmount: 0,
        totalPrice:     product.price * quantity,
      };
      return { cart: [...state.cart, newItem] };
    });
  },

  removeFromCart: (productId: string) => {
    set(state => ({ cart: state.cart.filter(i => i.product.id !== productId) }));
  },

  updateQuantity: (productId: string, quantity: number) => {
    if (quantity <= 0) {
      get().removeFromCart(productId);
      return;
    }
    set(state => ({
      cart: state.cart.map(i =>
        i.product.id === productId
          ? { ...i, quantity, totalPrice: quantity * i.unitPrice - i.discountAmount }
          : i
      ),
    }));
  },

  updateDiscount: (productId: string, discount: number) => {
    set(state => ({
      cart: state.cart.map(i =>
        i.product.id === productId
          ? { ...i, discountAmount: discount, totalPrice: i.quantity * i.unitPrice - discount }
          : i
      ),
    }));
  },

  clearCart: () => set({ cart: [] }),

  // -------------------------------------------------------
  // Sotuvni yakunlash
  // -------------------------------------------------------
  completeSale: async (payments: PaymentEntry[], customerId?: string): Promise<LocalSale> => {
    const state = get();
    if (!state.activeShift) throw new Error('Smena ochilmagan');
    if (!state.currentUser) throw new Error('Foydalanuvchi aniqlanmagan');
    if (!state.selectedWarehouse) throw new Error('Omborxona tanlanmagan');
    if (state.cart.length === 0) throw new Error('Savatcha bo\'sh');

    const subtotal      = get().getSubtotal();
    const discountTotal = get().getDiscountTotal();
    const vatTotal      = get().getVatTotal();
    const total         = get().getTotal();

    const sale: LocalSale = {
      id:             uuidv4(),
      tenantId:       state.currentUser.tenantId,
      shiftId:        state.activeShift.id,
      cashierId:      state.currentUser.id,
      warehouseId:    state.selectedWarehouse.id,
      customerId,
      receiptNumber:  generateReceiptNumber(),
      items:          [...state.cart],
      payments,
      subtotal,
      discountAmount: discountTotal,
      vatAmount:      vatTotal,
      totalAmount:    total,
      status:         'completed',
      syncStatus:     'pending',
      saleTime:       new Date().toISOString(),
    };

    // Lokal bazaga saqlash (sinxron navbatga ham qo'shiladi)
    await db.saveSale(sale);

    // Savatchani tozalash
    set({ cart: [] });

    // Kutilayotgan sinxronizatsiyalar sonini yangilash
    await get().refreshPendingCount();

    return sale;
  },

  // -------------------------------------------------------
  // Yordamchi setterlar
  // -------------------------------------------------------
  setActiveShift:    (shift) => set({ activeShift: shift }),
  setCurrentUser:    (user)  => set({ currentUser: user }),
  setWarehouse:      (wh)    => set({ selectedWarehouse: wh }),
  setOnlineStatus:   (val)   => set({ isOnline: val }),

  refreshPendingCount: async () => {
    const count = await db.getPendingSyncCount();
    set({ pendingSyncCount: count });
  },

  // -------------------------------------------------------
  // Hisob-kitob funksiyalari
  // -------------------------------------------------------
  getSubtotal: () => {
    return get().cart.reduce((sum, i) => sum + i.quantity * i.unitPrice, 0);
  },
  getDiscountTotal: () => {
    return get().cart.reduce((sum, i) => sum + i.discountAmount, 0);
  },
  getVatTotal: () => {
    return get().cart.reduce((sum, i) => {
      const base = i.totalPrice;
      const vat = i.product.vatRate ?? 12;
      return sum + (base * vat) / (100 + vat);
    }, 0);
  },
  getTotal: () => {
    return get().cart.reduce((sum, i) => sum + i.totalPrice, 0);
  },
}));
