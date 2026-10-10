'use client';

import React, { useState, useEffect } from 'react';
import PageHeader from '@/components/layout/PageHeader';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Layers,
  Activity,
  Smartphone,
  Laptop,
  Users,
  Eye,
  X,
  Loader2,
  RefreshCw,
  BookOpen,
  Calendar,
  AlertCircle,
  TrendingUp,
  Sliders,
  ChevronRight,
  Info,
} from 'lucide-react';
import {
  User,
  studentIntegrityAPI,
  StudentIntegrityOverviewResponse,
  StudentExamIntegrityItem,
  StudentSessionIntegrityDetailResponse,
} from '@/lib/api';

interface StudentIntegrityViewProps {
  user: User;
}

export default function StudentIntegrityView({ user }: StudentIntegrityViewProps) {
  const [data, setData] = useState<StudentIntegrityOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal State
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionDetail, setSessionDetail] = useState<StudentSessionIntegrityDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await studentIntegrityAPI.getOverview();
      setData(resp);
    } catch (err: any) {
      setError(err?.message || 'Failed to load integrity overview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const handleOpenDetail = async (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const detail = await studentIntegrityAPI.getSessionDetail(sessionId);
      setSessionDetail(detail);
    } catch (err: any) {
      setDetailError(err?.message || 'Failed to load session integrity details.');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedSessionId(null);
    setSessionDetail(null);
    setDetailError(null);
  };

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

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-rose-950 text-rose-400 border border-rose-800">
            {severity}
          </span>
        );
      case 'WARNING':
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-amber-950 text-amber-400 border border-amber-800">
            {severity}
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-800 text-slate-400 border border-slate-700">
            {severity}
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 pb-16">
      <PageHeader
        title="Integrity Status"
        subtitle="Review your examination integrity and proctoring history."
      />

      {/* ERROR STATE */}
      {error && (
        <div className="p-4 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-2xl flex items-center justify-between shadow-xl">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchOverview}
            className="px-3 py-1.5 bg-rose-900/60 hover:bg-rose-900 text-rose-200 font-semibold rounded-xl text-xs transition flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry
          </button>
        </div>
      )}

      {/* LOADING STATE */}
      {loading && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-28 bg-slate-900/60 border border-slate-800 rounded-2xl animate-pulse" />
            ))}
          </div>
          <div className="h-64 bg-slate-900/60 border border-slate-800 rounded-2xl animate-pulse" />
        </div>
      )}

      {/* SUMMARY CARDS */}
      {!loading && data && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {/* Exams Monitored */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-2 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="font-semibold">Exams Monitored</span>
              <BookOpen className="w-4 h-4 text-indigo-400" />
            </div>
            <p className="text-2xl font-bold text-white tracking-tight">{data.summary.exams_monitored}</p>
            <p className="text-[11px] text-slate-500 font-mono">
              {data.summary.exams_completed} completed
            </p>
          </div>

          {/* Average Integrity Score */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-2 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="font-semibold">Average Integrity</span>
              <TrendingUp className="w-4 h-4 text-indigo-400" />
            </div>
            <p className="text-2xl font-bold text-white tracking-tight">
              {data.summary.average_integrity_score}
              <span className="text-sm text-slate-500 font-normal">/100</span>
            </p>
            <p className="text-[11px] text-emerald-400 font-mono">Platform Baseline</p>
          </div>

          {/* Low Risk */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-2 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="font-semibold text-emerald-300">Low Risk</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-emerald-400 tracking-tight">{data.summary.low_risk_count}</p>
            <p className="text-[11px] text-slate-500 font-mono">Standard compliance</p>
          </div>

          {/* Moderate Risk */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-2 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="font-semibold text-amber-300">Moderate Risk</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-2xl font-bold text-amber-400 tracking-tight">{data.summary.moderate_risk_count}</p>
            <p className="text-[11px] text-slate-500 font-mono">Minor signals</p>
          </div>

          {/* High Risk */}
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl space-y-2 shadow-xl">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span className="font-semibold text-rose-300">High Risk</span>
              <ShieldAlert className="w-4 h-4 text-rose-400" />
            </div>
            <p className="text-2xl font-bold text-rose-400 tracking-tight">{data.summary.high_risk_count}</p>
            <p className="text-[11px] text-slate-500 font-mono">Multiple signals</p>
          </div>
        </div>
      )}

      {/* EXAM INTEGRITY HISTORY */}
      {!loading && data && (
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-6 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white tracking-tight">Exam Integrity History</h3>
                <p className="text-xs text-slate-400">
                  Record of monitored examinations and assessment summaries.
                </p>
              </div>
            </div>
          </div>

          {data.exams.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <ShieldCheck className="w-12 h-12 text-slate-600 mx-auto" />
              <p className="text-sm font-semibold text-slate-300">No Monitored Examinations Yet</p>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Once you participate in proctored examinations, your session integrity scores and proctoring summaries will be displayed here.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                    <th className="pb-3 font-semibold">Examination</th>
                    <th className="pb-3 font-semibold">Date</th>
                    <th className="pb-3 font-semibold">Status</th>
                    <th className="pb-3 font-semibold text-center">Score</th>
                    <th className="pb-3 font-semibold">Risk Level</th>
                    <th className="pb-3 font-semibold text-center">Events</th>
                    <th className="pb-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {data.exams.map((exam) => (
                    <tr key={exam.session_id} className="hover:bg-slate-800/30 transition">
                      <td className="py-4 pr-4">
                        <p className="font-bold text-white text-xs">{exam.exam_title}</p>
                        <p className="text-[10px] text-slate-500 font-mono mt-0.5">
                          Session: {exam.session_id.slice(0, 8)}...
                        </p>
                      </td>
                      <td className="py-4 pr-4 text-slate-300 font-mono text-[11px]">
                        {exam.started_at ? new Date(exam.started_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="py-4 pr-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                          {exam.status}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center font-bold text-sm text-slate-200">
                        {exam.integrity_score.toFixed(1)}
                      </td>
                      <td className="py-4 pr-4">{getRiskBadge(exam.risk_level)}</td>
                      <td className="py-4 px-4 text-center font-mono text-slate-400">
                        {exam.event_count}
                      </td>
                      <td className="py-4 pl-4 text-right">
                        <button
                          onClick={() => handleOpenDetail(exam.session_id)}
                          className="px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 font-semibold text-xs transition inline-flex items-center gap-1"
                        >
                          View Details
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* DETAIL MODAL */}
      {selectedSessionId && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 space-y-6 shadow-2xl relative max-h-[92vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight">
                    {sessionDetail ? sessionDetail.exam_title : 'Session Integrity Details'}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Comprehensive multi-signal proctoring and behavioral assessment.
                  </p>
                </div>
              </div>
              <button
                onClick={handleCloseDetail}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingDetail && (
              <div className="p-12 text-center space-y-3">
                <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Loading session integrity assessment...</p>
              </div>
            )}

            {detailError && (
              <div className="p-4 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{detailError}</span>
              </div>
            )}

            {!loadingDetail && sessionDetail && (
              <div className="space-y-6">
                {/* Score & Risk Overview Banner */}
                <div className="p-5 bg-slate-950 border border-slate-800 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Assessment Score</span>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-extrabold text-white">
                        {sessionDetail.integrity_score.toFixed(1)}
                      </span>
                      <span className="text-sm font-semibold text-slate-500">/ 100</span>
                    </div>
                  </div>

                  <div className="space-y-1 sm:text-right">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Assigned Risk</span>
                    <div>{getRiskBadge(sessionDetail.risk_level)}</div>
                  </div>
                </div>

                {/* Neutral Status Explanation */}
                <div className="p-4 bg-indigo-950/30 border border-indigo-800/40 rounded-xl text-xs text-indigo-200 flex items-start gap-3">
                  <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <p className="leading-relaxed">{sessionDetail.status_explanation}</p>
                </div>

                {/* Event Category Breakdown Badges */}
                <div className="space-y-2">
                  <span className="text-xs font-bold text-slate-200">Event Summary</span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Tab Switches</span>
                      <p className="text-lg font-bold text-slate-200">{sessionDetail.event_summary.tab_switches || 0}</p>
                    </div>
                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Fullscreen Exits</span>
                      <p className="text-lg font-bold text-slate-200">{sessionDetail.event_summary.fullscreen_exits || 0}</p>
                    </div>
                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Face Absence</span>
                      <p className="text-lg font-bold text-slate-200">{sessionDetail.event_summary.face_absence || 0}</p>
                    </div>
                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Multiple Faces</span>
                      <p className="text-lg font-bold text-slate-200">{sessionDetail.event_summary.multiple_faces || 0}</p>
                    </div>
                  </div>
                </div>

                {/* Event Timeline */}
                <div className="space-y-3">
                  <span className="text-xs font-bold text-slate-200">Monitoring Events</span>
                  {sessionDetail.events.length === 0 ? (
                    <div className="p-4 bg-slate-950 border border-slate-800/80 rounded-xl text-center text-xs text-slate-400">
                      No proctoring anomalies or integrity events were recorded during this session.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                      {sessionDetail.events.map((ev, idx) => (
                        <div
                          key={idx}
                          className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl flex items-start justify-between gap-3 text-xs"
                        >
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-semibold text-slate-200">{ev.title}</span>
                              {getSeverityBadge(ev.severity)}
                            </div>
                            <p className="text-[11px] text-slate-400">{ev.description}</p>
                          </div>
                          {ev.occurred_at && (
                            <span className="text-[10px] font-mono text-slate-500 shrink-0">
                              {new Date(ev.occurred_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Behavioural Metrics */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-slate-200">Behavioural Summary</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Questions Visited</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.questions_visited !== null
                          ? sessionDetail.behavioural_metrics.questions_visited
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Questions Answered</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.questions_answered !== null
                          ? sessionDetail.behavioural_metrics.questions_answered
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Answer Changes</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.answer_changes !== null
                          ? sessionDetail.behavioural_metrics.answer_changes
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Answers Cleared</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.answers_cleared !== null
                          ? sessionDetail.behavioural_metrics.answers_cleared
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Navigation Count</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.navigation_count !== null
                          ? sessionDetail.behavioural_metrics.navigation_count
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Backtracking Count</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.backtracking_count !== null
                          ? sessionDetail.behavioural_metrics.backtracking_count
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Average Question Time</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.avg_question_time !== null
                          ? `${sessionDetail.behavioural_metrics.avg_question_time}s`
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Median Question Time</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.median_question_time !== null
                          ? `${sessionDetail.behavioural_metrics.median_question_time}s`
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                      <span className="text-[10px] text-slate-400">Rapid Change Clusters</span>
                      <p className="font-semibold text-slate-200">
                        {sessionDetail.behavioural_metrics.metrics_available && sessionDetail.behavioural_metrics.rapid_change_clusters !== null
                          ? sessionDetail.behavioural_metrics.rapid_change_clusters
                          : 'Not available'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Environment Monitoring */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Laptop className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-slate-200">Environment Monitoring</span>
                  </div>
                  <div className="p-4 bg-slate-950 border border-slate-800/80 rounded-xl space-y-3 text-xs">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="space-y-0.5">
                        <span className="text-[10px] text-slate-400">Phone Detected</span>
                        <p className="font-semibold text-slate-200">{sessionDetail.environment_monitoring.phone_detected_count}</p>
                      </div>
                      <div className="space-y-0.5">
                        <span className="text-[10px] text-slate-400">Laptop / Display</span>
                        <p className="font-semibold text-slate-200">{sessionDetail.environment_monitoring.laptop_detected_count}</p>
                      </div>
                      <div className="space-y-0.5">
                        <span className="text-[10px] text-slate-400">Study Material</span>
                        <p className="font-semibold text-slate-200">{sessionDetail.environment_monitoring.book_detected_count}</p>
                      </div>
                      <div className="space-y-0.5">
                        <span className="text-[10px] text-slate-400">Additional Person</span>
                        <p className="font-semibold text-slate-200">{sessionDetail.environment_monitoring.additional_person_count}</p>
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-800/60 leading-relaxed">
                      {sessionDetail.environment_monitoring.explanation}
                    </p>
                  </div>
                </div>

                {/* Close Button */}
                <div className="flex justify-end pt-2 border-t border-slate-800">
                  <button
                    onClick={handleCloseDetail}
                    className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
