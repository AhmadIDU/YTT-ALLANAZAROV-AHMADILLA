import React from 'react';
import type { LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface Props {
  label:    string;
  value:    string | number;
  sub?:     string;
  icon:     LucideIcon;
  color?:   'blue' | 'green' | 'orange' | 'purple' | 'red';
  trend?:   number;   // foiz o'zgarish
}

const COLORS = {
  blue:   'bg-blue-50   text-blue-600   border-blue-100',
  green:  'bg-green-50  text-green-600  border-green-100',
  orange: 'bg-orange-50 text-orange-600 border-orange-100',
  purple: 'bg-purple-50 text-purple-600 border-purple-100',
  red:    'bg-red-50    text-red-600    border-red-100',
};

export function StatCard({ label, value, sub, icon: Icon, color = 'blue', trend }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-500 mb-1">{label}</p>
          <p className="text-2xl font-bold text-gray-800 truncate">{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
          {trend !== undefined && (
            <p className={clsx('text-xs font-medium mt-1', trend >= 0 ? 'text-green-600' : 'text-red-500')}>
              {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}% kechagiga nisbatan
            </p>
          )}
        </div>
        <div className={clsx('p-3 rounded-xl border shrink-0 ml-3', COLORS[color])}>
          <Icon size={22} />
        </div>
      </div>
    </div>
  );
}
