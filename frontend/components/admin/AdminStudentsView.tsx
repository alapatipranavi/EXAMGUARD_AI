'use client';

import React, { useState, useEffect, useCallback } from 'react';
import PageHeader from '@/components/layout/PageHeader';
import {
  GraduationCap,
  Users,
  Search,
  Filter,
  UserCheck,
  UserX,
  Eye,
  Loader2,
  AlertCircle,
  CheckCircle2,
  X,
  ChevronLeft,
  ChevronRight,
  Building2,
  BookOpen,
  Calendar,
  Clock,
  ShieldCheck,
  Award,
  RefreshCw,
  RotateCcw,
} from 'lucide-react';
import {
  adminStudentsAPI,
  adminAPI,
  academicAPI,
  AdminStudentListItem,
  AdminStudentSummaryMetrics,
  AdminStudentDetailResponse,
  College,
  Department,
  Section,
} from '@/lib/api';

export default function AdminStudentsView() {
  const [students, setStudents] = useState<AdminStudentListItem[]>([]);
  const [summary, setSummary] = useState<AdminStudentSummaryMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  // Pagination & Filtering
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [totalStudents, setTotalStudents] = useState(0);

  // Search & Filter state
  const [search, setSearch] = useState('');
  const [selectedCollegeId, setSelectedCollegeId] = useState('');
  const [selectedDeptId, setSelectedDeptId] = useState('');
  const [selectedYear, setSelectedYear] = useState<string>('');
  const [selectedSectionId, setSelectedSectionId] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');

  // Cascading Academic Options
  const [colleges, setColleges] = useState<College[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [loadingDepts, setLoadingDepts] = useState(false);
  const [loadingSections, setLoadingSections] = useState(false);

  // Detail Modal State
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [studentDetail, setStudentDetail] = useState<AdminStudentDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Status Toggle Modal State
  const [statusModalStudent, setStatusModalStudent] = useState<AdminStudentListItem | null>(null);
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
        console.error('Failed to load colleges:', err);
      }
    }
    loadColleges();
  }, []);

  // 2. Cascading: When College Changes -> Fetch Departments
  useEffect(() => {
    async function updateDepartments() {
      if (!selectedCollegeId) {
        setDepartments([]);
        setSelectedDeptId('');
        setSections([]);
        setSelectedSectionId('');
        return;
      }
      setLoadingDepts(true);
      try {
        const depts = await academicAPI.getPublicDepartments(selectedCollegeId);
        setDepartments(depts);
        setSelectedDeptId('');
        setSections([]);
        setSelectedSectionId('');
      } catch (err) {
        console.error('Failed to load departments:', err);
      } finally {
        setLoadingDepts(false);
      }
    }
    updateDepartments();
  }, [selectedCollegeId]);

  // 3. Cascading: When Department or Year Changes -> Fetch Sections
  useEffect(() => {
    async function updateSections() {
      if (!selectedDeptId) {
        setSections([]);
        setSelectedSectionId('');
        return;
      }
      setLoadingSections(true);
      try {
        const yearNum = selectedYear ? parseInt(selectedYear, 10) : undefined;
        const secs = await academicAPI.getPublicSections(selectedDeptId, yearNum);
        setSections(secs);
        setSelectedSectionId('');
      } catch (err) {
        console.error('Failed to load sections:', err);
      } finally {
        setLoadingSections(false);
      }
    }
    updateSections();
  }, [selectedDeptId, selectedYear]);

  // 4. Fetch Students List
  const fetchStudents = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const is_active_param =
        selectedStatus === '' ? undefined : selectedStatus === 'true';

      const res = await adminStudentsAPI.list({
        search: search.trim() || undefined,
        college_id: selectedCollegeId || undefined,
        department_id: selectedDeptId || undefined,
        year_of_study: selectedYear ? parseInt(selectedYear, 10) : undefined,
        section_id: selectedSectionId || undefined,
        is_active: is_active_param,
        page,
        page_size: pageSize,
      });

      setStudents(res.items);
      setTotalPages(res.total_pages || 1);
      setTotalStudents(res.total || 0);
      setSummary(res.summary);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch students.');
    } finally {
      setLoading(false);
    }
  }, [
    page,
    pageSize,
    search,
    selectedCollegeId,
    selectedDeptId,
    selectedYear,
    selectedSectionId,
    selectedStatus,
  ]);

  useEffect(() => {
    fetchStudents();
  }, [fetchStudents]);

  // Handle Search Input Change
  const handleSearchChange = (val: string) => {
    setSearch(val);
    setPage(1);
  };

  // Reset All Filters
  const handleResetFilters = () => {
    setSearch('');
    setSelectedCollegeId('');
    setSelectedDeptId('');
    setSelectedYear('');
    setSelectedSectionId('');
    setSelectedStatus('');
    setPage(1);
  };

  // Open Detail Modal
  const handleOpenDetail = async (studentId: string) => {
    setSelectedStudentId(studentId);
    setStudentDetail(null);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const detail = await adminStudentsAPI.getDetail(studentId);
      setStudentDetail(detail);
    } catch (err: unknown) {
      setDetailError(err instanceof Error ? err.message : 'Failed to load student details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedStudentId(null);
    setStudentDetail(null);
    setDetailError(null);
  };

  // Toggle Account Status
  const handleStatusToggle = async () => {
    if (!statusModalStudent) return;
    setStatusUpdating(true);
    try {
      const updatedStatus = !statusModalStudent.is_active;
      await adminAPI.updateUserStatus(statusModalStudent.id, updatedStatus);
      showToast(
        `Student account for ${statusModalStudent.first_name} ${statusModalStudent.last_name} successfully ${
          updatedStatus ? 'activated' : 'deactivated'
        }.`
      );
      setStatusModalStudent(null);
      fetchStudents();
    } catch (err: unknown) {
      showToast(
        err instanceof Error ? err.message : 'Failed to update student account status.',
        'error'
      );
    } finally {
      setStatusUpdating(false);
    }
  };

  // Helper for Year of Study Formatting
  const formatYear = (year?: number | null) => {
    if (!year) return 'Not assigned';
    switch (year) {
      case 1:
        return '1st Year';
      case 2:
        return '2nd Year';
      case 3:
        return '3rd Year';
      case 4:
        return '4th Year';
      default:
        return `Year ${year}`;
    }
  };

  const hasActiveFilters =
    search ||
    selectedCollegeId ||
    selectedDeptId ||
    selectedYear ||
    selectedSectionId ||
    selectedStatus;

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
        title="Students"
        subtitle="Manage and review students registered on the platform."
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Students */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Total Students
            </p>
            <div className="p-2 bg-indigo-600/20 rounded-xl border border-indigo-500/30 text-indigo-400">
              <GraduationCap className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-white mt-3">
            {summary ? summary.total_students : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Platform registered students</p>
        </div>

        {/* Active Students */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Students
            </p>
            <div className="p-2 bg-emerald-600/20 rounded-xl border border-emerald-500/30 text-emerald-400">
              <UserCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-emerald-400 mt-3">
            {summary ? summary.active_students : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Active platform accounts</p>
        </div>

        {/* Inactive Students */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Inactive Students
            </p>
            <div className="p-2 bg-amber-600/20 rounded-xl border border-amber-500/30 text-amber-400">
              <UserX className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-amber-400 mt-3">
            {summary ? summary.inactive_students : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Deactivated student accounts</p>
        </div>

        {/* Unassigned Profiles */}
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Unassigned Profiles
            </p>
            <div className="p-2 bg-purple-600/20 rounded-xl border border-purple-500/30 text-purple-400">
              <Building2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-purple-300 mt-3">
            {summary ? summary.unassigned_academic_profiles : '--'}
          </p>
          <p className="text-[11px] text-slate-400 mt-1">Missing institutional scope</p>
        </div>
      </div>

      {/* Search & Cascading Filter Bar */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-5 space-y-4 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row gap-3">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search by student name or email..."
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

        {/* Cascading Filter Controls Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 pt-1 border-t border-slate-800/60">
          {/* College Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              College
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

          {/* Department Filter (Cascading) */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
              Department
              {loadingDepts && <Loader2 className="w-2.5 h-2.5 animate-spin text-indigo-400" />}
            </label>
            <select
              value={selectedDeptId}
              onChange={(e) => {
                setSelectedDeptId(e.target.value);
                setPage(1);
              }}
              disabled={!selectedCollegeId || loadingDepts}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">
                {!selectedCollegeId ? 'Select College first' : 'All Departments'}
              </option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name} ({dept.code})
                </option>
              ))}
            </select>
          </div>

          {/* Year of Study Filter */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Year of Study
            </label>
            <select
              value={selectedYear}
              onChange={(e) => {
                setSelectedYear(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition"
            >
              <option value="">All Years</option>
              <option value="1">1st Year</option>
              <option value="2">2nd Year</option>
              <option value="3">3rd Year</option>
              <option value="4">4th Year</option>
            </select>
          </div>

          {/* Section Filter (Cascading) */}
          <div>
            <label className="block text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
              Section
              {loadingSections && <Loader2 className="w-2.5 h-2.5 animate-spin text-indigo-400" />}
            </label>
            <select
              value={selectedSectionId}
              onChange={(e) => {
                setSelectedSectionId(e.target.value);
                setPage(1);
              }}
              disabled={!selectedDeptId || loadingSections}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">
                {!selectedDeptId ? 'Select Department first' : 'All Sections'}
              </option>
              {sections.map((sec) => (
                <option key={sec.id} value={sec.id}>
                  {sec.name} ({sec.code})
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

      {/* Main Student Records Table */}
      <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl overflow-hidden backdrop-blur-sm">
        {loading ? (
          <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
            <span>Loading students list...</span>
          </div>
        ) : error ? (
          <div className="p-8 text-center space-y-4">
            <div className="p-3 bg-red-950/40 border border-red-800/60 rounded-xl inline-block text-red-400">
              <AlertCircle className="w-6 h-6 mx-auto" />
            </div>
            <p className="text-sm font-semibold text-red-300">{error}</p>
            <button
              onClick={fetchStudents}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 mx-auto"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry Loading
            </button>
          </div>
        ) : students.length === 0 ? (
          <div className="p-16 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700/80 flex items-center justify-center mx-auto text-slate-400">
              <GraduationCap className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-white">
              {hasActiveFilters ? 'No students match your filters' : 'No students found'}
            </h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              {hasActiveFilters
                ? 'Try adjusting your search query or relaxing your academic filters.'
                : 'There are currently no students registered on the platform.'}
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
                    <th className="py-3.5 px-4">Student</th>
                    <th className="py-3.5 px-4">Email</th>
                    <th className="py-3.5 px-4">College</th>
                    <th className="py-3.5 px-4">Department</th>
                    <th className="py-3.5 px-4">Year</th>
                    <th className="py-3.5 px-4">Section</th>
                    <th className="py-3.5 px-4">Status</th>
                    <th className="py-3.5 px-4">Registered</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {students.map((student) => {
                    const initials = `${student.first_name[0] || ''}${
                      student.last_name[0] || ''
                    }`.toUpperCase() || 'ST';

                    return (
                      <tr
                        key={student.id}
                        className="hover:bg-slate-800/40 transition-colors group"
                      >
                        {/* Student Name & Avatar */}
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 font-bold flex items-center justify-center text-xs shrink-0">
                              {initials}
                            </div>
                            <div>
                              <p className="font-semibold text-white">
                                {student.first_name} {student.last_name}
                              </p>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                {student.is_face_registered ? (
                                  <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                                    <ShieldCheck className="w-2.5 h-2.5" /> Biometric Verified
                                  </span>
                                ) : (
                                  <span className="text-[10px] text-slate-500">
                                    Biometric Pending
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Email */}
                        <td className="py-3.5 px-4 font-mono text-slate-300 text-[11px]">
                          {student.email}
                        </td>

                        {/* College */}
                        <td className="py-3.5 px-4">
                          {student.college_name ? (
                            <div>
                              <p className="font-medium text-slate-200">{student.college_name}</p>
                              {student.college_code && (
                                <span className="text-[10px] font-mono text-slate-500">
                                  {student.college_code}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500 italic">Not assigned</span>
                          )}
                        </td>

                        {/* Department */}
                        <td className="py-3.5 px-4">
                          {student.department_name ? (
                            <div>
                              <p className="font-medium text-slate-200">
                                {student.department_name}
                              </p>
                              {student.department_code && (
                                <span className="text-[10px] font-mono text-slate-500">
                                  {student.department_code}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500 italic">Not assigned</span>
                          )}
                        </td>

                        {/* Year */}
                        <td className="py-3.5 px-4">
                          <span
                            className={
                              student.year_of_study
                                ? 'font-medium text-slate-200'
                                : 'text-slate-500 italic'
                            }
                          >
                            {formatYear(student.year_of_study)}
                          </span>
                        </td>

                        {/* Section */}
                        <td className="py-3.5 px-4">
                          {student.section_name ? (
                            <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-mono text-[11px] border border-slate-700">
                              {student.section_name}
                            </span>
                          ) : (
                            <span className="text-slate-500 italic">Not assigned</span>
                          )}
                        </td>

                        {/* Status Badge */}
                        <td className="py-3.5 px-4">
                          {student.is_active ? (
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
                          {new Date(student.created_at).toLocaleDateString()}
                        </td>

                        {/* Actions */}
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {/* View Details Button */}
                            <button
                              onClick={() => handleOpenDetail(student.id)}
                              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition font-medium flex items-center gap-1 text-[11px] border border-slate-700/60"
                              title="View Student Details"
                            >
                              <Eye className="w-3.5 h-3.5 text-indigo-400" /> Details
                            </button>

                            {/* Toggle Status Button */}
                            <button
                              onClick={() => setStatusModalStudent(student)}
                              className={`px-2.5 py-1.5 rounded-lg transition font-medium text-[11px] border ${
                                student.is_active
                                  ? 'bg-amber-950/40 hover:bg-amber-900/50 text-amber-300 border-amber-800/50'
                                  : 'bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 border-emerald-800/50'
                              }`}
                              title={
                                student.is_active
                                  ? 'Deactivate Student Account'
                                  : 'Activate Student Account'
                              }
                            >
                              {student.is_active ? 'Deactivate' : 'Activate'}
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
                Showing <strong className="text-white">{students.length}</strong> of{' '}
                <strong className="text-white">{totalStudents}</strong> students (Page{' '}
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

      {/* STUDENT DETAILS MODAL */}
      {selectedStudentId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl my-8">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-600/20 rounded-xl border border-indigo-500/30 text-indigo-400">
                  <GraduationCap className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Student Details</h3>
                  <p className="text-xs text-slate-400">
                    Comprehensive profile and examination records
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
                <span>Loading student records...</span>
              </div>
            ) : detailError ? (
              <div className="p-6 bg-red-950/40 border border-red-800 text-red-300 rounded-xl text-xs space-y-2">
                <p className="font-bold">{detailError}</p>
                <button
                  onClick={() => handleOpenDetail(selectedStudentId)}
                  className="px-3 py-1.5 bg-red-900/60 hover:bg-red-800 rounded-lg text-white font-semibold transition"
                >
                  Retry
                </button>
              </div>
            ) : studentDetail ? (
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
                        {studentDetail.first_name} {studentDetail.last_name}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Email Address</span>
                      <p className="font-mono text-slate-200">{studentDetail.email}</p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Role</span>
                      <span className="px-2 py-0.5 text-[10px] font-mono font-bold rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                        {studentDetail.role}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Account Status</span>
                      {studentDetail.is_active ? (
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
                        {new Date(studentDetail.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Biometric Identity</span>
                      {studentDetail.is_face_registered ? (
                        <span className="text-emerald-400 font-semibold flex items-center gap-1">
                          <ShieldCheck className="w-3.5 h-3.5" /> Verified (
                          {studentDetail.face_registered_at
                            ? new Date(studentDetail.face_registered_at).toLocaleDateString()
                            : 'Active'}
                          )
                        </span>
                      ) : (
                        <span className="text-amber-400 flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" /> Pending Registration
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 2. Academic Information */}
                <div className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-3">
                  <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800/60 pb-2">
                    <Building2 className="w-3.5 h-3.5 text-emerald-400" /> Academic & Institution
                    Scope
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <span className="text-[10px] text-slate-400 block">College</span>
                      <p className="font-medium text-white">
                        {studentDetail.college_name || 'Not assigned'}
                      </p>
                      {studentDetail.college_code && (
                        <span className="text-[10px] font-mono text-slate-500">
                          Code: {studentDetail.college_code}
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Department</span>
                      <p className="font-medium text-white">
                        {studentDetail.department_name || 'Not assigned'}
                      </p>
                      {studentDetail.department_code && (
                        <span className="text-[10px] font-mono text-slate-500">
                          Code: {studentDetail.department_code}
                        </span>
                      )}
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Year of Study</span>
                      <p className="font-medium text-white">
                        {formatYear(studentDetail.year_of_study)}
                      </p>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Section</span>
                      <p className="font-medium text-white">
                        {studentDetail.section_name || 'Not assigned'}
                      </p>
                      {studentDetail.section_code && (
                        <span className="text-[10px] font-mono text-slate-500">
                          Code: {studentDetail.section_code}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* 3. Examination Activity Summary */}
                <div className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-xl space-y-3">
                  <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-800/60 pb-2">
                    <BookOpen className="w-3.5 h-3.5 text-blue-400" /> Examination Activity
                  </h4>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-center">
                      <span className="text-[10px] text-slate-400 block">Assigned Exams</span>
                      <p className="text-xl font-bold text-white mt-1">
                        {studentDetail.exams_assigned_count}
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-center">
                      <span className="text-[10px] text-slate-400 block">Attempted</span>
                      <p className="text-xl font-bold text-amber-300 mt-1">
                        {studentDetail.exams_attempted_count}
                      </p>
                    </div>
                    <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl text-center">
                      <span className="text-[10px] text-slate-400 block">Completed</span>
                      <p className="text-xl font-bold text-emerald-400 mt-1">
                        {studentDetail.exams_completed_count}
                      </p>
                    </div>
                  </div>

                  {/* Recent Sessions List */}
                  <div className="pt-2">
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                      Recent Sessions
                    </span>
                    {studentDetail.recent_sessions.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic text-center py-3 bg-slate-900/50 rounded-lg">
                        No examination sessions attempted yet.
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {studentDetail.recent_sessions.map((sess) => (
                          <div
                            key={sess.session_id}
                            className="p-3 bg-slate-900/90 border border-slate-800 rounded-xl flex items-center justify-between text-xs"
                          >
                            <div>
                              <p className="font-semibold text-white">{sess.exam_title}</p>
                              <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                                <span>{sess.exam_subject}</span>
                                <span>•</span>
                                <span className="font-mono">Status: {sess.status}</span>
                              </div>
                            </div>
                            <div className="text-right">
                              {sess.percentage !== null && sess.percentage !== undefined ? (
                                <div>
                                  <span className="font-bold text-white">{sess.percentage}%</span>
                                  {sess.pass_fail_status && (
                                    <span
                                      className={`block text-[10px] font-bold ${
                                        sess.pass_fail_status === 'PASSED'
                                          ? 'text-emerald-400'
                                          : 'text-red-400'
                                      }`}
                                    >
                                      {sess.pass_fail_status}
                                    </span>
                                  )}
                                </div>
                              ) : (
                                <span className="text-[10px] text-slate-500 italic">Pending</span>
                              )}
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
      {statusModalStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold text-white">Confirm Account Status Change</h3>
              </div>
              <button
                onClick={() => setStatusModalStudent(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-300 leading-relaxed">
                Are you sure you want to{' '}
                <strong className="text-white">
                  {statusModalStudent.is_active ? 'deactivate' : 'activate'}
                </strong>{' '}
                the student account for{' '}
                <strong className="text-white">
                  {statusModalStudent.first_name} {statusModalStudent.last_name}
                </strong>{' '}
                ({statusModalStudent.email})?
              </p>

              {statusModalStudent.is_active && (
                <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-300 text-[11px] leading-relaxed">
                  Deactivated students will be immediately prevented from logging into ExamGuard
                  AI or taking any examinations.
                </div>
              )}

              <div className="pt-3 flex items-center justify-end gap-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setStatusModalStudent(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleStatusToggle}
                  disabled={statusUpdating}
                  className={`px-4 py-2 rounded-xl text-white text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 ${
                    statusModalStudent.is_active
                      ? 'bg-red-600 hover:bg-red-500'
                      : 'bg-emerald-600 hover:bg-emerald-500'
                  }`}
                >
                  {statusUpdating ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : statusModalStudent.is_active ? (
                    'Deactivate Student'
                  ) : (
                    'Activate Student'
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
