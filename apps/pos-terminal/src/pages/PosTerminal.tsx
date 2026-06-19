/**
 * Asosiy Kassa Terminali sahifasi
 * Chap: mahsulot qidirish + kategoriyalar
 * O'ng: savatcha + to'lov
 */
import React, { useState, useEffect } from 'react';
import { ShoppingCart, Package, RotateCcw, LogOut } from 'lucide-react';
import { ProductSearch } from '../components/ProductSearch';
import { Cart } from '../components/Cart';
import { PaymentModal } from '../components/PaymentModal';
import { StatusBar } from '../components/StatusBar';
import { ReceiptPrinter } from '../components/ReceiptPrinter';
import { usePosStore } from '../store/posStore';
import { startSyncWorker } from '../sync/syncWorker';
import { formatPrice } from '../utils/formatters';
import type { LocalSale } from '../types';

export function PosTerminal() {
  const [showPayment, setShowPayment]   = useState(false);
  const [lastSale,    setLastSale]      = useState<LocalSale | null>(null);
  const [showReceipt, setShowReceipt]   = useState(false);

  const cart         = usePosStore(s => s.cart);
  const getTotal     = usePosStore(s => s.getTotal);
  const clearCart    = usePosStore(s => s.clearCart);
  const activeShift  = usePosStore(s => s.activeShift);
  const currentUser  = usePosStore(s => s.currentUser);

  // Sinxronizatsiya ishchisini boshlash
  useEffect(() => {
    startSyncWorker();
  }, []);

  const handleSaleSuccess = (sale: LocalSale) => {
    setLastSale(sale);
    setShowPayment(false);
    setShowReceipt(true);
  };

  const handleReceiptClose = () => {
    setShowReceipt(false);
    setLastSale(null);
  };

  // Smena ochilmagan bo'lsa
  if (!activeShift) {
    return (
      <div className="min-h-screen bg-gray-100 flex flex-col">
        <StatusBar />
        <div className="flex-1 flex items-center justify-center">
          <div className="bg-white rounded-2xl p-10 text-center shadow-xl max-w-md w-full">
            <div className="text-6xl mb-4">🔒</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Smena ochilmagan</html>
            <p className="text-gray-500 mb-6">
              Kassada ishlash uchun avval smenani oching.
            </p>
            <button
              onClick={() => window.location.href = '/shift/open'}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg transition-colors"
            >
              Smenani ochish
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <StatusBar />

      {/* Asosiy kontent */}
      <div className="flex flex-1 overflow-hidden">

        {/* CHAP PANEL — Mahsulot qidirish */}
        <div className="flex-1 flex flex-col p-4 gap-4 overflow-hidden">
          {/* Qidirish maydoni */}
          <ProductSearch />

          {/* Tez tanlov: kategoriyalar (ikonkalar) */}
          <div className="flex gap-2 flex-wrap">
            {['Barchasi', 'Oziq-ovqat', 'Ichimliklar', 'Non', 'Sut', 'Go\'sht'].map(cat => (
              <button
                key={cat}
                className="px-3 py-1.5 bg-white border border-gray-200 hover:border-blue-400 rounded-full text-sm text-gray-600 hover:text-blue-600 transition-colors"
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Ma'lumot paneli */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-xl p-4 text-center shadow-sm">
              <div className="text-2xl font-bold text-blue-700">{cart.length}</div>
              <div className="text-xs text-gray-500 mt-1">Mahsulot turi</div>
            </div>
            <div className="bg-white rounded-xl p-4 text-center shadow-sm">
              <div className="text-2xl font-bold text-green-600">
                {cart.reduce((s, i) => s + i.quantity, 0)}
              </div>
              <div className="text-xs text-gray-500 mt-1">Jami miqdor</div>
            </div>
            <div className="bg-white rounded-xl p-4 text-center shadow-sm">
              <div className="text-lg font-bold text-orange-600">
                {formatPrice(getTotal())}
              </div>
              <div className="text-xs text-gray-500 mt-1">Jami summa</div>
            </div>
          </div>

          {/* Qisqa amallar */}
          <div className="flex gap-2 mt-auto">
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-600 hover:border-blue-300 transition-colors">
              <RotateCcw size={16} />
              Qaytarish
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-600 hover:border-blue-300 transition-colors">
              <Package size={16} />
              Tovarlar
            </button>
            <button
              onClick={clearCart}
              disabled={cart.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-red-500 hover:border-red-300 disabled:opacity-40 transition-colors ml-auto"
            >
              Savatchani tozalash
            </button>
          </div>
        </div>

        {/* O'NG PANEL — Savatcha va to'lov */}
        <div className="w-96 bg-white flex flex-col shadow-xl">
          {/* Sarlavha */}
          <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100">
            <ShoppingCart size={20} className="text-blue-600" />
            <h2 className="font-bold text-gray-800">Savatcha</h2>
            {cart.length > 0 && (
              <span className="ml-auto bg-blue-100 text-blue-700 text-xs font-bold px-2 py-0.5 rounded-full">
                {cart.length}
              </span>
            )}
          </div>

          {/* Savatcha qatorlari */}
          <div className="flex-1 p-4 overflow-hidden">
            <Cart />
          </div>

          {/* To'lov tugmasi */}
          <div className="p-4 border-t border-gray-100">
            <button
              onClick={() => setShowPayment(true)}
              disabled={cart.length === 0}
              className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 text-white rounded-xl font-bold text-xl transition-colors shadow-lg"
            >
              {cart.length === 0
                ? 'Mahsulot qo\'shing'
                : `💳 To'lov — ${formatPrice(getTotal())}`}
            </button>
          </div>
        </div>
      </div>

      {/* Modalar */}
      {showPayment && (
        <PaymentModal
          onClose={() => setShowPayment(false)}
          onSuccess={handleSaleSuccess}
        />
      )}

      {showReceipt && lastSale && (
        <ReceiptPrinter
          sale={lastSale}
          onClose={handleReceiptClose}
        />
      )}
    </div>
  );
}
