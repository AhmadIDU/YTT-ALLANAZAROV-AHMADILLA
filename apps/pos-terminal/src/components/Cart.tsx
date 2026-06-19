/**
 * Savatcha komponenti — sotuv qatorlari
 */
import React from 'react';
import { Trash2, Plus, Minus } from 'lucide-react';
import { usePosStore } from '../store/posStore';
import { formatPrice, formatQuantity } from '../utils/formatters';

export function Cart() {
  const cart          = usePosStore(s => s.cart);
  const updateQty     = usePosStore(s => s.updateQuantity);
  const removeItem    = usePosStore(s => s.removeFromCart);
  const getTotal      = usePosStore(s => s.getTotal);
  const getSubtotal   = usePosStore(s => s.getSubtotal);
  const getDiscTotal  = usePosStore(s => s.getDiscountTotal);
  const getVatTotal   = usePosStore(s => s.getVatTotal);

  if (cart.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 select-none">
        <div className="text-6xl mb-4">🛒</div>
        <p className="text-lg font-medium">Savatcha bo'sh</p>
        <p className="text-sm mt-1">Mahsulot qo'shing yoki shtrixkod skanerini ishlating</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Qatorlar */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-1">
        {cart.map((item, idx) => (
          <div
            key={item.product.id}
            className="flex items-center gap-2 bg-white rounded-lg p-2 border border-gray-100 hover:border-blue-200 transition-colors"
          >
            {/* Tartib raqami */}
            <span className="text-xs text-gray-400 w-5 text-right shrink-0">{idx + 1}</span>

            {/* Mahsulot nomi */}
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-800 truncate">{item.product.name}</div>
              <div className="text-xs text-gray-400">{formatPrice(item.unitPrice)}</div>
            </div>

            {/* Miqdor boshqaruvi */}
            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() => updateQty(item.product.id, item.quantity - 1)}
                className="w-7 h-7 rounded-full bg-gray-100 hover:bg-red-100 flex items-center justify-center transition-colors"
              >
                <Minus size={12} />
              </button>
              <span className="w-10 text-center text-sm font-bold">
                {item.product.unit === 'kg' ? item.quantity.toFixed(3) : item.quantity}
              </span>
              <button
                onClick={() => updateQty(item.product.id, item.quantity + 1)}
                className="w-7 h-7 rounded-full bg-gray-100 hover:bg-green-100 flex items-center justify-center transition-colors"
              >
                <Plus size={12} />
              </button>
            </div>

            {/* Jami narx */}
            <div className="text-sm font-bold text-blue-700 w-20 text-right shrink-0">
              {formatPrice(item.totalPrice)}
            </div>

            {/* O'chirish */}
            <button
              onClick={() => removeItem(item.product.id)}
              className="text-gray-300 hover:text-red-500 transition-colors shrink-0"
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>

      {/* Jami hisob-kitob */}
      <div className="border-t border-gray-200 pt-3 mt-3 space-y-1">
        <div className="flex justify-between text-sm text-gray-500">
          <span>Oraliq jami:</span>
          <span>{formatPrice(getSubtotal())}</span>
        </div>
        {getDiscTotal() > 0 && (
          <div className="flex justify-between text-sm text-red-500">
            <span>Chegirma:</span>
            <span>- {formatPrice(getDiscTotal())}</span>
          </div>
        )}
        <div className="flex justify-between text-sm text-gray-500">
          <span>QQS (12%):</span>
          <span>{formatPrice(getVatTotal())}</span>
        </div>
        <div className="flex justify-between text-xl font-bold text-gray-800 pt-1 border-t border-gray-200">
          <span>JAMI:</span>
          <span className="text-blue-700">{formatPrice(getTotal())}</span>
        </div>
      </div>
    </div>
  );
}
