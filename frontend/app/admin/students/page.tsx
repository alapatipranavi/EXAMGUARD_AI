'use client';

import React from 'react';
import AppShell from '@/components/layout/AppShell';
import AdminStudentsView from '@/components/admin/AdminStudentsView';

export default function AdminStudentsPage() {
  return (
    <AppShell title="Students" allowedRoles={['ADMIN']}>
      <AdminStudentsView />
    </AppShell>
  );
}
