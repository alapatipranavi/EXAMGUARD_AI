'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  UserCheck,
  BookOpen,
  ShieldCheck,
  BarChart3,
  Building2,
  GraduationCap,
  Layers,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  PlusCircle,
  Activity,
  Server,
  Database,
  FileCheck,
  UserX,
} from 'lucide-react';
import { User, AdminDashboardData, dashboardAPI } from '@/lib/api';
import PageHeader from '../layout/PageHeader';

interface AdminDashboardProps {
  user: User;
  summary?: any;
}

export default function AdminDashboard({ user }: AdminDashboardProps) {
  const [data, setData] = useState<AdminDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const adminData = await dashboardAPI.getAdminDashboard();
      setData(adminData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load system administration dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const greetingName = data?.greeting_name || `${user.first_name} ${user.last_name}`.trim() || 'Administrator';

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="System Administration Dashboard 🛡️"
          greetingUser={greetingName}
          subtitle="Monitor the examination platform and manage system activity."
        />
        <div className="p-12 text-center text-slate-400 font-mono text-xs flex flex-col items-center justify-center gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
          <span>Loading system administration metrics...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="System Administration Dashboard 🛡️"
          greetingUser={greetingName}
          subtitle="Monitor the examination platform and manage system activity."
        />
        <div className="p-6 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs space-y-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            <div>
              <p className="font-bold text-sm text-red-200">Failed to load admin dashboard metrics</p>
              <p className="text-red-300/80 text-xs mt-0.5">{error || 'An unexpected error occurred.'}</p>
            </div>
          </div>
          <button
            onClick={fetchDashboardData}
            className="px-4 py-2 bg-slate-900 border border-slate-700 hover:border-slate-600 text-slate-200 font-semibold rounded-xl text-xs flex items-center gap-2 transition"
          >
            <RefreshCw className="w-3.5 h-3.5 text-indigo-400" /> Retry Loading
          </button>
        </div>
      </div>
    );
  }

  const { summary, users, academic, examinations, recent_activity, system_status } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="System Administration Dashboard 🛡️"
        greetingUser={greetingName}
        subtitle="Monitor the examination platform and manage system activity."
        actions={
          <div className="flex items-center gap-3">
            <Link
              href="/users"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2"
            >
              <Users className="w-4 h-4" /> Manage Users
            </Link>
            <Link
              href="/admin/colleges"
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold rounded-xl transition flex items-center gap-2"
            >
              <Building2 className="w-4 h-4 text-indigo-400" /> Academic Structure
            </Link>
          </div>
        }
      />

      {/* Primary Summary Metrics (Row 1 & 2) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          href="/admin/students"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Students</p>
            <div className="p-2 bg-indigo-600/20 rounded-xl border border-indigo-500/30 text-indigo-400 group-hover:scale-105 transition-transform">
              <GraduationCap className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.total_students}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>{users.total_students} total registered</span>
            <ArrowRight className="w-3 h-3 text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href="/admin/examiners"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-emerald-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Examiners</p>
            <div className="p-2 bg-emerald-600/20 rounded-xl border border-emerald-500/30 text-emerald-400 group-hover:scale-105 transition-transform">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">{summary.total_examiners}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>{users.total_examiners} total provisioned</span>
            <ArrowRight className="w-3 h-3 text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href="/admin/exams"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-blue-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Exams</p>
            <div className="p-2 bg-blue-600/20 rounded-xl border border-blue-500/30 text-blue-400 group-hover:scale-105 transition-transform">
              <BookOpen className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.total_exams}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Platform assessments</span>
            <ArrowRight className="w-3 h-3 text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Sessions</p>
            <div className="p-2 bg-amber-600/20 rounded-xl border border-amber-500/30 text-amber-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-amber-300 mt-3">{summary.active_sessions}</p>
          <p className="text-[11px] text-slate-400 mt-1">Live in-progress sessions</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Completed Sessions</p>
            <div className="p-2 bg-purple-600/20 rounded-xl border border-purple-500/30 text-purple-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.completed_exams}</p>
          <p className="text-[11px] text-slate-400 mt-1">Submitted assessments</p>
        </div>

        <Link
          href="/results"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-rose-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pending Reviews</p>
            <div className="p-2 bg-rose-600/20 rounded-xl border border-rose-500/30 text-rose-400 group-hover:scale-105 transition-transform">
              <FileCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-rose-300 mt-3">{summary.pending_reviews}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Subjective reviews queue</span>
            <ArrowRight className="w-3 h-3 text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href="/admin/colleges"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Colleges</p>
            <div className="p-2 bg-indigo-600/20 rounded-xl border border-indigo-500/30 text-indigo-400 group-hover:scale-105 transition-transform">
              <Building2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.total_colleges}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Institutions configured</span>
            <ArrowRight className="w-3 h-3 text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href="/admin/colleges"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-emerald-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Departments</p>
            <div className="p-2 bg-emerald-600/20 rounded-xl border border-emerald-500/30 text-emerald-400 group-hover:scale-105 transition-transform">
              <GraduationCap className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.total_departments}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Academic departments</span>
            <ArrowRight className="w-3 h-3 text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>
      </div>

      {/* Main Grid: User Overview, Academic Overview & Exam Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): User, Academic & Exam Breakdown */}
        <div className="lg:col-span-2 space-y-6">
          {/* User Overview Section */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-400" /> User Accounts & Provisioning
              </h3>
              <Link
                href="/users"
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1"
              >
                Manage Users <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Students</span>
                <p className="font-bold text-white text-base">
                  {users.active_students}{' '}
                  <span className="text-slate-500 text-xs font-normal">/ {users.total_students}</span>
                </p>
                <span className="text-[10px] text-emerald-400 block">Active Students</span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Examiners</span>
                <p className="font-bold text-white text-base">
                  {users.active_examiners}{' '}
                  <span className="text-slate-500 text-xs font-normal">/ {users.total_examiners}</span>
                </p>
                <span className="text-[10px] text-emerald-400 block">Active Examiners</span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Inactive Accounts</span>
                <p className="font-bold text-amber-400 text-base">{users.inactive_users}</p>
                <span className="text-[10px] text-slate-500 block">Deactivated Users</span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Provisioning</span>
                <p className="font-bold text-indigo-300 text-base">Admin RBAC</p>
                <span className="text-[10px] text-indigo-400 block">Role Scoped</span>
              </div>
            </div>
          </div>

          {/* Academic Structure Overview Section */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Building2 className="w-4 h-4 text-emerald-400" /> Academic Structure & Targeting
              </h3>
              <Link
                href="/admin/colleges"
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition flex items-center gap-1"
              >
                Manage Academic Structure <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Colleges</span>
                <p className="font-bold text-white text-base">{academic.total_colleges}</p>
                <span className="text-[10px] text-slate-400 block">Institutions</span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Departments</span>
                <p className="font-bold text-white text-base">{academic.total_departments}</p>
                <span className="text-[10px] text-slate-400 block">Academic Units</span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Sections</span>
                <p className="font-bold text-white text-base">{academic.total_sections}</p>
                <span className="text-[10px] text-slate-400 block">Class Batches</span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Scoped Profiles</span>
                <p className="font-bold text-emerald-400 text-base">{academic.students_with_academic_profiles}</p>
                <span className="text-[10px] text-slate-400 block">Targeted Students</span>
              </div>
            </div>
          </div>

          {/* Examination Overview Section */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-blue-400" /> Platform Examinations Overview
              </h3>
              <Link
                href="/admin/exams"
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1"
              >
                View Exams <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-center space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase block">Draft</span>
                <p className="font-bold text-slate-300 text-lg">{examinations.draft}</p>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-center space-y-1">
                <span className="text-[10px] font-semibold text-emerald-400 uppercase block">Published</span>
                <p className="font-bold text-emerald-400 text-lg">{examinations.published}</p>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-center space-y-1">
                <span className="text-[10px] font-semibold text-blue-400 uppercase block">Scheduled</span>
                <p className="font-bold text-blue-400 text-lg">{examinations.scheduled}</p>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-center space-y-1">
                <span className="text-[10px] font-semibold text-amber-400 uppercase block">Active</span>
                <p className="font-bold text-amber-300 text-lg">{examinations.active}</p>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-center space-y-1">
                <span className="text-[10px] font-semibold text-purple-400 uppercase block">Completed</span>
                <p className="font-bold text-purple-300 text-lg">{examinations.completed}</p>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-center space-y-1">
                <span className="text-[10px] font-semibold text-slate-500 uppercase block">Archived</span>
                <p className="font-bold text-slate-500 text-lg">{examinations.archived}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column (1 Col): Activity Feed, System Health & Quick Actions */}
        <div className="space-y-6">
          {/* System Health / Operational Status */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="font-bold text-white text-sm flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" /> System Health & Status
            </h3>

            <div className="space-y-2.5 text-xs">
              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Server className="w-4 h-4 text-indigo-400" />
                  <span className="font-semibold text-slate-200">Backend API</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                  {system_status.backend.toUpperCase()}
                </span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Database className="w-4 h-4 text-emerald-400" />
                  <span className="font-semibold text-slate-200">Database</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                  {system_status.database.toUpperCase()}
                </span>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-blue-400" />
                  <span className="font-semibold text-slate-200">Platform Version</span>
                </div>
                <span className="font-mono text-slate-400 text-xs">v{system_status.version}</span>
              </div>
            </div>
          </div>

          {/* Quick Actions Card */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="font-bold text-white text-sm">Quick Actions</h3>
            <div className="space-y-2">
              <Link
                href="/users"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <Users className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">User Management</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
              </Link>

              <Link
                href="/admin/students"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <GraduationCap className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Students Management</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
              </Link>

              <Link
                href="/admin/examiners"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <UserCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Examiners Management</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
              </Link>

              <Link
                href="/admin/colleges"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <Building2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Academic Structure</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
              </Link>

              <Link
                href="/admin/exams"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-blue-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <BookOpen className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">View Examinations</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400 transition-colors" />
              </Link>

              <Link
                href="/analytics"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <BarChart3 className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">System Analytics</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-purple-400 transition-colors" />
              </Link>

              <Link
                href="/integrity"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-rose-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-4 h-4 text-rose-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Integrity Intelligence</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-rose-400 transition-colors" />
              </Link>
            </div>
          </div>

          {/* Recent Platform Activity */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="font-bold text-white text-sm">Recent Platform Activity</h3>

            {recent_activity.length === 0 ? (
              <div className="p-6 text-center bg-slate-950/40 border border-slate-800/60 rounded-xl space-y-1">
                <Clock className="w-6 h-6 text-slate-600 mx-auto" />
                <p className="text-slate-300 font-semibold text-xs">No recent platform activity</p>
                <p className="text-slate-500 text-[11px]">System activity log is currently empty.</p>
              </div>
            ) : (
              <div className="space-y-3 text-xs">
                {recent_activity.map((act) => (
                  <div key={act.id} className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="px-2 py-0.5 text-[9px] font-mono font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60 uppercase">
                        {act.event_type}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(act.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-slate-200 font-medium leading-relaxed pt-1">{act.description}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
