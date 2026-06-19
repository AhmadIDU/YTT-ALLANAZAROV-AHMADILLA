/**
 * Tovar Qabuli (Kirim) sahifasi
 * Foto / CSV / ESF → Tekshiruv → Tasdiqlash
 */
import React, { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import {
  Upload, Camera, FileSpreadsheet, FileText,
  CheckCircle, XCircle, Clock, Eye, ChevronDown, Check, X, Info,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { intakeApi } from '../utils/api';
import { fmt } from '../utils/formatters';

type DraftStatus = 'extracting' | 'review_pending' | 'approved' | 'rejected';
interface Draft { id: string; source: string; status: DraftStatus; rows_count: number; created_at: string; }
interface DraftRow {
  name: string; barcode?: string; qty: number; unit: string;
  unit_cost: number; total_cost: number; vat_rate: number; expiry_date?: string;
  approved: boolean;
  _match: { action: string; product_id?: string; product_name?: string; confidence?: number; candidates?: { id: string; name: string }[] };
}

const STATUS_BADGE: Record<DraftStatus, { label: string; icon: React.ElementType; cls: string }> = {
  extracting:     { label: 'Tahlil qilinmoqda', icon: Clock,        cls: 'bg-yellow-50 text-yellow-700' },
  review_pending: { label: 'Tekshiruv kutilmoqda', icon: Eye,       cls: 'bg-blue-50   text-blue-700'   },
  approved:       { label: 'Tasdiqlangan',      icon: CheckCircle,  cls: 'bg-green-50  text-green-700'  },
  rejected:       { label: 'Rad etilgan',       icon: XCircle,      cls: 'bg-red-50    text-red-700'    },
};

export function Intake() {
  const qc                              = useQueryClient();
  const [tab, setTab]                   = useState<'new'|'drafts'>('new');
  const [method, setMethod]             = useState<'photo'|'csv'|'esf'>('photo');
  const [esfNum, setEsfNum]             = useState('');
  const [selectedDraft, setSelectedDraft]= useState<string | null>(null);

  const { data: drafts = [] } = useQuery<Draft[]>({
    queryKey: ['intake-drafts'],
    queryFn:  () => intakeApi.drafts().then(r => r.data),
    refetchInterval: 5000,
  });

  const { data: draftDetail, isLoading: detailLoading } = useQuery({
    queryKey: ['intake-draft', selectedDraft],
    queryFn:  () => intakeApi.draft(selectedDraft!).then(r => r.data),
    enabled:  !!selectedDraft,
  });

  // ── Fayl yuklash (Dropzone) ─────────────────────────
  const uploadMut = useMutation({
    mutationFn: (form: FormData) =>
      method === 'photo' ? intakeApi.uploadPhoto(form) : intakeApi.uploadCsv(form),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['intake-drafts'] });
      toast.success('Fayl yuklandi! Tekshiruv uchun tayyor.');
      setSelectedDraft(r.data.draft_id);
      setTab('drafts');
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail ?? 'Yuklash xatosi'),
  });

  const onDrop = useCallback((files: File[]) => {
    if (!files[0]) return;
    const form = new FormData();
    form.append('file', files[0]);
    uploadMut.mutate(form);
  }, [uploadMut, method]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: method === 'photo'
      ? { 'image/*': ['.jpg', '.jpeg', '.png', '.webp'] }
      : { 'text/csv': ['.csv'], 'application/vnd.ms-excel': ['.xls', '.xlsx'],
          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxFiles: 1,
  });

  const esfMut = useMutation({
    mutationFn: () => intakeApi.fromEsf(esfNum),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['intake-drafts'] });
      toast.success('ESF yuklandi!');
      setSelectedDraft(r.data.draft_id);
      setTab('drafts');
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail ?? 'ESF xatosi'),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gray-800">Tovar qabuli (Kirim)</h1>

      {/* Tab tanlash */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(['new','drafts'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {t === 'new' ? 'Yangi kirim' : `Loyihalar (${drafts.length})`}
          </button>
        ))}
      </div>

      {tab === 'new' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Usul tanlash */}
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm space-y-4">
            <h2 className="font-bold text-gray-800">Kiritish usulini tanlang</h2>
            <div className="grid grid-cols-3 gap-3">
              {([
                { key: 'photo', icon: Camera,         label: 'Foto' ,       desc: 'Rasm olish\n(Claude Vision)' },
                { key: 'csv',   icon: FileSpreadsheet, label: 'CSV/Excel',   desc: 'Fayl\nyuklash' },
                { key: 'esf',   icon: FileText,        label: 'ESF',         desc: 'didox.uz\ndan pull' },
              ] as const).map(m => (
                <button key={m.key} onClick={() => setMethod(m.key)}
                  className={`flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${
                    method === m.key
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-blue-300 text-gray-600'
                  }`}>
                  <m.icon size={24} />
                  <div className="text-sm font-medium">{m.label}</div>
                  <div className="text-xs text-center whitespace-pre-line opacity-70">{m.desc}</div>
                </button>
              ))}
            </div>

            {/* ESF raqam kiritish */}
            {method === 'esf' ? (
              <div className="space-y-3">
                <div className="flex items-start gap-2 bg-blue-50 rounded-xl p-3 text-sm text-blue-700">
                  <Info size={16} className="shrink-0 mt-0.5" />
                  <span>ESF usuli eng aniq — OCR va qo'lda kiritish shart emas. Yetkazuvchi ESF bergan bo'lsa shu usulni tanlang.</span>
                </div>
                <input
                  value={esfNum}
                  onChange={e => setEsfNum(e.target.value)}
                  placeholder="ESF raqami (masalan: INV-2025-001234)"
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-blue-400 text-sm"
                />
                <button
                  onClick={() => esfMut.mutate()}
                  disabled={!esfNum.trim() || esfMut.isPending}
                  className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 text-white rounded-xl font-medium text-sm transition-colors"
                >
                  {esfMut.isPending ? 'Yuklanmoqda...' : 'ESF ni olish'}
                </button>
              </div>
            ) : (
              /* Drag & Drop zona */
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? 'border-blue-400 bg-blue-50'
                    : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="mx-auto text-gray-300 mb-3" size={36} />
                {uploadMut.isPending ? (
                  <div>
                    <p className="text-blue-600 font-medium">Yuklanmoqda...</p>
                    {method === 'photo' && <p className="text-sm text-gray-400 mt-1">Claude Vision tahlil qilmoqda</p>}
                  </div>
                ) : (
                  <>
                    <p className="font-medium text-gray-700">
                      {isDragActive ? 'Tashlang!' : 'Faylni tashlang yoki bosing'}
                    </p>
                    <p className="text-sm text-gray-400 mt-1">
                      {method === 'photo' ? 'JPEG, PNG, WEBP — maks. 20MB' : 'CSV, XLS, XLSX — maks. 10MB'}
                    </p>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Ko'rsatmalar */}
          <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm">
            <h2 className="font-bold text-gray-800 mb-4">Qanday ishlaydi?</h2>
            <div className="space-y-4">
              {[
                { n: '1', t: 'Fayl yuklash',      d: method === 'photo' ? 'Yetkazuvchi ro\'yxati rasmini yuklang' : method === 'csv' ? 'CSV yoki Excel faylini yuklang' : 'ESF raqamini kiriting' },
                { n: '2', t: 'Avtomatik tahlil',  d: method === 'photo' ? 'Claude Vision AI barcha mahsulotlarni ajratadi' : method === 'csv' ? 'Ustunlar avtomatik aniqlanadi' : 'didox.uz dan ma\'lumotlar olinadi' },
                { n: '3', t: 'Mahsulot moslashtirish', d: 'Shtrixkod bo\'yicha mavjud mahsulotlar aniqlanadi, yangilari uchun loyiha yaratiladi' },
                { n: '4', t: '⚠️ Inson tekshiruvi', d: 'MAJBURIY: Barcha qatorlarni tekshiring va tasdiqlang. Faqat shu so\'ng bazaga yoziladi.' },
                { n: '5', t: 'Zaxira yangilash',  d: 'Tasdiqlangandan so\'ng zaxira va tannarx avtomatik yangilanadi' },
              ].map(s => (
                <div key={s.n} className="flex gap-3">
                  <div className="w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center text-xs font-bold shrink-0">
                    {s.n}
                  </div>
                  <div>
                    <div className="font-medium text-gray-800 text-sm">{s.t}</div>
                    <div className="text-xs text-gray-500">{s.d}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'drafts' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Loyihalar ro'yxati */}
          <div className="space-y-2">
            <h2 className="font-semibold text-gray-700 text-sm px-1">Barcha loyihalar</h2>
            {drafts.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-100 p-6 text-center text-gray-400 text-sm">
                Hozircha loyiha yo'q
              </div>
            ) : (
              drafts.map(d => {
                const badge = STATUS_BADGE[d.status];
                return (
                  <button
                    key={d.id}
                    onClick={() => setSelectedDraft(d.id)}
                    className={`w-full text-left p-4 rounded-xl border transition-colors ${
                      selectedDraft === d.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-100 bg-white hover:border-blue-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-500 uppercase">{d.source}</span>
                      <span className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${badge.cls}`}>
                        <badge.icon size={10} />
                        {badge.label}
                      </span>
                    </div>
                    <div className="text-sm text-gray-700">{d.rows_count} ta qator</div>
                    <div className="text-xs text-gray-400 mt-1">{fmt.dateTime(d.created_at)}</div>
                  </button>
                );
              })
            )}
          </div>

          {/* Tanlangan loyiha tafsilotlari */}
          <div className="lg:col-span-2">
            {selectedDraft && draftDetail && (
              <ReviewPanel
                draft={draftDetail}
                onApproved={() => { qc.invalidateQueries({ queryKey: ['intake-drafts'] }); setSelectedDraft(null); }}
              />
            )}
            {!selectedDraft && (
              <div className="bg-white rounded-xl border border-gray-100 p-12 text-center text-gray-400">
                <Eye size={32} className="mx-auto mb-3 opacity-40" />
                <p>Tekshirish uchun loyihani tanlang</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tekshiruv paneli ──────────────────────────────────────
function ReviewPanel({ draft, onApproved }: { draft: { id: string; status: DraftStatus; rows: DraftRow[]; source: string }; onApproved: () => void }) {
  const qc = useQueryClient();
  const [rows, setRows] = useState<DraftRow[]>(
    (draft.rows ?? []).map(r => ({ ...r, approved: true }))
  );
  const [warehouseId, setWarehouseId] = useState('');

  const { data: warehouses = [] } = useQuery<{ id: string; name: string }[]>({
    queryKey: ['warehouses'],
    queryFn: () => import('../utils/api').then(m => m.inventoryApi.warehouses().then(r => r.data)),
  });

  const approveMut = useMutation({
    mutationFn: () => intakeApi.approve(draft.id, {
      reviewed_rows: rows,
      warehouse_id:  warehouseId || warehouses[0]?.id,
    }),
    onSuccess: (r) => {
      toast.success(`✅ ${r.data.items_count} ta mahsulot saqlandi! Chek: ${r.data.receipt_number}`);
      onApproved();
    },
    onError: (e: { response?: { data?: { detail?: string } } }) =>
      toast.error(e.response?.data?.detail ?? 'Xato'),
  });

  const rejectMut = useMutation({
    mutationFn: () => intakeApi.reject(draft.id, 'Inson tomonidan rad etildi'),
    onSuccess:  () => { toast.success('Rad etildi'); onApproved(); },
  });

  const toggleRow    = (i: number) => setRows(rs => rs.map((r, idx) => idx === i ? { ...r, approved: !r.approved } : r));
  const updateRow    = (i: number, field: keyof DraftRow, val: unknown) =>
    setRows(rs => rs.map((r, idx) => idx === i ? { ...r, [field]: val } : r));
  const approvedCount = rows.filter(r => r.approved).length;

  if (draft.status === 'approved') {
    return (
      <div className="bg-white rounded-xl border border-green-100 p-8 text-center">
        <CheckCircle className="mx-auto text-green-500 mb-3" size={40} />
        <p className="font-bold text-gray-800">Bu kirim tasdiqlangan</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      {/* Sarlavha */}
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-gray-800">Tekshiruv — {rows.length} ta qator</h3>
          <p className="text-xs text-gray-400 mt-0.5">
            {approvedCount} ta tasdiqlangan · {rows.length - approvedCount} ta rad etilgan
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={warehouseId}
            onChange={e => setWarehouseId(e.target.value)}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm outline-none"
          >
            <option value="">Omborni tanlang</option>
            {warehouses.map((w: { id: string; name: string }) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Qatorlar jadvali */}
      <div className="overflow-x-auto max-h-[50vh] overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-gray-50 border-b border-gray-100">
            <tr className="text-left text-gray-400 uppercase tracking-wide">
              <th className="px-3 py-2 w-8">✓</th>
              <th className="px-3 py-2">Mahsulot</th>
              <th className="px-3 py-2">Shtrixkod</th>
              <th className="px-3 py-2 text-right">Miqdor</th>
              <th className="px-3 py-2 text-right">Tannarx</th>
              <th className="px-3 py-2 text-right">Jami</th>
              <th className="px-3 py-2">Moslashtirish</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {rows.map((row, i) => (
              <tr key={i} className={row.approved ? 'hover:bg-gray-50' : 'bg-red-50/50 opacity-60'}>
                <td className="px-3 py-2">
                  <input type="checkbox" checked={row.approved} onChange={() => toggleRow(i)}
                    className="w-4 h-4 accent-blue-600" />
                </td>
                <td className="px-3 py-2">
                  <input
                    value={row.name}
                    onChange={e => updateRow(i, 'name', e.target.value)}
                    className="w-full border border-transparent focus:border-blue-300 rounded px-1 py-0.5 outline-none bg-transparent focus:bg-white"
                  />
                </td>
                <td className="px-3 py-2 font-mono text-gray-400">{row.barcode ?? '—'}</td>
                <td className="px-3 py-2 text-right">
                  <input type="number" value={row.qty}
                    onChange={e => updateRow(i, 'qty', +e.target.value)}
                    className="w-16 text-right border border-transparent focus:border-blue-300 rounded px-1 outline-none bg-transparent focus:bg-white"
                  />
                </td>
                <td className="px-3 py-2 text-right">
                  <input type="number" value={row.unit_cost}
                    onChange={e => updateRow(i, 'unit_cost', +e.target.value)}
                    className="w-20 text-right border border-transparent focus:border-blue-300 rounded px-1 outline-none bg-transparent focus:bg-white"
                  />
                </td>
                <td className="px-3 py-2 text-right font-medium text-gray-700">
                  {fmt.price(row.qty * row.unit_cost)}
                </td>
                <td className="px-3 py-2">
                  {row._match?.action === 'update_stock' && (
                    <span className="px-1.5 py-0.5 bg-green-50 text-green-700 rounded text-xs">
                      ✓ {row._match.product_name?.slice(0, 15)}
                    </span>
                  )}
                  {row._match?.action === 'create_new' && (
                    <span className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">+ Yangi</span>
                  )}
                  {row._match?.action === 'select_or_create' && (
                    <span className="px-1.5 py-0.5 bg-yellow-50 text-yellow-700 rounded text-xs">? Tanlang</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Harakatlar */}
      <div className="p-4 border-t border-gray-100 flex gap-3 justify-between items-center">
        <div className="text-sm text-gray-500">
          Jami: <span className="font-bold text-gray-800">
            {fmt.price(rows.filter(r => r.approved).reduce((s, r) => s + r.qty * r.unit_cost, 0))}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => rejectMut.mutate()}
            disabled={rejectMut.isPending}
            className="flex items-center gap-1.5 px-4 py-2 border border-red-200 text-red-600 hover:bg-red-50 rounded-xl text-sm font-medium transition-colors"
          >
            <X size={14} /> Rad etish
          </button>
          <button
            onClick={() => approveMut.mutate()}
            disabled={approvedCount === 0 || approveMut.isPending || (!warehouseId && warehouses.length > 0)}
            className="flex items-center gap-1.5 px-5 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-200 text-white rounded-xl text-sm font-bold transition-colors"
          >
            <Check size={14} /> Tasdiqlash ({approvedCount})
          </button>
        </div>
      </div>
    </div>
  );
}
