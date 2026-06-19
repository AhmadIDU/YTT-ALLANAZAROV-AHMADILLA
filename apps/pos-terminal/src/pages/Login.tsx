/**
 * Login sahifasi
 */
import React, { useState } from 'react';
import { apiClient } from '../utils/apiClient';
import { usePosStore } from '../store/posStore';

export function Login() {
  const [phone,    setPhone]    = useState('');
  const [pin,      setPin]      = useState('');
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState('');
  const setUser    = usePosStore(s => s.setCurrentUser);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const { data } = await apiClient.post('/auth/token', {
        username: phone,
        password: pin,
        grant_type: 'password',
      });
      localStorage.setItem('access_token',  data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      localStorage.setItem('tenant_id',     data.tenant_id);
      setUser(data.user);
      window.location.href = '/';
    } catch {
      setError('Login yoki parol noto\'g\'ri');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-4xl font-extrabold text-blue-700">PossKassa</div>
          <p className="text-gray-400 text-sm mt-1">Kassa tizimiga kirish</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">Telefon raqam</label>
            <input
              type="tel"
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="+998 90 123 45 67"
              className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-blue-400 transition-colors"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-600 mb-1">PIN kod</label>
            <input
              type="password"
              value={pin}
              onChange={e => setPin(e.target.value)}
              placeholder="••••"
              maxLength={6}
              className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 outline-none focus:border-blue-400 transition-colors text-center text-2xl tracking-widest"
              required
            />
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm rounded-lg px-4 py-2 text-center">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white rounded-xl font-bold text-lg transition-colors"
          >
            {loading ? 'Kirilmoqda...' : 'Kirish'}
          </button>
        </form>
      </div>
    </div>
  );
}
