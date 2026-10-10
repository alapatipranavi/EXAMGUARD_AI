'use client';

import React from 'react';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  greetingUser?: string;
  actions?: React.ReactNode;
}

export default function PageHeader({
  title,
  subtitle,
  greetingUser,
  actions,
}: PageHeaderProps) {
  // Determine local browser time greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good Morning';
    if (hour < 18) return 'Good Afternoon';
    return 'Good Evening';
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      <div className="space-y-1">
        {greetingUser ? (
          <h1 className="text-2xl font-extrabold text-white tracking-tight">
            {getGreeting()}, {greetingUser} 👋
          </h1>
        ) : (
          <h1 className="text-2xl font-extrabold text-white tracking-tight">{title}</h1>
        )}
        {subtitle && <p className="text-sm text-slate-400">{subtitle}</p>}
      </div>

      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}
