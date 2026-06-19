/**
 * Mahsulotlar boshqaruvi sahifasi
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Edit2, Trash2, Package, AlertTriangle, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { inventoryApi } from '../utils/api';
import { fmt } from '../utils/formatters';

interface Product {
  id: string; name: string; barcode?: string; sku?: string;
  unit: string; price: number; cost_price: number; is_active: boolean;
  margin_pct?: number;
  stock_levels?: { warehouse_name: string; quantity: number; is_low: boolean }[];
}

const UNITS = [
  { value: 'pcs', label: 'Dona' },
  { value: 'kg',  label: 'Kilogramm' },
  { value: 'l',   label: 'Litr' },
  { value: 'm',   label: 'Metr' },
  { value: 'box', label: 'Quti' },
];

export function Products() {
  const qc = useQueryClient();
  const [q, setQ]             = useState('');
  const [showForm, setShowForm]= useState(false);
  const [editing, setEditing]  = useState<Product | null>(null);
  const [form, setForm]        = useState<Partial<Product>>({});

  const { data: products = [], isLoading } = useQuery<Product[]>({
    queryKey: ['products', q],
    queryFn:  () => inventoryApi.products({ q: q || undefined }).then(r => r.data),
  });

  const createMut = useMutation({
    mutationFn: (body: Partial<Product>) => inventoryApi.createProduct(body),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['products'] }); toast.success('Mahsulot qo\'shildi'); closeForm(); },
    onError:    (e: { response?: { data?: { detail?: string } } }) => toast.error(e.response?.data?.detail ?? 'Xato yuz berdi'),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Product> }) => inventoryApi.updateProduct(id, body),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['products'] }); toast.success('Yangilandi'); closeForm(); },
    onError:    (e: { response?: { data?: { detail?: string } } }) => toast.error(e.response?.data?.detail ?? 'Xato'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => inventoryApi.deleteProduct(id),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['products'] }); toast.success('O\'chirildi'); },
  });

  const openCreate = () => { setEditing(null); setForm({ unit: 'pcs', vat_rate: 12 } as Partial<Product>); setShowForm(true); };
  const openEdit   = (p: Product) => { setEditing(p); setForm(p); setShowForm(true); };
  const closeForm  = () => { setShowForm(false); setEditing(null); setForm({}); };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editing) updateMut.mutate({ id: editing.id, body: form });
    else         createMut.mutate(form);
  };

  return (
    <div className="space-y-5">
      {/* Sarlavha */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Mahsulotlar</h1>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors"
        >
          <Plus size={16} /> Yangi mahsulot
        </button>
      </div>

      {/* Qidirish */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Mahsulot nomi yoki shtrixkod..."
          className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl outline-none focus:border-blue-400 text-sm"
        />
      </div>

      {/* Jadval */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Yuklanmoqda...</div>
        ) : products.length === 0 ? (
          <div className="p-12 text-center">
            <Package className="mx-auto text-gray-300 mb-3" size={40} />
            <p className="text-gray-500">Mahsulotlar topilmadi</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr className="text-left text-gray-500 text-xs uppercase tracking-wide">
                  <th className="px-4 py-3 font-medium">Mahsulot</th>
                  <th className="px-4 py-3 font-medium">Shtrixkod</th>
                  <th className="px-4 py-3 font-medium">Birlik</th>
                  <th className="px-4 py-3 font-medium text-right">Narx</th>
                  <th className="px-4 py-3 font-medium text-right">Tannarx</th>
                  <th className="px-4 py-3 font-medium text-right">Marjin</th>
                  <th className="px-4 py-3 font-medium text-center">Zaxira</th>
                  <th className="px-4 py-3 font-medium text-center">Holat</th>
                  <th className="px-4 py-3 font-medium text-center">Amal</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {products.map(p => {
                  const totalStock = p.stock_levels?.reduce((s, sl) => s + sl.quantity, 0) ?? 0;
                  const isLow      = p.stock_levels?.some(sl => sl.is_low) ?? false;
                  return (
                    <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-800">{p.name}</div>
                        {p.sku && <div className="text-xs text-gray-400">SKU: {p.sku}</div>}
                      </td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{p.barcode ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-500">{UNITS.find(u => u.value === p.unit)?.label ?? p.unit}</td>
                      <td className="px-4 py-3 text-right font-bold text-gray-800">{fmt.price(p.price)}</td>
                      <td className="px-4 py-3 text-right text-gray-500">{fmt.price(p.cost_price)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={`font-medium ${(p.margin_pct ?? 0) > 0 ? 'text-green-600' : 'text-red-500'}`}>
                          {p.margin_pct != null ? fmt.pct(p.margin_pct) : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
                          ${isLow ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
                          {isLow && <AlertTriangle size={10} />}
                          {totalStock.toLocaleString('uz-UZ')}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium
                          ${p.is_active ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                          {p.is_active ? 'Faol' : 'Nofaol'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center gap-1">
                          <button onClick={() => openEdit(p)} className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors">
                            <Edit2 size={14} />
                          </button>
                          <button
                            onClick={() => { if (confirm('O\'chirilsinmi?')) deleteMut.mutate(p.id); }}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Yaratish / Tahrirlash modali */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b">
              <h2 className="font-bold text-gray-800 text-lg">
                {editing ? 'Mahsulotni tahrirlash' : 'Yangi mahsulot'}
              </h2>
              <button onClick={closeForm} className="text-gray-400 hover:text-gray-600"><X size={20} /></button>
            </div>
            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              <Field label="Nomi *">
                <input required value={form.name ?? ''} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className={INPUT} placeholder="Non Obi 500g" />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Shtrixkod">
                  <input value={form.barcode ?? ''} onChange={e => setForm(f => ({ ...f, barcode: e.target.value }))}
                    className={INPUT} placeholder="4600000123456" />
                </Field>
                <Field label="SKU">
                  <input value={form.sku ?? ''} onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
                    className={INPUT} placeholder="SKU-001" />
                </Field>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <Field label="Narx (so'm) *">
                  <input required type="number" min="0" value={form.price ?? ''} onChange={e => setForm(f => ({ ...f, price: +e.target.value }))}
                    className={INPUT} placeholder="15000" />
                </Field>
                <Field label="Tannarx (so'm)">
                  <input type="number" min="0" value={form.cost_price ?? ''} onChange={e => setForm(f => ({ ...f, cost_price: +e.target.value }))}
                    className={INPUT} placeholder="10000" />
                </Field>
                <Field label="QQS (%)">
                  <input type="number" min="0" max="100" value={(form as Record<string, unknown>).vat_rate as number ?? 12}
                    onChange={e => setForm(f => ({ ...f, vat_rate: +e.target.value } as Partial<Product>))}
                    className={INPUT} />
                </Field>
              </div>
              <Field label="O'lchov birligi">
                <select value={form.unit ?? 'pcs'} onChange={e => setForm(f => ({ ...f, unit: e.target.value }))} className={INPUT}>
                  {UNITS.map(u => <option key={u.value} value={u.value}>{u.label}</option>)}
                </select>
              </Field>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="is_active" checked={form.is_active ?? true}
                  onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
                  className="w-4 h-4 accent-blue-600" />
                <label htmlFor="is_active" className="text-sm text-gray-700">Faol mahsulot</label>
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={closeForm} className="flex-1 py-2.5 border border-gray-200 rounded-xl text-sm text-gray-600 hover:bg-gray-50">
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={createMut.isPending || updateMut.isPending}
                  className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium disabled:opacity-60"
                >
                  {editing ? 'Saqlash' : 'Qo\'shish'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

const INPUT = 'w-full border border-gray-200 rounded-xl px-3 py-2 text-sm outline-none focus:border-blue-400 transition-colors';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
      {children}
    </div>
  );
}
