/**
 * Chek printer komponenti
 * Termal printer yoki ekranda ko'rsatish
 */
import React from 'react';
import { formatPrice, formatDateTime, formatQuantity } from '../utils/formatters';
import type { LocalSale } from '../types';

interface ReceiptPrinterProps {
  sale:          LocalSale;
  tenantName?:   string;
  tenantAddress?: string;
  onClose:       () => void;
}

export function ReceiptPrinter({ sale, tenantName = 'PossKassa Do\'kon', tenantAddress, onClose }: ReceiptPrinterProps) {
  const handlePrint = () => window.print();

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-72 max-h-screen overflow-y-auto">
        {/* Chek matni */}
        <div id="receipt" className="p-4 font-mono text-sm">
          {/* Do'kon nomi */}
          <div className="text-center mb-3">
            <div className="font-bold text-base">{tenantName}</div>
            {tenantAddress && <div className="text-xs text-gray-500">{tenantAddress}</div>}
            <div className="border-b border-dashed border-gray-300 my-2" />
          </div>

          {/* Chek ma'lumotlari */}
          <div className="text-xs text-gray-500 mb-2">
            <div>Chek: {sale.receiptNumber}</div>
            <div>Sana: {formatDateTime(sale.saleTime)}</div>
            {sale.fiscalUrl && (
              <div className="text-green-600">✓ Fiskal chek</div>
            )}
            {sale.syncStatus === 'pending' && (
              <div className="text-orange-500">⏳ Sinxronlanmagan (oflayn)</div>
            )}
          </div>

          <div className="border-b border-dashed border-gray-300 my-2" />

          {/* Mahsulotlar */}
          {sale.items.map((item, i) => (
            <div key={i} className="mb-2">
              <div className="font-medium text-xs">{item.product.name}</div>
              <div className="flex justify-between text-xs text-gray-600">
                <span>
                  {formatQuantity(item.quantity, item.product.unit)} × {formatPrice(item.unitPrice)}
                </span>
                <span className="font-medium">{formatPrice(item.totalPrice)}</span>
              </div>
            </div>
          ))}

          <div className="border-b border-dashed border-gray-300 my-2" />

          {/* Jami */}
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span>Oraliq jami:</span>
              <span>{formatPrice(sale.subtotal)}</span>
            </div>
            {sale.discountAmount > 0 && (
              <div className="flex justify-between text-red-600">
                <span>Chegirma:</span>
                <span>- {formatPrice(sale.discountAmount)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>QQS (12%):</span>
              <span>{formatPrice(sale.vatAmount)}</span>
            </div>
            <div className="flex justify-between font-bold text-sm border-t border-gray-200 pt-1 mt-1">
              <span>JAMI:</span>
              <span>{formatPrice(sale.totalAmount)}</span>
            </div>
          </div>

          {/* To'lov usullari */}
          <div className="border-t border-dashed border-gray-300 my-2">
            {sale.payments.map((p, i) => (
              <div key={i} className="flex justify-between text-xs">
                <span className="capitalize">
                  {p.method === 'cash' ? 'Naqd' :
                   p.method === 'payme' ? 'Payme' :
                   p.method === 'click' ? 'Click' : p.method}:
                </span>
                <span>{formatPrice(p.amount)}</span>
              </div>
            ))}
          </div>

          {/* QR kod joy */}
          {sale.fiscalUrl && (
            <div className="text-center mt-3">
              <div className="text-xs text-gray-400">Fiskal chekni tekshirish:</div>
              <div className="text-xs text-blue-500 break-all">{sale.fiscalUrl}</div>
            </div>
          )}

          <div className="text-center text-xs text-gray-400 mt-3">
            Xaridingiz uchun rahmat! 🙏
          </div>
        </div>

        {/* Tugmalar */}
        <div className="flex gap-2 p-3 border-t">
          <button
            onClick={handlePrint}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            🖨️ Chop etish
          </button>
          <button
            onClick={onClose}
            className="flex-1 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors"
          >
            Yopish
          </button>
        </div>
      </div>
    </div>
  );
}
