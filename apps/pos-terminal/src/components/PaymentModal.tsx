/**
 * To'lov modal oynasi
 * Naqd, Uzcard/Humo, Payme/Click/Uzum QR
 */
import React, { useState } from 'react';
import { X, Banknote, CreditCard, QrCode, CheckCircle } from 'lucide-react';
import { usePosStore } from '../store/posStore';
import { formatPrice } from '../utils/formatters';
import type { PaymentMethod, PaymentEntry } from '../types';

interface PaymentModalProps {
  onClose:   () => void;
  onSuccess: (sale: import('../types').LocalSale) => void;
}

const PAYMENT_METHODS: { key: PaymentMethod; label: string; icon: React.ReactNode; color: string }[] = [
  { key: 'cash',   label: 'Naqd pul',     icon: <Banknote size={24} />,   color: 'bg-green-500' },
  { key: 'uzcard', label: 'Uzcard',       icon: <CreditCard size={24} />, color: 'bg-blue-600' },
  { key: 'humo',   label: 'Humo',         icon: <CreditCard size={24} />, color: 'bg-orange-500' },
  { key: 'payme',  label: 'Payme',        icon: <QrCode size={24} />,     color: 'bg-cyan-500' },
  { key: 'click',  label: 'Click',        icon: <QrCode size={24} />,     color: 'bg-indigo-500' },
  { key: 'uzum',   label: 'Uzum',         icon: <QrCode size={24} />,     color: 'bg-purple-600' },
];

export function PaymentModal({ onClose, onSuccess }: PaymentModalProps) {
  const total       = usePosStore(s => s.getTotal());
  const completeSale = usePosStore(s => s.completeSale);

  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod>('cash');
  const [cashInput,      setCashInput]      = useState('');
  const [payments,       setPayments]       = useState<PaymentEntry[]>([]);
  const [processing,     setProcessing]     = useState(false);
  const [done,           setDone]           = useState(false);

  const paidAmount  = payments.reduce((s, p) => s + p.amount, 0);
  const remaining   = total - paidAmount;
  const change      = remaining < 0 ? Math.abs(remaining) : 0;
  const cashAmount  = parseFloat(cashInput) || 0;

  // Tez miqdor tugmalari
  const quickAmounts = [
    total,
    Math.ceil(total / 1000) * 1000,
    Math.ceil(total / 5000) * 5000,
    Math.ceil(total / 10000) * 10000,
  ].filter((v, i, arr) => arr.indexOf(v) === i).slice(0, 4);

  const addPayment = () => {
    const amount = selectedMethod === 'cash' ? cashAmount : remaining;
    if (amount <= 0) return;
    setPayments(prev => [...prev, { method: selectedMethod, amount: Math.min(amount, remaining) }]);
    setCashInput('');
  };

  const handlePay = async () => {
    if (remaining > 0 && payments.length === 0) return;
    setProcessing(true);
    try {
      // Agar to'lov qo'shilmagan bo'lsa, avtomatik qo'shish
      const finalPayments = payments.length > 0 ? payments : [{ method: selectedMethod, amount: total }];
      const sale = await completeSale(finalPayments);
      setDone(true);
      setTimeout(() => onSuccess(sale), 1000);
    } finally {
      setProcessing(false);
    }
  };

  if (done) {
    return (
      <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl p-10 text-center shadow-2xl">
          <CheckCircle className="mx-auto text-green-500 mb-4" size={64} />
          <h2 className="text-2xl font-bold text-gray-800">Sotuv amalga oshirildi!</h2>
          <p className="text-gray-500 mt-2">Chek chop etilmoqda...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        {/* Sarlavha */}
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-xl font-bold text-gray-800">To'lov</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={24} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* Jami summa */}
          <div className="bg-blue-50 rounded-xl p-4 text-center">
            <p className="text-sm text-gray-500 mb-1">To'lash kerak</p>
            <p className="text-3xl font-bold text-blue-700">{formatPrice(remaining > 0 ? remaining : 0)}</p>
          </div>

          {/* To'lov usullari */}
          <div className="grid grid-cols-3 gap-2">
            {PAYMENT_METHODS.map(m => (
              <button
                key={m.key}
                onClick={() => setSelectedMethod(m.key)}
                className={`flex flex-col items-center gap-1 p-3 rounded-xl border-2 transition-all ${
                  selectedMethod === m.key
                    ? `border-blue-500 ${m.color} text-white`
                    : 'border-gray-200 hover:border-blue-300 text-gray-600'
                }`}
              >
                {m.icon}
                <span className="text-xs font-medium">{m.label}</span>
              </button>
            ))}
          </div>

          {/* Naqd pul kiritish */}
          {selectedMethod === 'cash' && (
            <div className="space-y-2">
              <input
                type="number"
                value={cashInput}
                onChange={e => setCashInput(e.target.value)}
                placeholder="Miqdor kiriting..."
                className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 text-lg font-bold text-right outline-none focus:border-blue-400"
                autoFocus
              />
              {/* Tez miqdor tugmalari */}
              <div className="grid grid-cols-4 gap-2">
                {quickAmounts.map(a => (
                  <button
                    key={a}
                    onClick={() => setCashInput(a.toString())}
                    className="py-2 bg-gray-100 hover:bg-blue-100 rounded-lg text-sm font-medium text-gray-700 transition-colors"
                  >
                    {formatPrice(a)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Qo'shilgan to'lovlar */}
          {payments.length > 0 && (
            <div className="space-y-1">
              {payments.map((p, i) => (
                <div key={i} className="flex justify-between text-sm">
                  <span className="text-gray-600">{PAYMENT_METHODS.find(m => m.key === p.method)?.label}:</span>
                  <span className="font-medium">{formatPrice(p.amount)}</span>
                </div>
              ))}
            </div>
          )}

          {/* Qaytim */}
          {change > 0 && (
            <div className="bg-green-50 rounded-xl p-3 flex justify-between items-center">
              <span className="text-green-700 font-medium">Qaytim:</span>
              <span className="text-green-700 font-bold text-xl">{formatPrice(change)}</span>
            </div>
          )}
        </div>

        {/* Tugmalar */}
        <div className="flex gap-3 p-5 border-t">
          {remaining > 0 && (
            <button
              onClick={addPayment}
              className="flex-1 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-medium text-gray-700 transition-colors"
            >
              Qo'shish
            </button>
          )}
          <button
            onClick={handlePay}
            disabled={processing || (remaining > 0 && payments.length === 0 && cashAmount < remaining)}
            className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-xl font-bold text-lg transition-colors"
          >
            {processing ? 'Qayta ishlanmoqda...' : '✅ To\'landi'}
          </button>
        </div>
      </div>
    </div>
  );
}
