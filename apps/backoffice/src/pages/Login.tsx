import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../utils/api';

export function Login() {
  const [phone,   setPhone]   = useState('');
  const [pass,    setPass]    = useState('');
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const { data } = await api.post('/auth/token', { username: phone, password: pass, grant_type: 'password' });
      localStorage.setItem('access_token',  data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('tenant_id',     data.tenant_id);
      localStorage.setItem('role',          data.user?.role ?? 'manager');
      localStorage.setItem('full_name',     data.user?.full_name ?? '');
      navigate('/');
    } catch {
      setError('Login yoki parol noto\'g\'ri');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center font-bold text-white text-lg mx-auto mb-3">PK</div>
          <div className="text-xl font-bold text-gray-800">PossKassa</div>
          <div className="text-gray-400 text-sm">Backoffice paneli</div>
        </div>
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Telefon raqam</label>
            <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} required
              placeholder="+998 90 123 45 67"
              className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-blue-400 text-sm transition-colors" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Parol</label>
            <input type="password" value={pass} onChange={e => setPass(e.target.value)} required
              placeholder="••••••••"
              className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-blue-400 text-sm transition-colors" />
          </div>
          {error && <div className="bg-red-50 text-red-600 text-sm rounded-xl px-4 py-2 text-center">{error}</div>}
          <button type="submit" disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-xl font-bold transition-colors">
            {loading ? 'Kirilmoqda...' : 'Kirish'}
          </button>
        </form>
      </div>
    </div>
  );
}
