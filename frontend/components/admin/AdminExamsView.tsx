'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import {
  BookOpen,
  Search,
  Building2,
  Calendar,
  Clock,
  Eye,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Users,
  Award,
  ShieldCheck,
  Layers,
  FileText,
  UserCheck,
  HelpCircle,
} from 'lucide-react';
import {
  adminExamsAPI,
  academicAPI,
  AdminExamListItem,
  AdminExamSummaryMetrics,
  AdminExamDetailResponse,
  College,
  ExamStatus,
  ExamTargetType,
} from '@/lib/api';

export default function AdminExamsView() {
  const [exams, setExams] = useState<AdminExamListItem[]>([]);
  const [summary, setSummary] = useState<AdminExamSummaryMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalExams, setTotalExams] = useState(0);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedTargetType, setSelectedTargetType] = useState<string>('');
  const [selectedCollegeId, setSelectedCollegeId] = useState('');

  // Colleges for dropdown
  const [colleges, setColleges] = useState<College[]>([]);

  // Detail Modal State
  const [selectedExamId, setSelectedExamId] = useState<string | null>(null);
  const [examDetail, setExamDetail] = useState<AdminExamDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // 1. Initial Load of Colleges
  useEffect(() => {
    async function loadColleges() {
      try {
        const list = await academicAPI.getPublicColleges();
        setColleges(list);
      } catch (err) {
        console.error('Failed to load colleges for filter:', err);
      }
    }
    loadColleges();
  }, []);

  // 2. Fetch Exams List
  const fetchExams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await adminExamsAPI.list({
        search: search.trim() || undefined,
        status: selectedStatus || undefined,
        target_type: selectedTargetType || undefined,
        college_id: selectedCollegeId || undefined,
        page,
        page_size: pageSize,
      });

      setExams(res.items);
      setTotalExams(res.total);
      setTotalPages(res.total_pages);
      setSummary(res.summary);
    } catch (err: any) {
      console.error('Failed to load exams:', err);
      setError(err.message || 'Failed to load examinations. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [search, selectedStatus, selectedTargetType, selectedCollegeId, page, pageSize]);

  useEffect(() => {
    fetchExams();
  }, [fetchExams]);

  // Handle Search Input with debounce/trigger
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchExams();
  };

  const handleResetFilters = () => {
    setSearch('');
    setSelectedStatus('');
    setSelectedTargetType('');
    setSelectedCollegeId('');
    setPage(1);
  };

  // 3. Open Detail Modal
  const handleOpenDetail = async (examId: string) => {
    setSelectedExamId(examId);
    setDetailLoading(true);
    setDetailError(null);
    setExamDetail(null);
    try {
      const detail = await adminExamsAPI.getDetail(examId);
      setExamDetail(detail);
    } catch (err: any) {
      console.error('Failed to load exam detail:', err);
      setDetailError(err.message || 'Failed to fetch exam details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedExamId(null);
    setExamDetail(null);
    setDetailError(null);
  };

  const getStatusBadge = (status: ExamStatus | string) => {
    switch (status) {
      case 'PUBLISHED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Published
          </span>
        );
      case 'ACTIVE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            Active
          </span>
        );
      case 'SCHEDULED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Clock className="w-3 h-3 text-indigo-400" />
            Scheduled
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <CheckCircle2 className="w-3 h-3 text-purple-400" />
            Completed
          </span>
        );
      case 'ARCHIVED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Archived
          </span>
        );
      case 'DRAFT':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
            Draft
          </span>
        );
    }
  };

  const getTargetTypeBadge = (targetType?: ExamTargetType | string | null) => {
    switch (targetType) {
      case 'COLLEGE':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Building2 className="w-3 h-3" /> College
          </span>
        );
      case 'DEPARTMENT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Layers className="w-3 h-3" /> Dept
          </span>
        );
      case 'YEAR':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Calendar className="w-3 h-3" /> Year
          </span>
        );
      case 'SECTION':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Users className="w-3 h-3" /> Section
          </span>
        );
      case 'SPECIFIC_STUDENTS':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-pink-500/10 text-pink-400 border border-pink-500/20">
            <UserCheck className="w-3 h-3" /> Specific
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
            General
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Institutional Exam Oversight"
        subtitle="Centralized platform monitoring of all examinations, academic scopes, and session progress."
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Exams */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 shadow-sm backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Total Exams
            </span>
            <div className="p-2.5 bg-blue-500/10 rounded-xl border border-blue-500/20 text-blue-400">
              <BookOpen className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">
            {summary ? summary.total_exams : <span className="animate-pulse text-slate-600">--</span>}
          </p>
          <p className="text-xs text-slate-500 mt-1">Platform-wide examinations</p>
        </div>

        {/* Published & Active */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 shadow-sm backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Published & Active
            </span>
            <div className="p-2.5 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">
            {summary ? summary.published_active_exams : <span className="animate-pulse text-slate-600">--</span>}
          </p>
          <p className="text-xs text-slate-500 mt-1">Ready or currently running</p>
        </div>

        {/* Completed Exams */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 shadow-sm backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Completed Exams
            </span>
            <div className="p-2.5 bg-purple-500/10 rounded-xl border border-purple-500/20 text-purple-400">
              <Award className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-purple-400 mt-3">
            {summary ? summary.completed_exams : <span className="animate-pulse text-slate-600">--</span>}
          </p>
          <p className="text-xs text-slate-500 mt-1">Concluded test sessions</p>
        </div>

        {/* Draft Exams */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 shadow-sm backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Draft Exams
            </span>
            <div className="p-2.5 bg-amber-500/10 rounded-xl border border-amber-500/20 text-amber-400">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-amber-400 mt-3">
            {summary ? summary.draft_exams : <span className="animate-pulse text-slate-600">--</span>}
          </p>
          <p className="text-xs text-slate-500 mt-1">In preparation by examiners</p>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search title, subject, examiner..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </form>

          {/* Status Filter */}
          <div>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition"
            >
              <option value="">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="PUBLISHED">Published</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="ACTIVE">Active</option>
              <option value="COMPLETED">Completed</option>
              <option value="ARCHIVED">Archived</option>
            </select>
          </div>

          {/* Target Type Filter */}
          <div>
            <select
              value={selectedTargetType}
              onChange={(e) => {
                setSelectedTargetType(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition"
            >
              <option value="">All Audiences</option>
              <option value="COLLEGE">College-wide</option>
              <option value="DEPARTMENT">Department-level</option>
              <option value="YEAR">Year of Study</option>
              <option value="SECTION">Specific Section</option>
              <option value="SPECIFIC_STUDENTS">Selected Students</option>
            </select>
          </div>

          {/* College Filter */}
          <div>
            <select
              value={selectedCollegeId}
              onChange={(e) => {
                setSelectedCollegeId(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-indigo-500 transition"
            >
              <option value="">All Colleges</option>
              {colleges.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Action Row: Reset & Results Count */}
        <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/60">
          <span>
            Found <strong className="text-white">{totalExams}</strong> examinations
          </span>
          {(search || selectedStatus || selectedTargetType || selectedCollegeId) && (
            <button
              onClick={handleResetFilters}
              className="flex items-center gap-1.5 text-xs font-medium text-indigo-400 hover:text-indigo-300 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-between text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchExams}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 rounded-lg text-xs font-semibold transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Table Section */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur-sm shadow-sm">
        {loading ? (
          <div className="py-20 flex flex-col items-center justify-center space-y-3">
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
            <p className="text-sm text-slate-400 font-medium">Loading institutional examinations...</p>
          </div>
        ) : exams.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-800/60 flex items-center justify-center mx-auto text-slate-500">
              <BookOpen className="w-6 h-6" />
            </div>
            <p className="text-sm font-semibold text-slate-300">No examinations found</p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              There are no exams matching your search and filter criteria.
            </p>
            {(search || selectedStatus || selectedTargetType || selectedCollegeId) && (
              <button
                onClick={handleResetFilters}
                className="mt-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-medium transition inline-flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Clear Filters
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 font-semibold uppercase tracking-wider">
                  <th className="py-3.5 px-4">Examination</th>
                  <th className="py-3.5 px-4">Examiner & Institution</th>
                  <th className="py-3.5 px-4">Audience Scope</th>
                  <th className="py-3.5 px-4">Questions & Marks</th>
                  <th className="py-3.5 px-4">Attempts / Activity</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {exams.map((exam) => (
                  <tr key={exam.id} className="hover:bg-slate-800/30 transition-colors">
                    {/* Examination Title & Subject */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5">
                        <p className="font-semibold text-white text-sm line-clamp-1">{exam.title}</p>
                        <div className="flex items-center gap-2 text-slate-400">
                          <span className="text-[11px] font-medium text-indigo-400">{exam.subject}</span>
                          <span>•</span>
                          <span className="text-[11px] flex items-center gap-1">
                            <Clock className="w-3 h-3 text-slate-500" />
                            {exam.duration_minutes}m
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Examiner & Institution */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <p className="font-medium text-slate-200">{exam.examiner_name}</p>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {exam.examiner_college_code || exam.examiner_college_name ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700/60">
                              <Building2 className="w-2.5 h-2.5 text-slate-400" />
                              {exam.examiner_college_code || exam.examiner_college_name}
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-500 italic">No college assigned</span>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Audience Scope */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5">
                          {getTargetTypeBadge(exam.target_type)}
                          <span className="text-[11px] text-slate-400 font-medium">
                            {exam.eligible_students_count} eligible
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 line-clamp-1">
                          {exam.target_description}
                        </p>
                      </div>
                    </td>

                    {/* Questions & Marks */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5 text-xs">
                        <p className="font-medium text-slate-200">
                          {exam.question_count} <span className="text-slate-500 text-[11px]">questions</span>
                        </p>
                        <p className="text-[11px] text-slate-400">
                          Total: <strong className="text-slate-300">{exam.total_marks}</strong> (Pass: {exam.passing_marks})
                        </p>
                      </div>
                    </td>

                    {/* Attempts / Activity */}
                    <td className="py-3.5 px-4">
                      <div className="space-y-0.5 text-xs">
                        <p className="font-medium text-slate-200">
                          {exam.sessions_count} <span className="text-slate-500 text-[11px]">attempts</span>
                        </p>
                        <p className="text-[11px] text-slate-400">
                          Completed: <strong className="text-emerald-400">{exam.completed_sessions_count}</strong>
                        </p>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">
                      {getStatusBadge(exam.status)}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleOpenDetail(exam.id)}
                        className="px-3 py-1.5 rounded-xl bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border border-indigo-500/20 font-medium transition inline-flex items-center gap-1.5 text-xs"
                      >
                        <Eye className="w-3.5 h-3.5" /> Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="py-3.5 px-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 bg-slate-950/40">
            <span>
              Showing Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong>
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Prev
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed transition flex items-center gap-1"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* DETAIL MODAL */}
      {selectedExamId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-3xl max-h-[90vh] flex flex-col bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="py-4 px-6 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-2xl">
                  <BookOpen className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-base text-white">Examination Inspection</h3>
                  <p className="text-xs text-slate-400">Institutional review and activity oversight</p>
                </div>
              </div>
              <button
                onClick={handleCloseDetail}
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800/60 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 text-xs text-slate-300">
              {detailLoading ? (
                <div className="py-16 flex flex-col items-center justify-center space-y-3">
                  <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
                  <p className="text-xs text-slate-400 font-medium">Fetching complete examination data...</p>
                </div>
              ) : detailError ? (
                <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 space-y-2">
                  <p className="font-semibold text-sm flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" /> Unable to load exam details
                  </p>
                  <p className="text-xs">{detailError}</p>
                </div>
              ) : examDetail ? (
                <>
                  {/* Basic Exam Banner */}
                  <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h4 className="text-base font-bold text-white">{examDetail.title}</h4>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs font-semibold text-indigo-400">{examDetail.subject}</span>
                          <span className="text-slate-600">•</span>
                          <span className="text-xs text-slate-400">
                            Created {new Date(examDetail.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <div>{getStatusBadge(examDetail.status)}</div>
                    </div>

                    {examDetail.description && (
                      <p className="text-xs text-slate-400 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
                        {examDetail.description}
                      </p>
                    )}
                  </div>

                  {/* 2-Column: Examiner Ownership & Target Audience */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Examiner Ownership */}
                    <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 flex items-center gap-2">
                          <UserCheck className="w-4 h-4 text-emerald-400" /> Examiner Ownership
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">Institutional FK</span>
                      </div>
                      <div className="space-y-1.5">
                        <p className="text-sm font-bold text-white">{examDetail.examiner_name}</p>
                        <p className="text-xs text-slate-400">{examDetail.examiner_email}</p>
                        <div className="pt-2">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">
                            Assigned College
                          </span>
                          <p className="text-xs text-slate-300 font-medium mt-0.5">
                            {examDetail.examiner_college_name ? (
                              <span>
                                {examDetail.examiner_college_name}{' '}
                                {examDetail.examiner_college_code && (
                                  <span className="text-slate-400">({examDetail.examiner_college_code})</span>
                                )}
                              </span>
                            ) : (
                              <span className="text-slate-500 italic">No college assigned</span>
                            )}
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Target Audience */}
                    <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 flex items-center gap-2">
                          <Building2 className="w-4 h-4 text-cyan-400" /> Target Audience
                        </span>
                        <div>{getTargetTypeBadge(examDetail.target_type)}</div>
                      </div>
                      <div className="space-y-2">
                        <p className="text-xs text-slate-300 font-medium">
                          {examDetail.target_description}
                        </p>
                        <div className="grid grid-cols-2 gap-2 pt-1 text-[11px]">
                          <div>
                            <span className="text-slate-500">Department:</span>{' '}
                            <span className="text-slate-300 font-medium">
                              {examDetail.target_department_name || 'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-500">Year:</span>{' '}
                            <span className="text-slate-300 font-medium">
                              {examDetail.target_year_of_study ? `Year ${examDetail.target_year_of_study}` : 'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-500">Section:</span>{' '}
                            <span className="text-slate-300 font-medium">
                              {examDetail.target_section_name || 'N/A'}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-500">Eligible Pool:</span>{' '}
                            <strong className="text-emerald-400">
                              {examDetail.eligible_students_count} students
                            </strong>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Configuration & Proctoring Parameters */}
                  <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800 space-y-3">
                    <span className="font-semibold text-slate-200 flex items-center gap-2 border-b border-slate-800/80 pb-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-400" /> Examination & Security Settings
                    </span>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                      <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase block font-semibold">Duration</span>
                        <p className="text-sm font-bold text-white mt-0.5">{examDetail.duration_minutes} mins</p>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase block font-semibold">Total Marks</span>
                        <p className="text-sm font-bold text-white mt-0.5">{examDetail.total_marks}</p>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase block font-semibold">Pass Marks</span>
                        <p className="text-sm font-bold text-emerald-400 mt-0.5">{examDetail.passing_marks}</p>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase block font-semibold">Max Tab Switch</span>
                        <p className="text-sm font-bold text-amber-400 mt-0.5">{examDetail.max_tab_switches}</p>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2 pt-2 text-[11px]">
                      <span
                        className={`px-2.5 py-1 rounded-lg border font-medium ${
                          examDetail.proctoring_enabled
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {examDetail.proctoring_enabled ? '✓ AI Proctoring Enabled' : 'Proctoring Disabled'}
                      </span>
                      <span
                        className={`px-2.5 py-1 rounded-lg border font-medium ${
                          examDetail.randomize_questions
                            ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {examDetail.randomize_questions ? '✓ Randomized Questions' : 'Sequential Questions'}
                      </span>
                      <span
                        className={`px-2.5 py-1 rounded-lg border font-medium ${
                          examDetail.randomize_options
                            ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {examDetail.randomize_options ? '✓ Randomized Options' : 'Fixed Options'}
                      </span>
                      <span
                        className={`px-2.5 py-1 rounded-lg border font-medium ${
                          examDetail.negative_marking_enabled
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {examDetail.negative_marking_enabled ? '✓ Negative Marking' : 'No Negative Marking'}
                      </span>
                    </div>
                  </div>

                  {/* Question Composition & Activity Breakdown */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Question Breakdown */}
                    <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 flex items-center gap-2">
                          <HelpCircle className="w-4 h-4 text-amber-400" /> Question Breakdown
                        </span>
                        <strong className="text-white text-xs">{examDetail.question_count} Total</strong>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between">
                          <span className="text-slate-400">MCQ:</span>
                          <span className="font-bold text-white">{examDetail.mcq_count}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between">
                          <span className="text-slate-400">Multi-Select:</span>
                          <span className="font-bold text-white">{examDetail.multi_select_count}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between">
                          <span className="text-slate-400">Short Answer:</span>
                          <span className="font-bold text-white">{examDetail.short_answer_count}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between">
                          <span className="text-slate-400">Long Answer:</span>
                          <span className="font-bold text-white">{examDetail.long_answer_count}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between col-span-2">
                          <span className="text-slate-400">Handwritten / OCR:</span>
                          <span className="font-bold text-white">{examDetail.handwritten_count}</span>
                        </div>
                      </div>
                    </div>

                    {/* Session Activity */}
                    <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <span className="font-semibold text-slate-200 flex items-center gap-2">
                          <Award className="w-4 h-4 text-purple-400" /> Student Sessions
                        </span>
                        <strong className="text-white text-xs">{examDetail.total_sessions_count} Total</strong>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between">
                          <span className="text-slate-400">Completed:</span>
                          <span className="font-bold text-emerald-400">{examDetail.completed_sessions_count}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between">
                          <span className="text-slate-400">In Progress:</span>
                          <span className="font-bold text-blue-400">{examDetail.in_progress_sessions_count}</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 flex justify-between col-span-2">
                          <span className="text-slate-400">Other / Expired / Terminated:</span>
                          <span className="font-bold text-slate-300">{examDetail.other_sessions_count}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="py-3 px-6 border-t border-slate-800 flex items-center justify-end bg-slate-950/60">
              <button
                onClick={handleCloseDetail}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
