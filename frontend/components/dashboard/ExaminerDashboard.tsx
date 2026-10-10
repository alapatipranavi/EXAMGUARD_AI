'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  BookOpen,
  FileCheck,
  Clock,
  AlertCircle,
  Building2,
  GraduationCap,
  PlusCircle,
  ArrowRight,
  RefreshCw,
  ShieldCheck,
  CheckCircle2,
  Users,
  Award,
  BarChart3,
  Layers,
  Sparkles,
  FileSpreadsheet,
  HelpCircle,
} from 'lucide-react';
import { User, ExaminerDashboardData, dashboardAPI } from '@/lib/api';
import PageHeader from '../layout/PageHeader';

interface ExaminerDashboardProps {
  user: User;
  summary?: any;
}

export default function ExaminerDashboard({ user }: ExaminerDashboardProps) {
  const [data, setData] = useState<ExaminerDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const examinerData = await dashboardAPI.getExaminerDashboard();
      setData(examinerData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load examiner dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const greetingName = data?.greeting_name || `${user.first_name} ${user.last_name}`.trim() || 'Examiner';

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Examiner Dashboard 📊"
          greetingUser={greetingName}
          subtitle="Manage your examinations, monitor student activity, and review evaluation results."
        />
        <div className="p-12 text-center text-slate-400 font-mono text-xs flex flex-col items-center justify-center gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
          <span>Loading examiner metrics and exam operations...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Examiner Dashboard 📊"
          greetingUser={greetingName}
          subtitle="Manage your examinations, monitor student activity, and review evaluation results."
        />
        <div className="p-6 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs space-y-4">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            <div>
              <p className="font-bold text-sm text-red-200">Failed to load dashboard data</p>
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

  const { summary, academic_scope, exams, pending_reviews, recent_activity } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Examiner Dashboard 📊"
        greetingUser={greetingName}
        subtitle="Manage your examinations, monitor student activity, and review evaluation results."
        actions={
          <Link
            href="/exams/create"
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 whitespace-nowrap"
          >
            <PlusCircle className="w-4 h-4" /> Create Exam
          </Link>
        }
      />

      {/* Academic Scope Banner */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-mono font-bold text-slate-400 uppercase tracking-wider block">
              Academic & Institutional Scope
            </span>
            <p className="text-xs font-semibold text-white mt-0.5">
              {academic_scope.college_name ? (
                <>
                  {academic_scope.college_name}{' '}
                  {academic_scope.college_code && (
                    <span className="text-indigo-400 font-mono text-[11px]">({academic_scope.college_code})</span>
                  )}
                </>
              ) : (
                <span className="text-slate-400 italic">College scope not assigned</span>
              )}
            </p>
          </div>
        </div>
        <div className="text-right text-[11px] text-slate-400 font-mono hidden sm:block">
          Examiner Identity Scoped
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          href="/exams"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Exams</p>
            <div className="p-2 bg-indigo-600/20 rounded-xl border border-indigo-500/30 text-indigo-400 group-hover:scale-105 transition-transform">
              <BookOpen className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.total_exams}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Owned examinations</span>
            <ArrowRight className="w-3 h-3 text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href="/exams"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-emerald-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Published Exams</p>
            <div className="p-2 bg-emerald-600/20 rounded-xl border border-emerald-500/30 text-emerald-400 group-hover:scale-105 transition-transform">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">{summary.published_exams}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Active & scheduled</span>
            <ArrowRight className="w-3 h-3 text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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
          <p className="text-[11px] text-slate-400 mt-1">Live student attempts</p>
        </div>

        <Link
          href="/results"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-purple-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Pending Reviews</p>
            <div className="p-2 bg-purple-600/20 rounded-xl border border-purple-500/30 text-purple-400 group-hover:scale-105 transition-transform">
              <FileCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-purple-300 mt-3">{summary.pending_reviews}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Manual evaluation required</span>
            <ArrowRight className="w-3 h-3 text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>
      </div>

      {/* Main Grid: Exams & Pending Reviews + Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Examinations & Pending Reviews */}
        <div className="lg:col-span-2 space-y-6">
          {/* Section 1: Examinations */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-400" /> Your Examinations
              </h3>
              <div className="flex items-center gap-3">
                <Link
                  href="/exams/create"
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1"
                >
                  <PlusCircle className="w-3.5 h-3.5" /> New Exam
                </Link>
                <Link
                  href="/exams"
                  className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition flex items-center gap-1"
                >
                  View All <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>

            {exams.length === 0 ? (
              <div className="p-8 text-center bg-slate-950/40 border border-slate-800/60 rounded-xl space-y-3">
                <BookOpen className="w-8 h-8 text-slate-600 mx-auto" />
                <div>
                  <p className="text-slate-300 font-semibold text-xs">No examinations created yet</p>
                  <p className="text-slate-500 text-[11px] mt-0.5">
                    Build your first assessment with college targeting and automated proctoring.
                  </p>
                </div>
                <Link
                  href="/exams/create"
                  className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-md shadow-indigo-600/20"
                >
                  <PlusCircle className="w-3.5 h-3.5" /> Create Exam
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {exams.slice(0, 5).map((ex) => (
                  <div
                    key={ex.id}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-bold text-white text-xs">{ex.title}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                            {ex.subject}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                              ex.status === 'PUBLISHED' || ex.status === 'ACTIVE'
                                ? 'bg-emerald-950 text-emerald-300 border-emerald-800/60'
                                : ex.status === 'DRAFT'
                                ? 'bg-slate-900 text-slate-400 border-slate-700'
                                : 'bg-blue-950 text-blue-300 border-blue-800/60'
                            }`}
                          >
                            {ex.status}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-1.5 font-mono flex-wrap">
                          <span>⏳ {ex.duration_minutes} Mins</span>
                          <span>•</span>
                          <span>❓ {ex.question_count} Questions</span>
                          <span>•</span>
                          <span>🏆 {ex.total_marks} Marks</span>
                          {ex.target_summary && (
                            <>
                              <span>•</span>
                              <span className="text-indigo-300">🎯 {ex.target_summary}</span>
                            </>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                        <span className="px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg">
                          👥 {ex.eligible_student_count} Eligible
                        </span>
                        <span className="px-2 py-1 bg-slate-900 border border-slate-800 rounded-lg">
                          📝 {ex.attempt_count} Attempts
                        </span>
                      </div>
                    </div>

                    {/* Operational Action Buttons */}
                    <div className="flex items-center gap-2 pt-2 border-t border-slate-900/80 flex-wrap text-xs">
                      <Link
                        href={`/exams/${ex.id}`}
                        className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-lg font-semibold transition text-[11px]"
                      >
                        View Exam
                      </Link>
                      <Link
                        href={`/results?exam_id=${ex.id}`}
                        className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-lg font-semibold transition text-[11px]"
                      >
                        Results
                      </Link>
                      <Link
                        href={`/analytics?exam_id=${ex.id}`}
                        className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-lg font-semibold transition text-[11px]"
                      >
                        Analytics
                      </Link>
                      <Link
                        href={`/integrity?exam_id=${ex.id}`}
                        className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-lg font-semibold transition text-[11px]"
                      >
                        Integrity
                      </Link>
                      <Link
                        href={`/cross-student-integrity?exam_id=${ex.id}`}
                        className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-indigo-300 border border-slate-800 rounded-lg font-semibold transition text-[11px]"
                      >
                        Cross-Student
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: Pending Evaluation Reviews */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-purple-400" /> Pending Evaluation Reviews
              </h3>
              <Link
                href="/results"
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1"
              >
                View All Results <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {pending_reviews.length === 0 ? (
              <div className="p-8 text-center bg-slate-950/40 border border-slate-800/60 rounded-xl space-y-2">
                <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
                <p className="text-slate-300 font-semibold text-xs">No pending evaluation reviews</p>
                <p className="text-slate-500 text-[11px]">
                  All subjective and handwritten student responses have been evaluated and finalized.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {pending_reviews.map((rev) => (
                  <div
                    key={rev.session_id}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-xs">{rev.student_name}</span>
                        <span className="text-[11px] text-slate-400">({rev.student_email})</span>
                      </div>
                      <p className="text-xs text-slate-300">
                        Exam: <span className="font-semibold text-white">{rev.exam_title}</span>
                      </p>
                      <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-0.5 font-mono">
                        <span className="text-purple-300">
                          {rev.pending_question_count} pending question(s)
                        </span>
                        {rev.submitted_at && (
                          <>
                            <span>•</span>
                            <span>Submitted: {new Date(rev.submitted_at).toLocaleTimeString()}</span>
                          </>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-3 justify-between sm:justify-end">
                      <span className="px-2.5 py-1 rounded-lg bg-purple-950/80 border border-purple-800 text-purple-300 font-semibold text-[11px] font-mono">
                        {rev.status}
                      </span>
                      <Link
                        href={`/results?session_id=${rev.session_id}`}
                        className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-xl text-xs transition shadow-md shadow-purple-600/20 whitespace-nowrap"
                      >
                        Review
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (1 Col): Recent Activity & Quick Actions */}
        <div className="space-y-6">
          {/* Quick Actions Card */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="font-bold text-white text-sm">Quick Actions</h3>
            <div className="space-y-2">
              <Link
                href="/exams/create"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <PlusCircle className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Create Exam</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
              </Link>

              <Link
                href="/question-bank"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-blue-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <HelpCircle className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Question Bank</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400 transition-colors" />
              </Link>

              <Link
                href="/results"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <Award className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Results & Reviews</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-purple-400 transition-colors" />
              </Link>

              <Link
                href="/analytics"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <BarChart3 className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Analytics</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
              </Link>

              <Link
                href="/integrity"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-rose-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-4 h-4 text-rose-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Integrity Monitoring</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-rose-400 transition-colors" />
              </Link>

              <Link
                href="/cross-student-integrity"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-amber-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <Layers className="w-4 h-4 text-amber-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Cross-Student Analysis</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-amber-400 transition-colors" />
              </Link>
            </div>
          </div>

          {/* Recent Examination Activity */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="font-bold text-white text-sm">Recent Activity</h3>

            {recent_activity.length === 0 ? (
              <div className="p-6 text-center bg-slate-950/40 border border-slate-800/60 rounded-xl space-y-1">
                <Clock className="w-6 h-6 text-slate-600 mx-auto" />
                <p className="text-slate-300 font-semibold text-xs">No recent activity</p>
                <p className="text-slate-500 text-[11px]">No student sessions recorded yet.</p>
              </div>
            ) : (
              <div className="space-y-3 text-xs">
                {recent_activity.map((act) => (
                  <div key={act.id} className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                    <p className="text-slate-200 font-medium leading-relaxed">{act.description}</p>
                    <p className="text-[10px] text-slate-500 font-mono">
                      {new Date(act.timestamp).toLocaleString()}
                    </p>
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
