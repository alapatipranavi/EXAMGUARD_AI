'use client';

import React from 'react';
import AppShell from '@/components/layout/AppShell';
import AdminExaminersView from '@/components/admin/AdminExaminersView';

export default function AdminExaminersPage() {
  return (
    <AppShell title="Examiners" allowedRoles={['ADMIN']}>
      <AdminExaminersView />
    </AppShell>
  );
}
