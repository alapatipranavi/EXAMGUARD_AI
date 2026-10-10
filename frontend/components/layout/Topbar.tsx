'use client';

import React from 'react';
import { Menu } from 'lucide-react';
import { User } from '@/lib/api';
import NotificationButton from './NotificationButton';
import UserMenu from './UserMenu';

interface TopbarProps {
  user: User;
  onOpenMobileSidebar?: () => void;
  title?: string;
}

export default function Topbar({ user, onOpenMobileSidebar, title }: TopbarProps) {
  return (
    <header className="h-16 bg-slate-950/90 border-b border-slate-800/80 sticky top-0 z-30 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileSidebar}
          className="lg:hidden p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-900 transition"
          title="Open Menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h2 className="text-sm font-bold text-white tracking-tight">
          {title || 'ExamGuard AI'}
        </h2>
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        <NotificationButton />
        <div className="h-5 w-[1px] bg-slate-800 hidden sm:block" />
        <UserMenu user={user} />
      </div>
    </header>
  );
}
