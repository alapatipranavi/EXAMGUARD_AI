'use client';

import React from 'react';
import AppShell from '@/components/layout/AppShell';
import AdminExamsView from '@/components/admin/AdminExamsView';

export default function AdminExamsPage() {
  return (
    <AppShell title="Examinations Oversight" allowedRoles={['ADMIN']}>
      <AdminExamsView />
    </AppShell>
  );
}
