'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import PageHeader from '@/components/layout/PageHeader';
import {
  UserCheck,
  UserX,
  Users,
  Search,
  Building2,
  BookOpen,
  Calendar,
  Clock,
  Eye,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  RotateCcw,
  Plus,
} from 'lucide-react';
import {
  adminExaminersAPI,
  adminAPI,
  academicAPI,
  AdminExaminerListItem,
  AdminExaminerSummaryMetrics,
  AdminExaminerDetailResponse,
  College,
} from '@/lib/api';

export default function AdminExaminersView() {
  const [examiners, setExaminers] = useState<AdminExaminerListItem[]>([]);
  const [summary, setSummary] = useState<AdminExaminerSummaryMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Pagination & Filtering
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalExaminers, setTotalExaminers] = useState(0);

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [selectedCollegeId, setSelectedCollegeId] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  // Colleges List for Filter
  const [colleges, setColleges] = useState<College[]>([]);

  // Detail Modal State
  const [selectedExaminerId, setSelectedExaminerId] = useState<string | null>(null);
  const [examinerDetail, setExaminerDetail] = useState<AdminExaminerDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Status Toggle Modal State
  const [statusModalExaminer, setStatusModalExaminer] = useState<AdminExaminerListItem | null>(null);
  const [statusUpdating, setStatusUpdating] = useState(false);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

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

  // 2. Fetch Examiners List
  const fetchExaminers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const is_active_param =
        selectedStatus === '' ? undefined : selectedStatus === 'true';

      const res = await adminExaminersAPI.list({
        search: search.trim() || undefined,
        college_id: selectedCollegeId || undefined,
        is_active: is_active_param,
        page,
        page_size: pageSize,
      });

      setExaminers(res.items);
      setTotalPages(res.total_pages || 1);
      setTotalExaminers(res.total || 0);
      setSummary(res.summary);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch examiners.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, selectedCollegeId, selectedStatus]);

  useEffect(() => {
    fetchExaminers();
  }, [fetchExaminers]);

  // Handle Search Input Change
  const handleSearchChange = (val: string) => {
    setSearch(val);
    setPage(1);
  };

  // Reset All Filters
  const handleResetFilters = () => {
    setSearch('');
    setSelectedCollegeId('');
    setSelectedStatus('');
    setPage(1);
  };

  // Open Detail Modal
  const handleOpenDetail = async (examinerId: string) => {
    setSelectedExaminerId(examinerId);
    setExaminerDetail(null);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const detail = await adminExaminersAPI.getDetail(examinerId);
      setExaminerDetail(detail);
    } catch (err: unknown) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load examiner details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedExaminerId(null);
    setExaminerDetail(null);
    setDetailError(null);
  };

  // Toggle Account Status
  const handleStatusToggle = async () => {
    if (!statusModalExaminer) return;
    setStatusUpdating(true);
    try {
      const updatedStatus = !statusModalExaminer.is_active;
      await adminAPI.updateUserStatus(statusModalExaminer.id, updatedStatus);
      showToast(
        `Examiner account for ${statusModalExaminer.first_name} ${statusModalExaminer.last_name} successfully ${
          updatedStatus ? 'activated' : 'deactivated'
        }.`
      );
      setStatusModalExaminer(null);
      fetchExaminers();
    } catch (err: unknown) {
      showToast(
        err instanceof Error ? err.message : 'Failed to update examiner account status.',
        'error'
      );
    } finally {
      setStatusUpdating(false);
    }
  };

  const hasActiveFilters = search || selectedCollegeId || selectedStatus;

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed top-4 right-4 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border text-xs font-semibold shadow-2xl transition animate-in fade-in slide-in-from-top-2 ${
            toast.type === 'success'
              ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-300'
              : 'bg-red-950/90 border-red-500/50 text-red-300'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-400" />
          )}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Page Header */}
      <PageHeader
        title="Examiners"
        subtitle="Manage examiner accounts, institutional assignments, and examination activity."
        actions={
          <Link
            href="/users"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Provision Examiner
          </Link>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Examiners */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Total Examiners
            </p>
            <div className="p-2 bg-indigo-600/20 rounded-xl border border-indigo-500/30 text-indigo-400">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">
            {summary ? summary.total_examiners : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Platform provisioned examiners</p>
        </div>

        {/* Active Examiners */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Examiners
            </p>
            <div className="p-2 bg-emerald-600/20 rounded-xl border border-emerald-500/30 text-emerald-400">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">
            {summary ? summary.active_examiners : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Active platform accounts</p>
        </div>

        {/* Inactive Examiners */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Inactive Examiners
            </p>
            <div className="p-2 bg-amber-600/20 rounded-xl border border-amber-500/30 text-amber-400">
              <UserX className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-amber-400 mt-3">
            {summary ? summary.inactive_examiners : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Deactivated examiner accounts</p>
        </div>

        {/* Unassigned College */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Unassigned College
            </p>
            <div className="p-2 bg-purple-600/20 rounded-xl border border-purple-500/30 text-purple-400">
              <Building2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-purple-300 mt-3">
            {summary ? summary.unassigned_college : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Missing institutional assignment</p>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 space-y-4 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search by examiner name or email..."
              className="w-full pl-10 pr-10 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
            {search && (
              <button
                onClick={() => handleSearchChange('')}
                className="absolute right-3.5 top-3 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Clear Filters Button */}
          {hasActiveFilters && (
            <button
              onClick={handleResetFilters}
              className="px-3.5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition shrink-0"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Clear Filters
            </button>
          )}
        </div>

        {/* Filter Controls Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1 border-t border-slate-800/60">
          {/* College Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Assigned College
            </label>
            <select
              value={selectedCollegeId}
              onChange={(e) => {
                setSelectedCollegeId(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition"
            >
              <option value="">All Colleges</option>
              {colleges.map((col) => (
                <option key={col.id} value={col.id}>
                  {col.name} ({col.code})
                </option>
              ))}
            </select>
          </div>

          {/* Account Status Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Account Status
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition"
            >
              <option value="">All Statuses</option>
              <option value="true">Active Only</option>
              <option value="false">Inactive Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Examiner Records Table */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur-sm">
        {loading ? (
          <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
            <span>Loading examiners list...</span>
          </div>
        ) : error ? (
          <div className="p-8 text-center space-y-4">
            <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-xl inline-block text-red-400">
              <AlertCircle className="w-6 h-6 mx-auto" />
            </div>
            <p className="text-sm font-semibold text-red-300">{error}</p>
            <button
              onClick={fetchExaminers}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 mx-auto"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry Loading
            </button>
          </div>
        ) : examiners.length === 0 ? (
          <div className="p-16 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700/80 flex items-center justify-center mx-auto text-slate-400">
              <UserCheck className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-white">
              {hasActiveFilters ? 'No examiners match your filters' : 'No examiners found'}
            </h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              {hasActiveFilters
                ? 'Try adjusting your search query or relaxing your college filter.'
                : 'There are currently no examiners provisioned on the platform.'}
            </p>
            {hasActiveFilters && (
              <button
                onClick={handleResetFilters}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition inline-block mt-2"
              >
                Reset All Filters
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                    <th className="py-3.5 px-4">Examiner</th>
                    <th className="py-3.5 px-4">Email</th>
                    <th className="py-3.5 px-4">Assigned College</th>
                    <th className="py-3.5 px-4">Exams Created</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4">Registered</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {examiners.map((examiner) => {
                    const initials = `${examiner.first_name[0] || ''}${
                      examiner.last_name[0] || ''
                    }`.toUpperCase() || 'EX';

                    return (
                      <tr
                        key={examiner.id}
                        className="hover:bg-slate-800/40 transition-colors group"
                      >
                        {/* Examiner Name & Avatar */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 font-bold flex items-center justify-center text-xs shrink-0">
                              {initials}
                            </div>
                            <div>
                              <p className="font-semibold text-white">
                                {examiner.first_name} {examiner.last_name}
                              </p>
                              <span className="text-[10px] text-slate-500">
                                Examiner Account
                              </span>
                            </div>
                          </div>
                        </td>

                        {/* Email */}
                        <td className="py-3.5 px-4 font-mono text-slate-300 text-[11px]">
                          {examiner.email}
                        </td>

                        {/* Assigned College */}
                        <td className="py-3.5 px-4">
                          {examiner.college_name ? (
                            <div>
                              <p className="font-medium text-slate-200">{examiner.college_name}</p>
                              {examiner.college_code && (
                                <span className="text-[10px] font-mono text-slate-500">
                                  {examiner.college_code}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500 italic">Not assigned</span>
                          )}
                        </td>

                        {/* Exams Created & Published */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-white text-sm">
                              {examiner.total_exams_count}
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/60">
                              {examiner.published_exams_count} Published
                            </span>
                          </div>
                        </td>

                        {/* Status Badge */}
                        <td className="py-3.5 px-4">
                          {examiner.is_active ? (
                            <span className="px-2.5 py-1 rounded-md text-[10px] font-bold font-mono uppercase bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 w-fit">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Active
                            </span>
                          ) : (
                            <span className="px-2.5 py-1 rounded-md text-[10px] font-bold font-mono uppercase bg-red-950/80 text-red-400 border border-red-500/30 flex items-center gap-1.5 w-fit">
                              <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span> Inactive
                            </span>
                          )}
                        </td>

                        {/* Registration Date */}
                        <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                          {new Date(examiner.created_at).toLocaleDateString()}
                        </td>

                        {/* Actions */}
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {/* View Details Button */}
                            <button
                              onClick={() => handleOpenDetail(examiner.id)}
                              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition font-medium flex items-center gap-1 text-[11px] border border-slate-700/60"
                              title="View Examiner Details"
                            >
                              <Eye className="w-3.5 h-3.5 text-indigo-400" /> Details
                            </button>

                            {/* Toggle Status Button */}
                            <button
                              onClick={() => setStatusModalExaminer(examiner)}
                              className={`px-2.5 py-1.5 rounded-lg transition font-medium text-[11px] border ${
                                examiner.is_active
                                  ? 'bg-amber-950/40 hover:bg-amber-900/50 text-amber-300 border-amber-800/50'
                                  : 'bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 border-emerald-800/50'
                              }`}
                              title={
                                examiner.is_active
                                  ? 'Deactivate Examiner Account'
                                  : 'Activate Examiner Account'
                              }
                            >
                              {examiner.is_active ? 'Deactivate' : 'Activate'}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination Bar */}
            <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between text-xs text-slate-400">
              <span>
                Showing <strong className="text-white">{examiners.length}</strong> of{' '}
                <strong className="text-white">{totalExaminers}</strong> examiners (Page{' '}
                <strong className="text-white">{page}</strong> of{' '}
                <strong className="text-white">{totalPages}</strong>)
              </span>

              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" /> Previous
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
                >
                  Next <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* EXAMINER DETAILS MODAL */}
      {selectedExaminerId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl my-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-600/20 rounded-xl border border-indigo-500/30 text-indigo-400">
                  <UserCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Examiner Details</h3>
                  <p className="text-xs text-slate-400">
                    Institutional profile and exam management records
                  </p>
                </div>
              </div>
              <button
                onClick={handleCloseDetail}
                className="text-slate-400 hover:text-white transition p-1"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {detailLoading ? (
              <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
                <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
                <span>Loading examiner records...</span>
              </div>
            ) : detailError ? (
              <div className="p-6 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-xs space-y-2">
                <p className="font-bold">{detailError}</p>
                <button
                  onClick={() => handleOpenDetail(selectedExaminerId)}
                  className="px-3 py-1.5 bg-red-900/60 hover:bg-red-800 rounded-lg text-white font-semibold transition"
                >
                  Retry
                </button>
              </div>
            ) : examinerDetail ? (
              <div className="space-y-5 text-xs">
                {/* 1. Personal Information */}
                <div className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-3">
                  <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800/60 pb-2">
                    <Users className="w-3.5 h-3.5 text-indigo-400" /> Personal Information
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <span className="text-[10px] text-slate-400 block">Full Name</span>
                      <p className="font-semibold text-white text-sm">
                        {examinerDetail.first_name} {examinerDetail.last_name}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Email Address</span>
                      <p className="font-mono text-slate-200">{examinerDetail.email}</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Role</span>
                      <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                        {examinerDetail.role}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Account Status</span>
                      {examinerDetail.is_active ? (
                        <span className="text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Active
                        </span>
                      ) : (
                        <span className="text-red-400 font-semibold flex items-center gap-1">
                          <AlertCircle className="w-3.5 h-3.5" /> Deactivated
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Registered Date</span>
                      <p className="text-slate-300 font-mono">
                        {new Date(examinerDetail.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* 2. Institutional Scope */}
                <div className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-3">
                  <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800/60 pb-2">
                    <Building2 className="w-3.5 h-3.5 text-emerald-400" /> Institutional Scope
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <span className="text-[10px] text-slate-400 block">Assigned College</span>
                      <p className="font-medium text-white">
                        {examinerDetail.college_name || 'Not assigned'}
                      </p>
                      {examinerDetail.college_code && (
                        <span className="text-[10px] font-mono text-slate-500">
                          Code: {examinerDetail.college_code}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 3. Examination Ownership Activity */}
                <div className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-3">
                  <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800/60 pb-2">
                    <BookOpen className="w-3.5 h-3.5 text-blue-400" /> Examination Ownership Activity
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-center">
                      <span className="text-[10px] text-slate-400 block">Total Created</span>
                      <p className="text-xl font-bold text-white mt-1">
                        {examinerDetail.total_exams_created}
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-center">
                      <span className="text-[10px] text-emerald-400 block">Published</span>
                      <p className="text-xl font-bold text-emerald-400 mt-1">
                        {examinerDetail.published_exams_count}
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-center">
                      <span className="text-[10px] text-slate-400 block">Draft</span>
                      <p className="text-xl font-bold text-slate-300 mt-1">
                        {examinerDetail.draft_exams_count}
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-center">
                      <span className="text-[10px] text-purple-400 block">Completed</span>
                      <p className="text-xl font-bold text-purple-300 mt-1">
                        {examinerDetail.completed_exams_count}
                      </p>
                    </div>
                  </div>

                  {/* Recent Exams List */}
                  <div className="pt-2">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                      Recent Examinations
                    </span>
                    {examinerDetail.recent_exams.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic text-center py-3 bg-slate-900/50 rounded-lg">
                        No examinations created yet.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {examinerDetail.recent_exams.map((exam) => (
                          <div
                            key={exam.id}
                            className="p-3 bg-slate-900/90 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                          >
                            <div>
                              <p className="font-semibold text-white">{exam.title}</p>
                              <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                                <span>{exam.subject}</span>
                                <span>•</span>
                                <span>{exam.duration_minutes} mins</span>
                                <span>•</span>
                                <span>{exam.total_marks} Marks</span>
                                {exam.target_type && (
                                  <>
                                    <span>•</span>
                                    <span className="font-mono text-indigo-400">
                                      Target: {exam.target_type}
                                    </span>
                                  </>
                                )}
                              </div>
                            </div>
                            <div className="text-right">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                                  exam.status === 'PUBLISHED'
                                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                    : exam.status === 'DRAFT'
                                    ? 'bg-slate-800 text-slate-300 border border-slate-700'
                                    : 'bg-blue-950 text-blue-300 border border-blue-800'
                                }`}
                              >
                                {exam.status}
                              </span>
                              <span className="text-[10px] text-slate-500 block mt-1 font-mono">
                                {new Date(exam.created_at).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    onClick={handleCloseDetail}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* CONFIRM STATUS TOGGLE DIALOG */}
      {statusModalExaminer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold text-white">Confirm Account Status Change</h3>
              </div>
              <button
                onClick={() => setStatusModalExaminer(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-300 leading-relaxed">
                Are you sure you want to{' '}
                <strong className="text-white">
                  {statusModalExaminer.is_active ? 'deactivate' : 'activate'}
                </strong>{' '}
                the examiner account for{' '}
                <strong className="text-white">
                  {statusModalExaminer.first_name} {statusModalExaminer.last_name}
                </strong>{' '}
                ({statusModalExaminer.email})?
              </p>

              {statusModalExaminer.is_active && (
                <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-300 text-[11px] leading-relaxed">
                  Deactivated examiners will be immediately prevented from logging into ExamGuard
                  AI, managing examinations, or creating questions.
                </div>
              )}

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setStatusModalExaminer(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleStatusToggle}
                  disabled={statusUpdating}
                  className={`px-4 py-2 rounded-xl text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 ${
                    statusModalExaminer.is_active
                      ? 'bg-red-600 hover:bg-red-500'
                      : 'bg-emerald-600 hover:bg-emerald-500'
                  }`}
                >
                  {statusUpdating ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : statusModalExaminer.is_active ? (
                    'Deactivate Examiner'
                  ) : (
                    'Activate Examiner'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
