/**
 * PossKassa Backoffice — API mijoz
 */
import axios from 'axios';

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

export const api = axios.create({ baseURL: BASE, timeout: 30_000 });

api.interceptors.request.use(cfg => {
  const token    = localStorage.getItem('access_token');
  const tenantId = localStorage.getItem('tenant_id');
  if (token)    cfg.headers.Authorization = `Bearer ${token}`;
  if (tenantId) cfg.headers['X-Tenant-ID'] = tenantId;
  return cfg;
});

api.interceptors.response.use(
  r => r,
  async err => {
    if (err.response?.status === 401 && !err.config._retry) {
      err.config._retry = true;
      try {
        const { data } = await axios.post(`${BASE}/auth/refresh`, {
          refresh_token: localStorage.getItem('refresh_token'),
        });
        localStorage.setItem('access_token', data.access_token);
        err.config.headers.Authorization = `Bearer ${data.access_token}`;
        return api(err.config);
      } catch {
        localStorage.clear();
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

// ── Typed API calls ──────────────────────────────────────
export const salesApi = {
  list:    (p?: Record<string, unknown>) => api.get('/sales', { params: p }),
  get:     (id: string)                  => api.get(`/sales/${id}`),
  refund:  (id: string, body: unknown)   => api.post(`/sales/${id}/refund`, body),
  summary: (p: Record<string, unknown>)  => api.get('/reports/sales-summary', { params: p }),
};

export const inventoryApi = {
  products:    (p?: Record<string, unknown>) => api.get('/products', { params: p }),
  product:     (id: string)                  => api.get(`/products/${id}`),
  createProduct:(body: unknown)              => api.post('/products', body),
  updateProduct:(id: string, body: unknown)  => api.put(`/products/${id}`, body),
  deleteProduct:(id: string)                 => api.delete(`/products/${id}`),
  categories:  ()                            => api.get('/categories'),
  warehouses:  ()                            => api.get('/warehouses'),
  lowStock:    ()                            => api.get('/products/low-stock'),
  adjustStock: (body: unknown)               => api.post('/stock/adjust', body),
};

export const intakeApi = {
  uploadPhoto: (form: FormData)              => api.post('/intake/photo', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  uploadCsv:   (form: FormData)              => api.post('/intake/csv',   form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  fromEsf:     (invoiceNum: string, wid?: string) => api.post('/intake/esf', null, { params: { invoice_number: invoiceNum, warehouse_id: wid } }),
  drafts:      (status?: string)             => api.get('/intake/drafts', { params: { status } }),
  draft:       (id: string)                  => api.get(`/intake/drafts/${id}`),
  updateRows:  (id: string, rows: unknown[]) => api.put(`/intake/drafts/${id}/rows`, rows),
  approve:     (id: string, body: unknown)   => api.post(`/intake/drafts/${id}/approve`, body),
  reject:      (id: string, reason: string)  => api.post(`/intake/drafts/${id}/reject`, { reason }),
  suppliers:   ()                            => api.get('/intake/suppliers'),
};

export const analyticsApi = {
  dashboard:   ()                            => api.get('/dashboard'),
  topProducts: (p: Record<string, unknown>)  => api.get('/reports/top-products', { params: p }),
  abc:         (p: Record<string, unknown>)  => api.get('/reports/abc-analysis', { params: p }),
  margin:      (p: Record<string, unknown>)  => api.get('/reports/margin', { params: p }),
  cashiers:    (p: Record<string, unknown>)  => api.get('/reports/cashier-performance', { params: p }),
  stockValue:  (wid?: string)                => api.get('/reports/stock-value', { params: { warehouse_id: wid } }),
  auditLog:    (p?: Record<string, unknown>) => api.get('/audit-log', { params: p }),
  export:      (p: Record<string, unknown>)  => api.post('/reports/export', p, { responseType: 'blob' }),
};
