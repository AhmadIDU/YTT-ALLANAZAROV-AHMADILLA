/**
 * Asosiy Layout — Sidebar + Header + Kontent
 */
import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ShoppingCart, Package, TruckIcon,
  BarChart3, Users, Settings, LogOut, ChevronLeft,
  ChevronRight, Bell, AlertTriangle, ClipboardList,
} from 'lucide-react';
import clsx from 'clsx';

const NAV = [
  { label: 'Dashboard',      icon: LayoutDashboard, path: '/',             roles: ['manager','admin','owner'] },
  { label: 'Sotuvlar',       icon: ShoppingCart,    path: '/sales',        roles: ['cashier','manager','admin','owner'] },
  { label: 'Mahsulotlar',    icon: Package,         path: '/products',     roles: ['manager','admin','owner'] },
  { label: 'Tovar qabuli',   icon: TruckIcon,       path: '/intake',       roles: ['manager','admin','owner'] },
  { label: 'Hisobotlar',     icon: BarChart3,        path: '/reports',      roles: ['manager','admin','owner'] },
  { label: 'Foydalanuvchilar',icon: Users,           path: '/users',        roles: ['admin','owner'] },
  { label: 'Audit jurnali',  icon: ClipboardList,   path: '/audit',        roles: ['admin','owner'] },
  { label: 'Sozlamalar',     icon: Settings,        path: '/settings',     roles: ['admin','owner'] },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const location  = useLocation();
  const navigate  = useNavigate();
  const userRole  = localStorage.getItem('role') ?? 'manager';
  const userName  = localStorage.getItem('full_name') ?? 'Foydalanuvchi';

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans">
      {/* ── Sidebar ─────────────────────────────────── */}
      <aside className={clsx(
        'flex flex-col bg-gray-900 text-white transition-all duration-200 shrink-0',
        collapsed ? 'w-16' : 'w-60'
      )}>
        {/* Logo */}
        <div className={clsx('flex items-center gap-3 px-4 py-5 border-b border-gray-800',
          collapsed && 'justify-center px-2')}>
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center font-bold text-sm shrink-0">
            PK
          </div>
          {!collapsed && (
            <div>
              <div className="font-bold text-sm">PossKassa</div>
              <div className="text-xs text-gray-400">Backoffice</div>
            </div>
          )}
        </div>

        {/* Navigatsiya */}
        <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
          {NAV.filter(item => item.roles.includes(userRole)).map(item => {
            const active = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                to={item.path}
                title={collapsed ? item.label : undefined}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
                  active
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white',
                  collapsed && 'justify-center px-2'
                )}
              >
                <item.icon size={18} className="shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Foydalanuvchi va yig'ishtirish */}
        <div className="border-t border-gray-800 p-2 space-y-1">
          {!collapsed && (
            <div className="px-3 py-2 text-xs text-gray-400">
              <div className="font-medium text-gray-200 truncate">{userName}</div>
              <div className="capitalize">{userRole}</div>
            </div>
          )}
          <button
            onClick={handleLogout}
            className={clsx(
              'flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm',
              'text-gray-400 hover:bg-red-900/40 hover:text-red-400 transition-colors',
              collapsed && 'justify-center px-2'
            )}
          >
            <LogOut size={18} />
            {!collapsed && <span>Chiqish</span>}
          </button>
          <button
            onClick={() => setCollapsed(v => !v)}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-gray-500 hover:text-gray-300 transition-colors"
          >
            {collapsed
              ? <ChevronRight size={18} className="mx-auto" />
              : <><ChevronLeft size={18} /><span>Yig'ishtirish</span></>}
          </button>
        </div>
      </aside>

      {/* ── Asosiy kontent ──────────────────────────── */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-200 shrink-0">
          <div className="text-gray-500 text-sm">
            {NAV.find(n => location.pathname === n.path || (n.path !== '/' && location.pathname.startsWith(n.path)))?.label ?? 'PossKassa'}
          </div>
          <div className="flex items-center gap-3">
            <button className="relative p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
              <Bell size={18} />
            </button>
            <LowStockBadge />
          </div>
        </header>

        {/* Sahifa kontent */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

function LowStockBadge() {
  return (
    <Link
      to="/products?filter=low_stock"
      className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 text-orange-600 rounded-lg text-xs font-medium hover:bg-orange-100 transition-colors"
    >
      <AlertTriangle size={14} />
      Kam zaxira
    </Link>
  );
}
