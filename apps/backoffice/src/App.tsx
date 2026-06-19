import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { Layout }   from './components/Layout';
import { Login }    from './pages/Login';
import { Dashboard }from './pages/Dashboard';
import { Products } from './pages/Products';
import { Intake }   from './pages/Intake';
import { Reports }  from './pages/Reports';

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } });

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!localStorage.getItem('access_token')) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{ duration: 3500 }} />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/"        element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/products"element={<ProtectedRoute><Products /></ProtectedRoute>} />
          <Route path="/intake"  element={<ProtectedRoute><Intake /></ProtectedRoute>} />
          <Route path="/reports" element={<ProtectedRoute><Reports /></ProtectedRoute>} />
          <Route path="*"        element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
