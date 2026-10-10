'use client';

import React, { useState, useEffect } from 'react';
import { User, DashboardSummary, authAPI, dashboardAPI } from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import ExaminerDashboard from '@/components/dashboard/ExaminerDashboard';
import StudentDashboard from '@/components/dashboard/StudentDashboard';
import AdminDashboard from '@/components/dashboard/AdminDashboard';

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const u = await authAPI.getMe();
        setUser(u);
        const sum = await dashboardAPI.getSummary();
        setSummary(sum);
      } catch (err) {
        console.error('Failed to load dashboard:', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <AppShell title="Dashboard">
        <div className="flex items-center justify-center p-12 text-slate-400 font-mono text-xs">
          Loading dashboard metrics...
        </div>
      </AppShell>
    );
  }

  if (!user) return null;

  return (
    <AppShell title="Dashboard">
      {user.role === 'EXAMINER' && <ExaminerDashboard user={user} summary={summary} />}
      {user.role === 'STUDENT' && <StudentDashboard user={user} />}
      {user.role === 'ADMIN' && <AdminDashboard user={user} summary={summary} />}
    </AppShell>
  );
}
