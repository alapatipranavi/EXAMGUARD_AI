'use client';

import React from 'react';
import { Bell } from 'lucide-react';

export default function NotificationButton() {
  return (
    <button
      className="p-2 text-slate-400 hover:text-white hover:bg-slate-900 rounded-full border border-transparent hover:border-slate-800 transition relative"
      title="Notifications"
    >
      <Bell className="w-5 h-5" />
      <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-500 rounded-full animate-pulse" />
    </button>
  );
}
