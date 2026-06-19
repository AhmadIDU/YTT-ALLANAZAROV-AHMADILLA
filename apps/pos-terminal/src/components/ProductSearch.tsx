/**
 * Mahsulot qidirish komponenti
 * Shtrixkod skaneri + matnli qidirish
 */
import React, { useState, useRef, useEffect } from 'react';
import { Search, X } from 'lucide-react';
import { db } from '../db/localDatabase';
import { usePosStore } from '../store/posStore';
import { useBarcode } from '../hooks/useBarcode';
import { formatPrice } from '../utils/formatters';
import type { Product } from '../types';

export function ProductSearch() {
  const [query, setQuery]         = useState('');
  const [results, setResults]     = useState<Product[]>([]);
  const [loading, setLoading]     = useState(false);
  const inputRef                  = useRef<HTMLInputElement>(null);
  const addToCart                 = usePosStore(s => s.addToCart);

  // Shtrixkod skaneri
  useBarcode({
    onScan: async (barcode) => {
      const product = await db.findProductByBarcode(barcode);
      if (product) {
        addToCart(product);
        setQuery('');
        setResults([]);
      } else {
        // Topilmadi — qidirish maydoniga barcode yozish
        setQuery(barcode);
      }
    },
  });

  // Matnli qidirish
  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    const timer = setTimeout(async () => {
      setLoading(true);
      const found = await db.searchProducts(query, 20);
      setResults(found);
      setLoading(false);
    }, 200);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (product: Product) => {
    addToCart(product);
    setQuery('');
    setResults([]);
    inputRef.current?.focus();
  };

  return (
    <div className="relative w-full">
      {/* Qidirish maydoni */}
      <div className="flex items-center gap-2 bg-white border-2 border-blue-400 rounded-xl px-4 py-3 shadow-sm">
        <Search className="text-gray-400 shrink-0" size={20} />
        <input
          ref={inputRef}
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Mahsulot nomi yoki shtrixkod..."
          className="flex-1 outline-none text-gray-800 text-base"
          autoFocus
        />
        {query && (
          <button onClick={() => { setQuery(''); setResults([]); }}>
            <X size={18} className="text-gray-400 hover:text-gray-600" />
          </button>
        )}
      </div>

      {/* Natijalar ro'yxati */}
      {results.length > 0 && (
        <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-white border border-gray-200 rounded-xl shadow-xl max-h-80 overflow-y-auto">
          {loading && (
            <div className="p-3 text-center text-gray-400 text-sm">Qidirmoqda...</div>
          )}
          {results.map(product => (
            <button
              key={product.id}
              onClick={() => handleSelect(product)}
              className="w-full flex items-center justify-between px-4 py-3 hover:bg-blue-50 border-b border-gray-100 last:border-0 transition-colors"
            >
              <div className="text-left">
                <div className="font-medium text-gray-800">{product.name}</div>
                <div className="text-xs text-gray-400">
                  {product.barcode ?? product.sku ?? '—'}
                  {product.stockQuantity !== undefined && (
                    <span className={`ml-2 ${product.stockQuantity > 0 ? 'text-green-600' : 'text-red-500'}`}>
                      Zaxira: {product.stockQuantity}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-blue-700">{formatPrice(product.price)}</div>
                <div className="text-xs text-gray-400">{product.unit}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
