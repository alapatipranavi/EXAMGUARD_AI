'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  ShieldCheck,
  LayoutDashboard,
  HelpCircle,
  PlusCircle,
  Sparkles,
  FileSpreadsheet,
  BookOpen,
  Award,
  ShieldAlert,
  User as UserIcon,
  Settings,
  Users,
  UserCheck,
  GraduationCap,
  BarChart2,
  Building2,
  X,
} from 'lucide-react';
import { User } from '@/lib/api';

interface SidebarProps {
  user: User;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  comingSoon?: boolean;
}

export default function Sidebar({ user, isMobileOpen = false, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();

  let navItems: NavItem[] = [];

  if (user.role === 'STUDENT') {
    navItems = [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'My Exams', href: '/my-exams', icon: BookOpen },
      { label: 'My Results', href: '/results', icon: Award },
      { label: 'Integrity Status', href: '/integrity', icon: ShieldAlert },
      { label: 'Profile', href: '/profile', icon: UserIcon },
      { label: 'Settings', href: '/settings', icon: Settings },
    ];
  } else if (user.role === 'EXAMINER') {
    navItems = [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'Question Bank', href: '/question-bank', icon: HelpCircle },
      { label: 'Create Question', href: '/question-bank/create', icon: PlusCircle },
      { label: 'AI Generator', href: '/question-bank/generate', icon: Sparkles },
      { label: 'Import Questions', href: '/question-bank/import', icon: FileSpreadsheet },
      { label: 'Exams', href: '/exams', icon: BookOpen },
      { label: 'Results', href: '/results', icon: Award },
      { label: 'Analytics', href: '/analytics', icon: BarChart2 },
      { label: 'Integrity', href: '/integrity', icon: ShieldAlert },
      { label: 'Cross-Student Integrity', href: '/cross-student-integrity', icon: Users },
      { label: 'Profile', href: '/profile', icon: UserIcon },
      { label: 'Settings', href: '/settings', icon: Settings },
    ];
  } else if (user.role === 'ADMIN') {
    navItems = [
      { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { label: 'User Management', href: '/users', icon: Users },
      { label: 'Academic Structure', href: '/admin/colleges', icon: Building2 },
      { label: 'Examiners', href: '/admin/examiners', icon: UserCheck },
      { label: 'Students', href: '/admin/students', icon: GraduationCap },
      { label: 'Exams', href: '/admin/exams', icon: BookOpen },
      { label: 'Integrity Monitoring', href: '/integrity', icon: ShieldAlert },
      { label: 'Cross-Student Integrity', href: '/cross-student-integrity', icon: Users },
      { label: 'Analytics', href: '/analytics', icon: BarChart2 },
      { label: 'Profile', href: '/profile', icon: UserIcon },
      { label: 'Settings', href: '/settings', icon: Settings },
    ];
  }

  const sidebarContent = (
    <div className="h-full flex flex-col justify-between bg-slate-950 border-r border-slate-800/80 w-64 p-4 text-slate-200">
      <div className="space-y-6">
        {/* Brand Header */}
        <div className="flex items-center justify-between px-2 pt-2">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/20 rounded-xl border border-indigo-500/30">
              <ShieldCheck className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="font-bold text-base text-white tracking-tight leading-none">
                ExamGuard AI
              </h1>
              <p className="text-[10px] text-slate-400 mt-1">Intelligent Examination Platform</p>
            </div>
          </div>
          {onCloseMobile && (
            <button
              onClick={onCloseMobile}
              className="lg:hidden p-1 text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.label}
                href={item.comingSoon ? `/coming-soon?feature=${encodeURIComponent(item.label)}` : item.href}
                onClick={onCloseMobile}
                className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition ${
                  isActive
                    ? 'bg-indigo-600/20 border border-indigo-500/40 text-indigo-300 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>

                {item.comingSoon && (
                  <span className="px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded bg-slate-900 text-slate-500 border border-slate-800">
                    Soon
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Role Footer */}
      <div className="p-3 bg-slate-900/60 border border-slate-800/80 rounded-xl text-xs">
        <p className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
          Active Workspace
        </p>
        <p className="font-bold text-slate-200 mt-0.5">{user.role} Environment</p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:block h-screen sticky top-0 flex-shrink-0">
        {sidebarContent}
      </aside>

      {/* Mobile Drawer Overlay */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={onCloseMobile}
          />
          <div className="relative z-10">{sidebarContent}</div>
        </div>
      )}
    </>
  );
}
