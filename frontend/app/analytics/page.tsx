'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import {
  BarChart3,
  TrendingUp,
  Award,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Filter,
  Users,
  ChevronRight,
  AlertCircle,
  BookOpen,
  Lock,
  UserCheck,
  HelpCircle,
  Layers,
  ArrowUpRight,
  PieChart,
} from 'lucide-react';
import {
  authAPI,
  examsAPI,
  analyticsAPI,
  User,
  Exam,
  ExamAnalyticsResponse,
  StudentResultResponse,
  QuestionPerformanceItem,
  PendingReviewItem,
} from '@/lib/api';

export default function AnalyticsPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>('');
  const [analyticsData, setAnalyticsData] = useState<ExamAnalyticsResponse | null>(null);
  const [loadingExams, setLoadingExams] = useState(true);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Student Performance Table Filter State
  const [search, setSearch] = useState('');
  const [passFailFilter, setPassFailFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    authAPI
      .getMe()
      .then((user) => {
        setCurrentUser(user);
        if (user.role === 'STUDENT') {
          setError('Access forbidden: Students are not authorized to view exam analytics.');
          setLoadingExams(false);
          return;
        }
        fetchExamsList();
      })
      .catch(() => {
        setCurrentUser(null);
        setLoadingExams(false);
      });
  }, []);

  const fetchExamsList = async () => {
    setLoadingExams(true);
    try {
      const res = await examsAPI.list({ page: 1, page_size: 100 });
      setExams(res.items);
      if (res.items.length > 0) {
        setSelectedExamId(res.items[0].id);
        fetchAnalytics(res.items[0].id, 1, '', '', '');
      } else {
        setLoadingExams(false);
      }
    } catch (err: any) {
      console.error('Failed to load exams list:', err);
      setError(err.message || 'Failed to load examinations list.');
      setLoadingExams(false);
    }
  };

  const fetchAnalytics = async (
    examId: string,
    pageNum: number,
    searchQuery: string,
    pfFilter: string,
    stFilter: string
  ) => {
    if (!examId) return;
    setLoadingAnalytics(true);
    setError(null);
    try {
      const data = await analyticsAPI.getExamAnalytics(examId, {
        page: pageNum,
        page_size: 10,
        search: searchQuery,
        pass_fail: pfFilter,
        session_status: stFilter,
      });
      setAnalyticsData(data);
    } catch (err: any) {
      console.error('Failed to fetch analytics:', err);
      setError(err.message || 'Failed to fetch exam analytics.');
    } finally {
      setLoadingAnalytics(false);
      setLoadingExams(false);
    }
  };

  const handleExamChange = (newExamId: string) => {
    setSelectedExamId(newExamId);
    setPage(1);
    setSearch('');
    setPassFailFilter('');
    setStatusFilter('');
    fetchAnalytics(newExamId, 1, '', '', '');
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchAnalytics(selectedExamId, 1, search, passFailFilter, statusFilter);
  };

  const handleFilterApply = (pf: string, st: string) => {
    setPassFailFilter(pf);
    setStatusFilter(st);
    setPage(1);
    fetchAnalytics(selectedExamId, 1, search, pf, st);
  };

  if (currentUser?.role === 'STUDENT') {
    return (
      <AppShell title="Analytics Forbidden">
        <div className="max-w-4xl mx-auto p-6 text-center space-y-4 pt-12">
          <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl inline-block text-rose-400">
            <AlertCircle className="w-12 h-12" />
          </div>
          <h2 className="text-xl font-bold text-white">Access Forbidden</h2>
          <p className="text-slate-400 text-xs max-w-md mx-auto">
            Exam Analytics are only available to Examiners and Administrators. Students are not authorized to view aggregated exam analytics.
          </p>
          <Link
            href="/dashboard"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl transition inline-block mt-2"
          >
            Return to Dashboard
          </Link>
        </div>
      </AppShell>
    );
  }

  const summary = analyticsData?.summary;
  const scorePerf = analyticsData?.score_performance;
  const scoreDist = analyticsData?.score_distribution;
  const passFailDist = analyticsData?.pass_fail_distribution;
  const finalizedPerf = analyticsData?.finalized_performance;
  const examInfo = analyticsData?.exam_info;

  // Max bucket count for scaling bar chart
  const maxBucketCount = scoreDist
    ? Math.max(
        scoreDist.bucket_0_20,
        scoreDist.bucket_21_40,
        scoreDist.bucket_41_60,
        scoreDist.bucket_61_80,
        scoreDist.bucket_81_100,
        1
      )
    : 1;

  return (
    <AppShell title="Exam Analytics" allowedRoles={['EXAMINER', 'ADMIN']}>
      <div className="space-y-6 max-w-7xl mx-auto pb-16">
        {/* Header */}
        <PageHeader
          title="Exam Analytics & Performance Insights"
          subtitle="Real-time aggregation of student evaluation scores, grade distributions, question accuracy metrics, and pending subjective review tracking."
        />

        {/* Exam Selector Toolbar */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <label className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                Selected Examination
              </label>
              <p className="text-xs text-slate-300 font-semibold">
                {examInfo ? `${examInfo.title} (${examInfo.subject})` : 'Select an Exam'}
              </p>
            </div>
          </div>

          <div className="w-full sm:w-72">
            <select
              value={selectedExamId}
              onChange={(e) => handleExamChange(e.target.value)}
              disabled={loadingExams || exams.length === 0}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs font-semibold text-white focus:outline-none focus:border-indigo-500 transition disabled:opacity-50"
            >
              {exams.length === 0 ? (
                <option value="">No Exams Available</option>
              ) : (
                exams.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.title} ({ex.subject}) • {ex.status}
                  </option>
                ))
              )}
            </select>
          </div>
        </div>

        {/* Global Error Banner */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading Indicator */}
        {loadingAnalytics || loadingExams ? (
          <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span>Calculating real-time exam performance metrics from database...</span>
          </div>
        ) : !analyticsData || exams.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <BarChart3 className="w-12 h-12 text-slate-600" />
            <p className="font-semibold text-slate-300 text-sm">No Examination Data Selected</p>
            <p className="text-slate-500 max-w-md">
              Create and publish an examination to start recording student evaluation sessions and generating analytics.
            </p>
          </div>
        ) : (
          <>
            {/* 1. TOP SUMMARY METRIC CARDS */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                  Total Sessions
                </span>
                <span className="text-2xl font-bold text-white font-mono block">
                  {summary?.total_sessions || 0}
                </span>
                <span className="text-[10px] text-slate-500">Submitted / Expired</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                  Evaluated
                </span>
                <span className="text-2xl font-bold text-indigo-400 font-mono block">
                  {summary?.evaluated_sessions || 0}
                </span>
                <span className="text-[10px] text-indigo-300/70">Processed by AI/Rule</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono font-bold text-amber-400 block">
                  Pending Review
                </span>
                <span className="text-2xl font-bold text-amber-400 font-mono block">
                  {summary?.pending_reviews || 0}
                </span>
                <span className="text-[10px] text-amber-300/70">Awaiting Examiner</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono font-bold text-emerald-400 block">
                  Finalized
                </span>
                <span className="text-2xl font-bold text-emerald-400 font-mono block">
                  {summary?.finalized_evaluations || 0}
                </span>
                <span className="text-[10px] text-emerald-300/70">Locked & Verified</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                  Average Score
                </span>
                <span className="text-2xl font-bold text-purple-400 font-mono block">
                  {summary?.average_score} <span className="text-xs text-slate-400 font-normal">/ {examInfo?.total_marks ?? 0}</span>
                </span>
                <span className="text-[10px] text-purple-300/70">Mean Total Score</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                  Average %
                </span>
                <span className="text-2xl font-bold text-cyan-400 font-mono block">
                  {summary?.average_percentage}%
                </span>
                <span className="text-[10px] text-cyan-300/70">Overall Mean</span>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                  Pass Rate
                </span>
                <span className="text-2xl font-bold text-emerald-400 font-mono block">
                  {summary?.pass_rate}%
                </span>
                <span className="text-[10px] text-emerald-300/70">
                  {summary?.pass_count} Pass / {summary?.fail_count} Fail
                </span>
              </div>
            </div>

            {/* 2. CHARTS SECTION: SCORE DISTRIBUTION & PASS/FAIL/PENDING BREAKDOWN */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Score Distribution Bar Chart */}
              <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-indigo-400">
                    <BarChart3 className="w-5 h-5" />
                    <h3 className="font-bold text-sm text-white">Score Distribution (Percentage Ranges)</h3>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400">
                    Median: <strong className="text-indigo-300">{scorePerf?.median_percentage}%</strong>
                  </span>
                </div>

                <div className="space-y-3 pt-2">
                  {[
                    { label: '81% – 100%', count: scoreDist?.bucket_81_100 || 0, color: 'bg-emerald-500' },
                    { label: '61% – 80%', count: scoreDist?.bucket_61_80 || 0, color: 'bg-indigo-500' },
                    { label: '41% – 60%', count: scoreDist?.bucket_41_60 || 0, color: 'bg-purple-500' },
                    { label: '21% – 40%', count: scoreDist?.bucket_21_40 || 0, color: 'bg-amber-500' },
                    { label: '0% – 20%', count: scoreDist?.bucket_0_20 || 0, color: 'bg-rose-500' },
                  ].map((b) => {
                    const widthPct = Math.round((b.count / maxBucketCount) * 100);
                    return (
                      <div key={b.label} className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-slate-400">{b.label}</span>
                          <span className="font-bold text-white">
                            {b.count} {b.count === 1 ? 'student' : 'students'}
                          </span>
                        </div>
                        <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className={`h-full ${b.color} transition-all duration-500 rounded-full`}
                            style={{ width: `${widthPct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                <div className="grid grid-cols-4 gap-2 pt-3 border-t border-slate-800 text-center text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Average</span>
                    <span className="font-bold text-white">{scorePerf?.average_percentage}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Highest</span>
                    <span className="font-bold text-emerald-400">{scorePerf?.highest_percentage}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Lowest</span>
                    <span className="font-bold text-rose-400">{scorePerf?.lowest_percentage}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Median</span>
                    <span className="font-bold text-indigo-400">{scorePerf?.median_percentage}%</span>
                  </div>
                </div>
              </div>

              {/* Pass / Fail / Pending Distribution Visual Card */}
              <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl flex flex-col justify-between">
                <div className="flex items-center gap-2 text-indigo-400">
                  <PieChart className="w-5 h-5" />
                  <h3 className="font-bold text-sm text-white">Outcome Breakdown</h3>
                </div>

                <div className="space-y-4 my-auto py-2">
                  <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-900/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20 text-emerald-400">
                        <CheckCircle2 className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-emerald-300 block">Passed</span>
                        <span className="text-[10px] text-emerald-400/70">Score ≥ Passing Marks</span>
                      </div>
                    </div>
                    <span className="text-xl font-bold font-mono text-emerald-400">
                      {passFailDist?.passed || 0}
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-900/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-rose-500/10 rounded-lg border border-rose-500/20 text-rose-400">
                        <XCircle className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-rose-300 block">Failed</span>
                        <span className="text-[10px] text-rose-400/70">Score &lt; Passing Marks</span>
                      </div>
                    </div>
                    <span className="text-xl font-bold font-mono text-rose-400">
                      {passFailDist?.failed || 0}
                    </span>
                  </div>

                  <div className="p-3.5 rounded-xl bg-amber-950/30 border border-amber-900/50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20 text-amber-400">
                        <Clock className="w-4 h-4" />
                      </div>
                      <div>
                        <span className="text-xs font-bold text-amber-300 block">Pending Review</span>
                        <span className="text-[10px] text-amber-400/70">Subjective Questions Awaiting Examiner</span>
                      </div>
                    </div>
                    <span className="text-xl font-bold font-mono text-amber-400">
                      {passFailDist?.pending_review || 0}
                    </span>
                  </div>
                </div>

                {/* Finalized Statistics Banner */}
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Finalized Evaluations:</span>
                    <strong className="text-white">{finalizedPerf?.finalized_sessions || 0}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Finalized Avg Score:</span>
                    <strong className="text-indigo-400">{finalizedPerf?.average_finalized_score}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Finalized Pass Rate:</span>
                    <strong className="text-emerald-400">{finalizedPerf?.finalized_pass_rate}%</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* 3. PENDING REVIEWS SECTION */}
            {analyticsData.pending_reviews.length > 0 && (
              <div className="p-6 rounded-2xl bg-amber-950/20 border border-amber-900/40 space-y-4 shadow-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-amber-400">
                    <Clock className="w-5 h-5" />
                    <h3 className="font-bold text-base text-white">
                      Pending Examiner Reviews ({analyticsData.pending_reviews.length})
                    </h3>
                  </div>
                  <span className="text-xs text-amber-400/80 font-mono">
                    Subjective answers requiring manual grading/finalization
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {analyticsData.pending_reviews.map((item: PendingReviewItem) => (
                    <div
                      key={item.session_id}
                      className="p-4 rounded-xl bg-slate-900/90 border border-amber-900/30 flex flex-col justify-between space-y-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white text-xs">{item.student_name}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            {item.pending_question_count} pending Qs
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 font-mono">{item.student_email}</p>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs font-mono">
                        <div>
                          <span className="text-slate-500 block text-[10px]">Current Score</span>
                          <span className="font-bold text-indigo-400">
                            {item.current_score} / {item.maximum_marks}
                          </span>
                        </div>
                        <Link
                          href="/results"
                          className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold rounded-lg text-xs transition inline-flex items-center gap-1"
                        >
                          Review <ArrowUpRight className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 4. QUESTION-WISE PERFORMANCE ANALYTICS */}
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-indigo-400">
                  <HelpCircle className="w-5 h-5" />
                  <h3 className="font-bold text-base text-white">Question Performance & Accuracy</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {analyticsData.question_performance.length} Total Questions
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 font-mono">
                      <th className="py-3 px-4">Q#</th>
                      <th className="py-3 px-4">Question Details</th>
                      <th className="py-3 px-4">Type</th>
                      <th className="py-3 px-4">Difficulty & Topic</th>
                      <th className="py-3 px-4 text-center">Attempted / Unanswered</th>
                      <th className="py-3 px-4 text-center">Correct / Accuracy</th>
                      <th className="py-3 px-4 text-right">Avg Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-xs">
                    {analyticsData.question_performance.map((qp: QuestionPerformanceItem) => {
                      const isObjective = ['MCQ', 'MULTI_SELECT'].includes(qp.question_type);
                      return (
                        <tr key={qp.question_id} className="hover:bg-slate-800/30 transition text-slate-300">
                          <td className="py-3.5 px-4 font-bold font-mono text-white">
                            Q{qp.question_order}
                          </td>
                          <td className="py-3.5 px-4 max-w-xs">
                            <p className="font-medium text-white line-clamp-2">{qp.question_text}</p>
                            <span className="text-[10px] text-slate-500 font-mono">Max Marks: {qp.marks}</span>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-indigo-300 border border-slate-700 font-semibold">
                              {qp.question_type}
                            </span>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="flex flex-col gap-1">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold inline-block w-max ${
                                  qp.difficulty === 'EASY'
                                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                                    : qp.difficulty === 'HARD'
                                    ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                                    : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                                }`}
                              >
                                {qp.difficulty}
                              </span>
                              {qp.topic && (
                                <span className="text-[10px] text-slate-400 font-mono">
                                  Topic: {qp.topic}
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono">
                            <div>
                              <strong className="text-white">{qp.attempted_count}</strong> / {qp.unanswered_count}
                            </div>
                            <span className="text-[10px] text-slate-500">Attempted / Empty</span>
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono">
                            {isObjective ? (
                              <div>
                                <span className="text-emerald-400 font-bold">{qp.correct_count} Correct</span>
                                <div className="w-24 mx-auto bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800 mt-1">
                                  <div
                                    className="h-full bg-emerald-500 rounded-full"
                                    style={{ width: `${qp.accuracy_percentage || 0}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-slate-400">{qp.accuracy_percentage}% Accuracy</span>
                              </div>
                            ) : (
                              <div>
                                <span className="text-purple-300 font-medium">
                                  {qp.evaluated_count} Evaluated
                                </span>
                                {qp.pending_review_count !== undefined && qp.pending_review_count !== null && qp.pending_review_count > 0 && (
                                  <span className="block text-[10px] text-amber-400 font-semibold">
                                    {qp.pending_review_count} Pending Review
                                  </span>
                                )}
                              </div>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono font-bold">
                            <span className="text-indigo-400">{qp.average_score}</span> / {qp.marks}
                            <span className="block text-[10px] text-slate-400">{qp.average_percentage}%</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 5. DIFFICULTY & TOPIC PERFORMANCE BREAKDOWN */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Difficulty Breakdown */}
              <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl">
                <div className="flex items-center gap-2 text-indigo-400">
                  <Layers className="w-5 h-5" />
                  <h3 className="font-bold text-sm text-white">Performance by Difficulty Level</h3>
                </div>

                <div className="space-y-3">
                  {analyticsData.difficulty_performance.map((dp) => (
                    <div key={dp.difficulty} className="space-y-1.5 p-3 rounded-lg bg-slate-950 border border-slate-800">
                      <div className="flex justify-between items-center text-xs font-mono">
                        <span
                          className={`font-bold ${
                            dp.difficulty === 'EASY'
                              ? 'text-emerald-400'
                              : dp.difficulty === 'HARD'
                              ? 'text-rose-400'
                              : 'text-amber-400'
                          }`}
                        >
                          {dp.difficulty} ({dp.question_count} Qs)
                        </span>
                        <strong className="text-white">{dp.average_percentage}% Avg</strong>
                      </div>
                      <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
                        <div
                          className={`h-full rounded-full ${
                            dp.difficulty === 'EASY'
                              ? 'bg-emerald-500'
                              : dp.difficulty === 'HARD'
                              ? 'bg-rose-500'
                              : 'bg-amber-500'
                          }`}
                          style={{ width: `${dp.average_percentage}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Topic Breakdown */}
              <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl">
                <div className="flex items-center gap-2 text-indigo-400">
                  <BookOpen className="w-5 h-5" />
                  <h3 className="font-bold text-sm text-white">Performance by Topic</h3>
                </div>

                {analyticsData.topic_performance.length === 0 ? (
                  <p className="text-xs text-slate-500 text-center py-6">
                    No topic tags assigned to questions in this exam.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {analyticsData.topic_performance.map((tp) => (
                      <div key={tp.topic} className="space-y-1.5 p-3 rounded-lg bg-slate-950 border border-slate-800">
                        <div className="flex justify-between items-center text-xs font-mono">
                          <span className="font-bold text-slate-300">
                            {tp.topic} ({tp.question_count} Qs)
                          </span>
                          <strong className="text-indigo-400">{tp.average_percentage}% Avg</strong>
                        </div>
                        <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
                          <div
                            className="h-full bg-indigo-500 rounded-full"
                            style={{ width: `${tp.average_percentage}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 6. STUDENT PERFORMANCE TABLE WITH SEARCH & FILTERS */}
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-indigo-400">
                  <Users className="w-5 h-5" />
                  <h3 className="font-bold text-base text-white">Student Exam Performance Table</h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {analyticsData.student_performance.total} Total Evaluated Students
                </span>
              </div>

              {/* Toolbar */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3 bg-slate-950 rounded-xl border border-slate-800">
                <form onSubmit={handleSearchSubmit} className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search student name or email..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </form>

                <select
                  value={passFailFilter}
                  onChange={(e) => handleFilterApply(e.target.value, statusFilter)}
                  className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Results (Pass & Fail)</option>
                  <option value="PASSED">Passed Only</option>
                  <option value="FAILED">Failed Only</option>
                </select>

                <select
                  value={statusFilter}
                  onChange={(e) => handleFilterApply(passFailFilter, e.target.value)}
                  className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Evaluation Statuses</option>
                  <option value="FINALIZED">Finalized</option>
                  <option value="MANUAL_REVIEW">Manual Review</option>
                  <option value="AI_EVALUATED">AI Evaluated</option>
                  <option value="PENDING_REVIEW">Pending Review</option>
                </select>
              </div>

              {/* Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 font-mono">
                      <th className="py-3 px-4">Student</th>
                      <th className="py-3 px-4">Email</th>
                      <th className="py-3 px-4 text-center">Score</th>
                      <th className="py-3 px-4 text-center">Percentage</th>
                      <th className="py-3 px-4 text-center">Result</th>
                      <th className="py-3 px-4 text-center">Evaluation Status</th>
                      <th className="py-3 px-4 text-right">Submitted At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-xs">
                    {analyticsData.student_performance.items.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-slate-500">
                          No student performance records found matching filter.
                        </td>
                      </tr>
                    ) : (
                      analyticsData.student_performance.items.map((stRes: StudentResultResponse) => (
                        <tr key={stRes.id} className="hover:bg-slate-800/30 transition text-slate-300">
                          <td className="py-3.5 px-4 font-bold text-white">{stRes.student_name}</td>
                          <td className="py-3.5 px-4 font-mono text-slate-400">{stRes.student_email}</td>
                          <td className="py-3.5 px-4 text-center font-mono font-bold">
                            <span className="text-indigo-400">{stRes.total_score}</span> / {stRes.maximum_marks}
                          </td>
                          <td className="py-3.5 px-4 text-center font-mono font-bold">
                            <span className={stRes.percentage >= 50 ? 'text-emerald-400' : 'text-rose-400'}>
                              {stRes.percentage}%
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            {stRes.pass_fail_status === 'PASSED' ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                <CheckCircle2 className="w-3 h-3" /> PASSED
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                                <XCircle className="w-3 h-3" /> FAILED
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            {stRes.status === 'FINALIZED' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                                Finalized
                              </span>
                            ) : stRes.status === 'MANUAL_REVIEW' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                                Manual Review
                              </span>
                            ) : stRes.status === 'AI_EVALUATED' ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/30">
                                AI Evaluated
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                Pending Review
                              </span>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-right font-mono text-slate-400 text-[11px]">
                            {stRes.submitted_at ? new Date(stRes.submitted_at).toLocaleString() : 'N/A'}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              {analyticsData.student_performance.total_pages > 1 && (
                <div className="flex items-center justify-between pt-2 text-xs text-slate-400">
                  <span>
                    Page {page} of {analyticsData.student_performance.total_pages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      disabled={page <= 1}
                      onClick={() => {
                        const newP = Math.max(1, page - 1);
                        setPage(newP);
                        fetchAnalytics(selectedExamId, newP, search, passFailFilter, statusFilter);
                      }}
                      className="px-3 py-1.5 bg-slate-950 border border-slate-800 hover:bg-slate-800 rounded-lg disabled:opacity-50 transition font-mono"
                    >
                      Previous
                    </button>
                    <button
                      disabled={page >= analyticsData.student_performance.total_pages}
                      onClick={() => {
                        const newP = Math.min(analyticsData.student_performance.total_pages, page + 1);
                        setPage(newP);
                        fetchAnalytics(selectedExamId, newP, search, passFailFilter, statusFilter);
                      }}
                      className="px-3 py-1.5 bg-slate-950 border border-slate-800 hover:bg-slate-800 rounded-lg disabled:opacity-50 transition font-mono"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
