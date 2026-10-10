'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  BookOpen,
  Award,
  ShieldCheck,
  User as UserIcon,
  Clock,
  ArrowRight,
  Building2,
  GraduationCap,
  PlayCircle,
  FileCheck,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  BookmarkCheck,
} from 'lucide-react';
import { User, StudentDashboardData, dashboardAPI } from '@/lib/api';
import PageHeader from '../layout/PageHeader';

interface StudentDashboardProps {
  user: User;
}

export default function StudentDashboard({ user }: StudentDashboardProps) {
  const [data, setData] = useState<StudentDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const dashboardData = await dashboardAPI.getStudentDashboard();
      setData(dashboardData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load student dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  // Helper for format time remaining
  const formatRemainingTime = (seconds: number) => {
    if (seconds <= 0) return 'Time Expired';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins >= 60) {
      const hrs = Math.floor(mins / 60);
      const remMins = mins % 60;
      return `${hrs}h ${remMins}m remaining`;
    }
    return `${mins}m ${secs}s remaining`;
  };

  const greetingName = data?.greeting_name || `${user.first_name} ${user.last_name}`.trim() || 'Student';

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Student Dashboard"
          greetingUser={greetingName}
          subtitle="Track your upcoming examinations, results, and academic activity."
        />
        <div className="p-12 text-center text-slate-400 font-mono text-xs flex flex-col items-center justify-center gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
          <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
          <span>Loading your academic dashboard...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Student Dashboard"
          greetingUser={greetingName}
          subtitle="Track your upcoming examinations, results, and academic activity."
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

  const { summary, academic_profile, in_progress_exam, upcoming_exams, recent_results } = data;

  const formatYearOfStudy = (year?: number | null) => {
    if (!year) return 'Not assigned';
    const suffix = year === 1 ? 'st' : year === 2 ? 'nd' : year === 3 ? 'rd' : 'th';
    return `${year}${suffix} Year`;
  };

  return (
    <div className="space-y-6">
      {/* Header with Time-Based Greeting */}
      <PageHeader
        title="Student Dashboard 🎓"
        greetingUser={greetingName}
        subtitle="Track your upcoming examinations, results, and academic activity."
      />

      {/* Identity Verification Onboarding Banner (if unverified) */}
      {!user.is_face_registered && (
        <div className="p-5 rounded-2xl bg-indigo-950/40 border border-indigo-800/80 backdrop-blur-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center gap-3.5">
            <div className="p-3 bg-indigo-600/20 border border-indigo-500/30 rounded-xl text-indigo-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight">Complete Identity Verification</h3>
              <p className="text-xs text-slate-300 mt-0.5">
                Register your face descriptor before attempting a proctored examination.
              </p>
            </div>
          </div>
          <Link
            href="/profile"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-md shadow-indigo-600/20 whitespace-nowrap"
          >
            Register Face
          </Link>
        </div>
      )}

      {/* Active In-Progress Examination Card (if exists) */}
      {in_progress_exam && (
        <div className="p-6 rounded-2xl bg-gradient-to-r from-amber-950/60 via-slate-900 to-slate-900 border-2 border-amber-500/60 shadow-xl shadow-amber-950/20 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-amber-500/20 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-amber-500/20 border border-amber-500/40 rounded-xl text-amber-400 animate-pulse">
                <Clock className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-wider">
                    Exam In Progress
                  </span>
                  <span className="text-xs text-amber-400 font-mono font-bold">
                    {formatRemainingTime(in_progress_exam.remaining_seconds)}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-white mt-1">{in_progress_exam.exam_title}</h2>
                <p className="text-xs text-slate-400">Subject: {in_progress_exam.exam_subject}</p>
              </div>
            </div>

            <Link
              href={`/exam/${in_progress_exam.session_id}`}
              className="px-5 py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs rounded-xl transition shadow-lg shadow-amber-500/25 flex items-center justify-center gap-2 whitespace-nowrap"
            >
              <PlayCircle className="w-4 h-4 fill-slate-950" /> Continue Examination
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs pt-1">
            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <span className="text-slate-400 text-[11px] block">Duration</span>
              <span className="font-bold text-white font-mono text-sm">{in_progress_exam.duration_minutes} Minutes</span>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <span className="text-slate-400 text-[11px] block">Questions</span>
              <span className="font-bold text-white font-mono text-sm">{in_progress_exam.total_questions} Questions</span>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <span className="text-slate-400 text-[11px] block">Answered Progress</span>
              <span className="font-bold text-emerald-400 font-mono text-sm">
                {in_progress_exam.answered_count} / {in_progress_exam.total_questions}
              </span>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-xl">
              <span className="text-slate-400 text-[11px] block">Marked for Review</span>
              <span className="font-bold text-indigo-400 font-mono text-sm">{in_progress_exam.marked_for_review_count}</span>
            </div>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          href="/my-exams"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-blue-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Upcoming Exams</p>
            <div className="p-2 bg-blue-600/20 rounded-xl border border-blue-500/30 text-blue-400 group-hover:scale-105 transition-transform">
              <BookOpen className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.upcoming_exams}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Targeted for you</span>
            <ArrowRight className="w-3 h-3 text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href={in_progress_exam ? `/exam/${in_progress_exam.session_id}` : '/my-exams'}
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-amber-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Exams In Progress</p>
            <div className="p-2 bg-amber-600/20 rounded-xl border border-amber-500/30 text-amber-400 group-hover:scale-105 transition-transform">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-amber-300 mt-3">{summary.in_progress_exams}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Active sessions</span>
            <ArrowRight className="w-3 h-3 text-amber-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href="/results"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-purple-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Completed Exams</p>
            <div className="p-2 bg-purple-600/20 rounded-xl border border-purple-500/30 text-purple-400 group-hover:scale-105 transition-transform">
              <FileCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">{summary.completed_exams}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Submitted sessions</span>
            <ArrowRight className="w-3 h-3 text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>

        <Link
          href="/results"
          className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-emerald-500/50 hover:bg-slate-900 transition backdrop-blur-sm group cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Results Available</p>
            <div className="p-2 bg-emerald-600/20 rounded-xl border border-emerald-500/30 text-emerald-400 group-hover:scale-105 transition-transform">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">{summary.results_available}</p>
          <p className="text-[11px] text-slate-400 mt-1 flex items-center justify-between">
            <span>Evaluations ready</span>
            <ArrowRight className="w-3 h-3 text-emerald-400 opacity-0 group-hover:opacity-100 transition-opacity" />
          </p>
        </Link>
      </div>

      {/* Main Grid: Upcoming Exams & Recent Results + Academic Profile Sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Upcoming Exams & Recent Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Section 1: Upcoming Examinations */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-indigo-400" /> Upcoming Examinations
              </h3>
              <Link
                href="/my-exams"
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1"
              >
                View All <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {upcoming_exams.length === 0 ? (
              <div className="p-8 text-center bg-slate-950/40 border border-slate-800/60 rounded-xl space-y-2">
                <FileCheck className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-slate-300 font-semibold text-xs">No upcoming examinations</p>
                <p className="text-slate-500 text-[11px]">
                  There are no active or scheduled examinations assigned to your academic profile right now.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {upcoming_exams.map((ex) => (
                  <div
                    key={ex.id}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-xs">{ex.title}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                          {ex.subject}
                        </span>
                        {ex.status === 'IN_PROGRESS' && (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800/60">
                            IN PROGRESS
                          </span>
                        )}
                      </div>
                      {ex.description && <p className="text-[11px] text-slate-400 line-clamp-1">{ex.description}</p>}
                      <div className="flex items-center gap-3 text-[11px] text-slate-400 pt-1 font-mono">
                        <span>⏳ {ex.duration_minutes} Mins</span>
                        <span>•</span>
                        <span>❓ {ex.question_count} Questions</span>
                        <span>•</span>
                        <span>🏆 {ex.total_marks} Marks</span>
                      </div>
                    </div>

                    <Link
                      href={ex.active_session_id ? `/exam/${ex.active_session_id}` : '/my-exams'}
                      className={`px-4 py-2 text-xs font-semibold rounded-xl transition flex items-center justify-center gap-1.5 whitespace-nowrap ${
                        ex.status === 'IN_PROGRESS'
                          ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                          : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20'
                      }`}
                    >
                      {ex.status === 'IN_PROGRESS' ? 'Resume Exam' : 'View Exam'}
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 2: Recent Evaluation Results */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Award className="w-4 h-4 text-emerald-400" /> Recent Results & Reports
              </h3>
              <Link
                href="/results"
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1"
              >
                All Results <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {recent_results.length === 0 ? (
              <div className="p-8 text-center bg-slate-950/40 border border-slate-800/60 rounded-xl space-y-2">
                <Award className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-slate-300 font-semibold text-xs">No evaluation results available</p>
                <p className="text-slate-500 text-[11px]">
                  You have not completed any examinations with processed evaluation reports yet.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {recent_results.map((res) => {
                  const isPass = res.pass_fail_status === 'PASSED';
                  return (
                    <div
                      key={res.evaluation_id}
                      className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-xs">{res.exam_title}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono text-slate-400 bg-slate-900 border border-slate-800">
                            {res.exam_subject}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-xs pt-1">
                          <span className="font-mono text-white font-bold">
                            Score: {res.total_score} / {res.maximum_marks}
                          </span>
                          <span className="font-mono text-slate-400">({res.percentage}%)</span>
                          <span className="text-[11px] text-slate-500">
                            {new Date(res.submitted_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 justify-between sm:justify-end">
                        {res.status === 'NEEDS_SUBJECTIVE_REVIEW' ? (
                          <span className="px-2.5 py-1 rounded-lg bg-amber-950/80 border border-amber-800/80 text-amber-300 font-semibold text-[11px] font-mono">
                            Pending Review
                          </span>
                        ) : isPass ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-950/80 border border-emerald-800 text-emerald-300 font-bold text-[11px] font-mono">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> PASSED
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-300 font-bold text-[11px] font-mono">
                            <XCircle className="w-3.5 h-3.5 text-rose-400" /> FAILED
                          </span>
                        )}

                        <Link
                          href="/results"
                          className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 rounded-xl text-xs transition"
                        >
                          Details
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Academic Profile & Quick Actions */}
        <div className="space-y-6">
          {/* Academic Profile Summary Card */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <GraduationCap className="w-4 h-4 text-indigo-400" /> Academic Profile
              </h3>
              <Link
                href="/profile"
                className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 transition"
              >
                View Profile →
              </Link>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">College</span>
                <p className="font-semibold text-white">
                  {academic_profile.college_name ? (
                    <>
                      {academic_profile.college_name}{' '}
                      <span className="text-slate-400 font-mono text-[10px]">({academic_profile.college_code})</span>
                    </>
                  ) : (
                    <span className="text-slate-500 italic">Not assigned</span>
                  )}
                </p>
              </div>

              <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Department</span>
                <p className="font-semibold text-white">
                  {academic_profile.department_name ? (
                    <>
                      {academic_profile.department_name}{' '}
                      <span className="text-slate-400 font-mono text-[10px]">({academic_profile.department_code})</span>
                    </>
                  ) : (
                    <span className="text-slate-500 italic">Not assigned</span>
                  )}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Year of Study</span>
                  <p className="font-semibold text-white">
                    {academic_profile.year_of_study ? (
                      formatYearOfStudy(academic_profile.year_of_study)
                    ) : (
                      <span className="text-slate-500 italic">Not assigned</span>
                    )}
                  </p>
                </div>

                <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">Section</span>
                  <p className="font-semibold text-white">
                    {academic_profile.section_name ? (
                      <>
                        {academic_profile.section_name}{' '}
                        {academic_profile.section_code && (
                          <span className="text-slate-400 font-mono text-[10px]">({academic_profile.section_code})</span>
                        )}
                      </>
                    ) : (
                      <span className="text-slate-500 italic">Not assigned</span>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Actions Card */}
          <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm space-y-4">
            <h3 className="font-bold text-white text-sm">Quick Actions</h3>
            <div className="space-y-2">
              <Link
                href="/my-exams"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <BookOpen className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">My Exams</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
              </Link>

              <Link
                href="/results"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <Award className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">My Results</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-purple-400 transition-colors" />
              </Link>

              <Link
                href="/profile"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-blue-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <UserIcon className="w-4 h-4 text-blue-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Profile Settings</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-blue-400 transition-colors" />
              </Link>

              <Link
                href="/profile"
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900 transition flex items-center justify-between group"
              >
                <div className="flex items-center gap-3">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-slate-200 group-hover:text-white">Integrity Status</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-emerald-400 transition-colors" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
