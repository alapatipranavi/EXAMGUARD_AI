'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { User as UserIcon, LogOut, UserCheck, Settings } from 'lucide-react';
import { User, authAPI } from '@/lib/api';

interface UserMenuProps {
  user: User;
  onLogout?: () => void;
}

export default function UserMenu({ user, onLogout }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    try {
      await authAPI.logout();
      if (onLogout) onLogout();
      window.location.href = '/login';
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 hover:border-slate-700 transition focus:outline-none"
      >
        <div className="w-7 h-7 rounded-full bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-indigo-300 font-bold text-xs">
          {user.first_name[0]}{user.last_name[0]}
        </div>
        <div className="text-left hidden sm:block">
          <p className="text-xs font-semibold text-slate-200 leading-tight">
            {user.first_name} {user.last_name}
          </p>
          <p className="text-[10px] text-slate-400 font-mono">{user.role}</p>
        </div>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl py-2 z-50 divide-y divide-slate-800/80">
          <div className="px-4 py-2.5">
            <p className="text-xs font-bold text-white">
              {user.first_name} {user.last_name}
            </p>
            <p className="text-xs text-slate-400 truncate">{user.email}</p>
            <span className="mt-1.5 inline-block px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/60">
              {user.role}
            </span>
          </div>

          <div className="py-1">
            <Link
              href="/profile"
              className="flex items-center gap-2.5 px-4 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 transition"
              onClick={() => setIsOpen(false)}
            >
              <UserCheck className="w-4 h-4 text-indigo-400" />
              <span>My Profile</span>
            </Link>
            <Link
              href="/settings"
              className="flex items-center gap-2.5 px-4 py-2 text-xs text-slate-300 hover:text-white hover:bg-slate-800/60 transition"
              onClick={() => setIsOpen(false)}
            >
              <Settings className="w-4 h-4 text-slate-400" />
              <span>Settings</span>
            </Link>
          </div>

          <div className="py-1">
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2.5 px-4 py-2 text-xs text-red-400 hover:text-red-300 hover:bg-red-950/30 transition text-left"
            >
              <LogOut className="w-4 h-4" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
