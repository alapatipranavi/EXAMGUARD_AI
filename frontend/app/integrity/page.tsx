'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
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
  Eye,
  X,
  Activity,
  Layers,
  Sparkles,
  ArrowUpRight,
  TrendingDown,
} from 'lucide-react';
import {
  authAPI,
  examsAPI,
  integrityAPI,
  User,
  Exam,
  PaginatedExamIntegrityResponse,
  ExamIntegritySummaryItem,
  SessionIntegrityDetailResponse,
} from '@/lib/api';
import StudentIntegrityView from '@/components/integrity/StudentIntegrityView';

export default function IntegrityPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>('');
  const [integrityData, setIntegrityData] = useState<PaginatedExamIntegrityResponse | null>(null);
  const [loadingExams, setLoadingExams] = useState(true);
  const [loadingIntegrity, setLoadingIntegrity] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState('');
  const [riskFilter, setRiskFilter] = useState<string>('ALL');

  // Detail Modal State
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<SessionIntegrityDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // 1. Load User & Exams
  useEffect(() => {
    async function loadInitial() {
      try {
        const user = await authAPI.getMe();
        setCurrentUser(user);

        if (user.role === 'STUDENT') {
          setLoadingExams(false);
          return;
        }

        const examsResp = await examsAPI.list({ page_size: 100 });
        const availableExams = examsResp.items || [];
        setExams(availableExams);

        if (availableExams.length > 0) {
          setSelectedExamId(availableExams[0].id);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to load initial integrity parameters.');
      } finally {
        setLoadingExams(false);
      }
    }
    loadInitial();
  }, []);

  // 2. Fetch Integrity Data on exam or filter change
  useEffect(() => {
    if (!selectedExamId || currentUser?.role === 'STUDENT') return;

    async function fetchIntegrity() {
      setLoadingIntegrity(true);
      setError(null);
      try {
        const res = await integrityAPI.getExamIntegrity(selectedExamId, {
          search: searchQuery || undefined,
          risk_level: riskFilter !== 'ALL' ? riskFilter : undefined,
          page_size: 50,
        });
        setIntegrityData(res);
      } catch (err: any) {
        setError(err?.message || 'Failed to calculate integrity metrics.');
      } finally {
        setLoadingIntegrity(false);
      }
    }
    fetchIntegrity();
  }, [selectedExamId, searchQuery, riskFilter, currentUser]);

  // Handle Exam Selection
  const handleExamChange = (examId: string) => {
    setSelectedExamId(examId);
  };

  // Open Session Detail Modal
  const handleOpenDetail = async (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setLoadingDetail(true);
    setSessionDetail(null);
    try {
      const detail = await integrityAPI.getSessionIntegrity(selectedExamId, sessionId);
      setSessionDetail(detail);
    } catch (err: any) {
      setError(err?.message || 'Failed to load session integrity details.');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedSessionId(null);
    setSessionDetail(null);
  };

  // Student Integrity Status View
  if (!loadingExams && currentUser?.role === 'STUDENT') {
    return (
      <AppShell title="Integrity Status">
        <StudentIntegrityView user={currentUser} />
      </AppShell>
    );
  }

  // Risk Badge Styling Helper
  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case 'LOW':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold font-mono uppercase bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 w-fit">
            <CheckCircle2 className="w-3 h-3" /> LOW RISK
          </span>
        );
      case 'MODERATE':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold font-mono uppercase bg-amber-950/80 text-amber-400 border border-amber-500/30 flex items-center gap-1.5 w-fit">
            <AlertTriangle className="w-3 h-3" /> MODERATE RISK
          </span>
        );
      case 'HIGH':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold font-mono uppercase bg-rose-950/80 text-rose-400 border border-rose-500/30 flex items-center gap-1.5 w-fit">
            <ShieldAlert className="w-3 h-3" /> HIGH RISK
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-bold font-mono uppercase bg-slate-800 text-slate-300 border border-slate-700 w-fit">
            {risk}
          </span>
        );
    }
  };

  // Severity Badge Helper
  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-rose-950 text-rose-400 border border-rose-800">{severity}</span>;
      case 'WARNING':
      case 'MEDIUM':
        return <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-amber-950 text-amber-400 border border-amber-800">{severity}</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-800 text-slate-400 border border-slate-700">{severity}</span>;
    }
  };

  return (
    <AppShell title="Integrity Analysis" allowedRoles={['EXAMINER', 'ADMIN']}>
      <div className="space-y-6 max-w-7xl mx-auto pb-16">
        {/* Header */}
        <PageHeader
          title="Integrity Analysis"
          subtitle="Explainable multi-signal integrity assessment, risk level classification, evidence indicators, and chronological session timelines."
        />

        {/* Toolbar: Exam Selector */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <label className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                Selected Examination
              </label>
              <p className="text-xs text-slate-300 font-semibold">
                {integrityData ? `${integrityData.exam_title} (${integrityData.exam_subject})` : 'Select an Exam'}
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

        {/* Main Content */}
        {loadingIntegrity || loadingExams ? (
          <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span>Computing multi-signal session integrity assessments...</span>
          </div>
        ) : !integrityData || exams.length === 0 ? (
          <div className="p-16 text-center text-slate-400 text-xs flex flex-col items-center gap-3 bg-slate-900/60 border border-slate-800 rounded-2xl">
            <ShieldAlert className="w-12 h-12 text-slate-600" />
            <p className="font-semibold text-slate-300 text-sm">No Examination Data Selected</p>
            <p className="text-slate-500 max-w-md">
              Create an examination and conduct sessions to evaluate multi-signal integrity metrics.
            </p>
          </div>
        ) : (
          <>
            {/* Top Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Card 1: Avg Integrity Score */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2 relative overflow-hidden">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>Average Integrity Score</span>
                  <Activity className="w-4 h-4 text-indigo-400" />
                </div>
                <div className="text-2xl font-bold text-white font-mono tracking-tight">
                  {integrityData.average_integrity_score} <span className="text-xs text-slate-500 font-sans">/ 100</span>
                </div>
                <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      integrityData.average_integrity_score >= 85
                        ? 'bg-emerald-500'
                        : integrityData.average_integrity_score >= 65
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                    }`}
                    style={{ width: `${integrityData.average_integrity_score}%` }}
                  />
                </div>
              </div>

              {/* Card 2: Low Risk Sessions */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>Low Risk Sessions</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-2xl font-bold text-emerald-400 font-mono">
                  {integrityData.low_risk_count}
                </div>
                <p className="text-[10px] text-slate-500">Standard session activity</p>
              </div>

              {/* Card 3: Moderate Risk Sessions */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>Moderate Risk Sessions</span>
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-2xl font-bold text-amber-400 font-mono">
                  {integrityData.moderate_risk_count}
                </div>
                <p className="text-[10px] text-slate-500">Minor session anomalies</p>
              </div>

              {/* Card 4: High Risk Sessions */}
              <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between text-slate-400 text-xs">
                  <span>High Risk Sessions</span>
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                </div>
                <div className="text-2xl font-bold text-rose-400 font-mono">
                  {integrityData.high_risk_count}
                </div>
                <p className="text-[10px] text-slate-500">Examiner review recommended</p>
              </div>
            </div>

            {/* Sessions Roster Section */}
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-5 shadow-xl">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-bold text-white tracking-tight">Student Session Integrity Roster</h3>
                  <p className="text-xs text-slate-400">
                    Individual student session evaluations, risk classifications, and proctoring event counts.
                  </p>
                </div>

                {/* Filter Controls */}
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search student..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500 w-44"
                    />
                  </div>

                  <select
                    value={riskFilter}
                    onChange={(e) => setRiskFilter(e.target.value)}
                    className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-semibold text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="ALL">All Risk Levels</option>
                    <option value="HIGH">High Risk</option>
                    <option value="MODERATE">Moderate Risk</option>
                    <option value="LOW">Low Risk</option>
                  </select>
                </div>
              </div>

              {/* Roster Table */}
              {integrityData.items.length === 0 ? (
                <div className="p-12 text-center text-slate-500 text-xs">
                  No student sessions match the selected integrity filters.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-semibold uppercase text-[10px]">
                        <th className="pb-3 px-3">Student</th>
                        <th className="pb-3 px-3">Session Status</th>
                        <th className="pb-3 px-3 text-center">Integrity Score</th>
                        <th className="pb-3 px-3">Risk Assessment</th>
                        <th className="pb-3 px-3 text-center">Tab Switches</th>
                        <th className="pb-3 px-3 text-center">Face Alerts</th>
                        <th className="pb-3 px-3 text-center">Total Signals</th>
                        <th className="pb-3 px-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {integrityData.items.map((item) => (
                        <tr key={item.session_id} className="hover:bg-slate-800/40 transition">
                          <td className="py-3 px-3">
                            <div className="font-semibold text-white">{item.student_name}</div>
                            <div className="text-[10px] text-slate-400 font-mono">{item.student_email}</div>
                          </td>
                          <td className="py-3 px-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                              {item.session_status}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-center font-mono font-bold text-white">
                            {item.integrity_score.toFixed(1)} <span className="text-[10px] text-slate-500">/ 100</span>
                          </td>
                          <td className="py-3 px-3">{getRiskBadge(item.risk_level)}</td>
                          <td className="py-3 px-3 text-center font-mono text-slate-300">
                            {item.tab_switches}
                          </td>
                          <td className="py-3 px-3 text-center font-mono text-slate-300">
                            {item.face_alerts}
                          </td>
                          <td className="py-3 px-3 text-center font-mono text-slate-300">
                            {item.total_signals}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <button
                              onClick={() => handleOpenDetail(item.session_id)}
                              className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition inline-flex items-center gap-1.5"
                            >
                              <Eye className="w-3.5 h-3.5" /> View Analysis
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* SESSION INTEGRITY DETAIL MODAL */}
      {selectedSessionId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full p-6 space-y-6 shadow-2xl my-8 relative max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-indigo-400" />
                  Session Integrity Assessment
                </h3>
                {sessionDetail && (
                  <p className="text-xs text-slate-400 mt-1">
                    Student: <span className="text-white font-semibold">{sessionDetail.student_name}</span> ({sessionDetail.student_email})
                  </p>
                )}
              </div>
              <button
                onClick={handleCloseDetail}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingDetail || !sessionDetail ? (
              <div className="py-16 text-center text-slate-400 text-xs flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <span>Extracting session signal timeline and scoring evidence...</span>
              </div>
            ) : (
              <div className="space-y-6">
                {/* 1. Overview & Score Card */}
                <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
                  {/* Score Indicator */}
                  <div className="space-y-2 text-center md:text-left">
                    <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                      Integrity Score
                    </span>
                    <div className="text-3xl font-extrabold text-white font-mono tracking-tight">
                      {sessionDetail.integrity_score.toFixed(1)} <span className="text-xs text-slate-500 font-sans">/ 100</span>
                    </div>
                    <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          sessionDetail.integrity_score >= 85
                            ? 'bg-emerald-500'
                            : sessionDetail.integrity_score >= 65
                            ? 'bg-amber-500'
                            : 'bg-rose-500'
                        }`}
                        style={{ width: `${sessionDetail.integrity_score}%` }}
                      />
                    </div>
                  </div>

                  {/* Risk Level */}
                  <div className="space-y-2 text-center md:text-left">
                    <span className="text-[10px] uppercase font-mono font-bold text-slate-400 block">
                      Risk Level
                    </span>
                    <div>{getRiskBadge(sessionDetail.risk_level)}</div>
                    <p className="text-[10px] text-slate-400">
                      Status: <span className="font-mono text-slate-300">{sessionDetail.session_status}</span>
                    </p>
                  </div>

                  {/* Signals Summary Counts */}
                  <div className="p-3 bg-slate-900 rounded-xl border border-slate-800/80 space-y-1.5 text-xs font-mono text-slate-300">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Tab Switches:</span>
                      <span className="text-white font-bold">{sessionDetail.signals_summary.tab_switches}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Face Alerts:</span>
                      <span className="text-white font-bold">{sessionDetail.signals_summary.face_alerts}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Fullscreen Exits:</span>
                      <span className="text-white font-bold">{sessionDetail.signals_summary.fullscreen_events}</span>
                    </div>
                  </div>
                </div>

                {/* Neutral Examiner Recommendation Banner */}
                <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-800/60 text-indigo-200 text-xs flex items-start gap-3">
                  <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold block text-white">Examiner Recommendation</span>
                    <p className="text-slate-300 mt-0.5">{sessionDetail.recommendation}</p>
                  </div>
                </div>

                {/* Student Identity Verification Card */}
                {(() => {
                  const idSum = sessionDetail.identity_summary || {};
                  const initialStatus = idSum.initial_status || 'UNVERIFIED';
                  const lastStatus = idSum.last_status || 'UNVERIFIED';
                  const mismatchEpisodes = idSum.mismatch_episodes ?? 0;
                  const confirmedMismatches = idSum.confirmed_mismatches ?? 0;

                  const getStatusBadge = (status: string) => {
                    switch (status) {
                      case 'VERIFIED':
                        return (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase bg-emerald-950/80 text-emerald-400 border border-emerald-500/30 inline-flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> VERIFIED
                          </span>
                        );
                      case 'TEMPORARILY_UNVERIFIED':
                        return (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase bg-amber-950/80 text-amber-400 border border-amber-500/30 inline-flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3" /> TEMPORARILY UNVERIFIED
                          </span>
                        );
                      case 'CONFIRMED_IDENTITY_MISMATCH':
                      case 'FAILED':
                        return (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase bg-rose-950/80 text-rose-400 border border-rose-500/30 inline-flex items-center gap-1">
                            <XCircle className="w-3 h-3" /> MISMATCH CONFIRMED
                          </span>
                        );
                      default:
                        return (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase bg-slate-800 text-slate-400 border border-slate-700">
                            {status}
                          </span>
                        );
                    }
                  };

                  return (
                    <div className="space-y-3">
                      <div className="flex flex-col gap-0.5">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                          <UserCheck className="w-4 h-4 text-indigo-400" />
                          Student Identity Verification
                        </h4>
                        <p className="text-[11px] text-slate-400 font-sans">
                          Facial landmark 3D geometric verification status against student template registration.
                        </p>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Initial Verification</span>
                          <div>{getStatusBadge(initialStatus)}</div>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Current/Final Status</span>
                          <div>{getStatusBadge(lastStatus)}</div>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block font-mono">Mismatch Episodes</span>
                          <span className="text-white font-bold">{mismatchEpisodes}</span>
                        </div>
                        <div className="space-y-1 font-mono">
                          <span className="text-[10px] text-slate-400 block">Confirmed Mismatches</span>
                          <span className={`font-bold ${confirmedMismatches > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {confirmedMismatches}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Observed Evidence Indicators */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    Observed Evidence Indicators
                  </h4>
                  {sessionDetail.evidence.length === 0 ? (
                    <div className="p-4 rounded-xl bg-slate-950 text-slate-400 text-xs text-center">
                      No significant integrity signals observed.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {sessionDetail.evidence.map((ev, idx) => (
                        <div
                          key={idx}
                          className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 relative"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white text-xs">{ev.title}</span>
                            {getSeverityBadge(ev.severity)}
                          </div>
                          <p className="text-xs text-slate-400 leading-relaxed">{ev.observation}</p>
                          {ev.score_deduction > 0 && (
                            <div className="text-[10px] font-mono text-rose-400 font-semibold">
                              Deduction: -{ev.score_deduction.toFixed(1)} pts
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Behavioural Intelligence Fingerprint */}
                {(() => {
                  const beh = sessionDetail.behavioural_summary || {};
                  const fmt = (val: any, suffix: string = '') => (val === null || val === undefined ? '—' : `${val}${suffix}`);
                  return (
                    <div className="space-y-3">
                      <div className="flex flex-col gap-0.5">
                        <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                          <Activity className="w-4 h-4 text-indigo-400" />
                          Behavioural Intelligence Fingerprint
                        </h4>
                        <p className="text-[11px] text-slate-400 font-sans">
                          Deterministic exam interaction behaviour summary based on navigation, timing, and answer-change patterns.
                        </p>
                      </div>
                      <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 grid grid-cols-2 sm:grid-cols-5 gap-4 text-xs font-mono">
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Questions Visited</span>
                          <span className="text-white font-bold">{fmt(beh.questions_visited)}</span>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Questions Answered</span>
                          <span className="text-white font-bold">{fmt(beh.questions_answered)}</span>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Answer Changes</span>
                          <span className="text-white font-bold">{fmt(beh.answer_change_count)}</span>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Answers Cleared</span>
                          <span className="text-white font-bold">{fmt(beh.clear_count)}</span>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Navigation Count</span>
                          <span className="text-white font-bold">{fmt(beh.navigation_count)}</span>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Backtracking Count</span>
                          <span className="text-white font-bold">{fmt(beh.backtrack_count)}</span>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Average Question Time</span>
                          <span className="text-white font-bold">{fmt(beh.average_question_time, 's')}</span>
                        </div>
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 block">Median Question Time</span>
                          <span className="text-white font-bold">{fmt(beh.median_question_time, 's')}</span>
                        </div>
                        <div className="space-y-1 font-mono">
                          <span className="text-[10px] text-slate-400 block">Rapid Change Clusters</span>
                          <span className="text-white font-bold">{fmt(beh.rapid_change_count)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* Chronological Session Timeline */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    Chronological Session Timeline
                  </h4>
                  {sessionDetail.timeline.length === 0 ? (
                    <div className="p-4 rounded-xl bg-slate-950 text-slate-400 text-xs text-center">
                      No timestamped events recorded during this session.
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4 max-h-64 overflow-y-auto">
                      {sessionDetail.timeline.map((item, idx) => (
                        <div key={idx} className="flex items-start gap-3 text-xs border-b border-slate-800/60 pb-3 last:border-0 last:pb-0">
                          <div className="text-[10px] font-mono text-slate-500 w-24 flex-shrink-0 pt-0.5">
                            {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'N/A'}
                          </div>
                          <div className="flex-1 space-y-0.5">
                            <div className="font-semibold text-slate-200 flex items-center justify-between">
                              <span>{item.label}</span>
                              {getSeverityBadge(item.severity)}
                            </div>
                            {item.details && <p className="text-[11px] text-slate-400">{item.details}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </AppShell>
  );
}
