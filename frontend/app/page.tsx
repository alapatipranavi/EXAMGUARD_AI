'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ShieldCheck, Cpu, Database, Server, Terminal, Activity, CheckCircle2, LogIn, UserPlus, Sparkles } from 'lucide-react';
import { authAPI, User } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const [apiHealth, setApiHealth] = useState<{ status: string; service: string } | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loadingAuth, setLoadingAuth] = useState<boolean>(true);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${apiUrl}/api/health`, { cache: 'no-store' });
        if (res.ok) {
          const data = await res.json();
          setApiHealth(data);
          setHealthError(null);
        } else {
          setHealthError(`HTTP Error ${res.status}`);
        }
      } catch (err: unknown) {
        setHealthError(err instanceof Error ? err.message : 'Backend unreachable');
      } finally {
        setLoadingHealth(false);
      }
    }

    async function checkCurrentUser() {
      try {
        const user = await authAPI.getMe();
        setCurrentUser(user);
        // Authenticated users are automatically redirected to /dashboard
        router.replace('/dashboard');
      } catch {
        setCurrentUser(null);
      } finally {
        setLoadingAuth(false);
      }
    }

    checkHealth();
    checkCurrentUser();
  }, [apiUrl, router]);

  if (loadingAuth || currentUser) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="flex items-center gap-3 text-slate-400 font-mono text-sm">
          <span className="animate-spin text-indigo-400">⏳</span> Checking session identity...
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-between p-6 md:p-12 max-w-6xl mx-auto">
      {/* Header Badge */}
      <header className="w-full flex justify-between items-center py-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 rounded-xl border border-indigo-500/30">
            <ShieldCheck className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight">ExamGuard AI</h1>
            <p className="text-xs text-slate-400">Stage 4.5 — Platform Shell & AI Question Bank</p>
          </div>
        </div>

        {/* Auth Buttons */}
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="px-3.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-200 hover:text-white transition flex items-center gap-1.5"
          >
            <LogIn className="w-3.5 h-3.5 text-indigo-400" /> Sign In
          </Link>
          <Link
            href="/register"
            className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
          >
            <UserPlus className="w-3.5 h-3.5" /> Register
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="my-12 text-center space-y-6 max-w-3xl">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium text-indigo-300 bg-indigo-950/60 border border-indigo-800/50 rounded-full">
          <Activity className="w-3.5 h-3.5" /> Intelligent Examination & Integrity System Active
        </div>
        <h2 className="text-4xl md:text-5xl font-extrabold text-white tracking-tight leading-tight">
          ExamGuard AI
        </h2>
        <p className="text-xl md:text-2xl font-semibold text-indigo-400">
          Intelligent Examination and Integrity Assessment System
        </p>
        <p className="text-slate-400 text-sm md:text-base leading-relaxed">
          AI-assisted Question Bank management, automated question generation, CSV/PDF question import workflows, 
          and secure role-based examination infrastructure.
        </p>

        <div className="flex items-center justify-center gap-4 pt-4">
          <Link
            href="/register"
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-sm text-white transition flex items-center gap-2 shadow-lg shadow-indigo-600/25"
          >
            <UserPlus className="w-4 h-4" /> Get Started
          </Link>
          <Link
            href="/login"
            className="px-6 py-3 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 font-semibold text-sm text-slate-200 hover:text-white transition flex items-center gap-2"
          >
            <LogIn className="w-4 h-4 text-indigo-400" /> Sign In
          </Link>
        </div>
      </section>

      {/* Backend Integration Status Card */}
      <section className="w-full bg-slate-900/80 border border-slate-800 rounded-2xl p-6 md:p-8 backdrop-blur-sm shadow-xl my-4">
        <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5 text-indigo-400" />
            <h3 className="font-semibold text-white">System & Identity Status</h3>
          </div>
          <span className="text-xs font-mono text-slate-400">{apiUrl}/api/health</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">API Health Check</p>
            {loadingHealth ? (
              <p className="text-sm text-slate-400 flex items-center gap-2">
                <span className="animate-spin text-indigo-400">⏳</span> Verifying backend...
              </p>
            ) : apiHealth ? (
              <div className="flex items-center gap-2 text-emerald-400 font-mono text-sm font-semibold">
                <CheckCircle2 className="w-4 h-4" /> Operational ({apiHealth.service})
              </div>
            ) : (
              <p className="text-sm text-amber-400 font-mono">
                Offline ({healthError || 'Check Backend Server'})
              </p>
            )}
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Authenticated Session</p>
            <p className="text-sm text-slate-400 font-mono">No active session (Guest)</p>
          </div>
        </div>
      </section>

      {/* Tech Stack Cards */}
      <section className="w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 my-8">
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition">
          <Terminal className="w-5 h-5 text-indigo-400 mb-2" />
          <h4 className="font-semibold text-sm text-white">Next.js 15 & React 19</h4>
          <p className="text-xs text-slate-400 mt-1">AppShell layout, credentials: &quot;include&quot;</p>
        </div>
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition">
          <Sparkles className="w-5 h-5 text-purple-400 mb-2" />
          <h4 className="font-semibold text-sm text-white">AI Authoring Assistant</h4>
          <p className="text-xs text-slate-400 mt-1">Transient draft generation & reviewer workflow</p>
        </div>
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition">
          <Database className="w-5 h-5 text-emerald-400 mb-2" />
          <h4 className="font-semibold text-sm text-white">Question Source Tracking</h4>
          <p className="text-xs text-slate-400 mt-1">MANUAL, AI_GENERATED, CSV, PDF tracking</p>
        </div>
        <div className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition">
          <Cpu className="w-5 h-5 text-amber-400 mb-2" />
          <h4 className="font-semibold text-sm text-white">FastAPI RBAC</h4>
          <p className="text-xs text-slate-400 mt-1">Student, Examiner, Admin role isolation</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full py-6 border-t border-slate-800 text-center text-xs text-slate-500">
        ExamGuard AI © 2026 — Stage 4.5 Platform Shell Operational
      </footer>
    </main>
  );
}
