'use client';

import React, { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Sparkles, ArrowLeft } from 'lucide-react';
import AppShell from '@/components/layout/AppShell';

function ComingSoonContent() {
  const searchParams = useSearchParams();
  const featureName = searchParams.get('feature') || 'Module';

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-12 text-center space-y-6 max-w-xl mx-auto backdrop-blur-sm shadow-2xl my-8">
      <div className="w-16 h-16 bg-indigo-600/20 border border-indigo-500/30 rounded-3xl flex items-center justify-center mx-auto text-indigo-400 shadow-inner">
        <Sparkles className="w-8 h-8" />
      </div>

      <div className="space-y-2">
        <h1 className="text-2xl font-extrabold text-white tracking-tight">
          {featureName} — Coming Soon
        </h1>
        <p className="text-xs text-slate-400 leading-relaxed">
          This module belongs to a future planned stage of <strong>ExamGuard AI</strong>.
          The current stage focuses on Question Bank Management, AI Question Authoring, and CSV/PDF Question Import workflows.
        </p>
      </div>

      <div className="pt-4">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/25"
        >
          <ArrowLeft className="w-4 h-4" /> Return to Dashboard
        </Link>
      </div>
    </div>
  );
}

export default function ComingSoonPage() {
  return (
    <AppShell title="Coming Soon">
      <Suspense fallback={<div className="p-12 text-center text-slate-400 text-xs font-mono">Loading...</div>}>
        <ComingSoonContent />
      </Suspense>
    </AppShell>
  );
}
