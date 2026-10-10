'use client';

import React, { useState, useEffect } from 'react';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import {
  Users,
  ShieldCheck,
  Play,
  RotateCcw,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Info,
  Clock,
  FileText,
  Search,
  ChevronRight,
  X,
  Network,
} from 'lucide-react';
import {
  examsAPI,
  crossStudentAPI,
  Exam,
  PaginatedCrossStudentAnalysisResponse,
  CrossStudentPairSummaryItem,
  CrossStudentPairDetailResponse,
  CrossStudentClusterItem,
} from '@/lib/api';

export default function CrossStudentIntegrityPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<string>('');
  const [loadingExams, setLoadingExams] = useState(true);

  const [summaryData, setSummaryData] = useState<PaginatedCrossStudentAnalysisResponse | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Pagination & Filtering
  const [page, setPage] = useState(1);
  const [minSimFilter, setMinSimFilter] = useState<number | undefined>(undefined);
  const [selectedClusterFilter, setSelectedClusterFilter] = useState<string | undefined>(undefined);

  // Pair Detail Modal
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | null>(null);
  const [pairDetail, setPairDetail] = useState<CrossStudentPairDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // 1. Fetch Examiner's Exams
  useEffect(() => {
    const fetchExams = async () => {
      setLoadingExams(true);
      try {
        const res = await examsAPI.list({ page: 1, page_size: 100 });
        setExams(res.items);
        if (res.items.length > 0) {
          setSelectedExamId(res.items[0].id);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to load examinations list.');
      } finally {
        setLoadingExams(false);
      }
    };

    fetchExams();
  }, []);

  // 2. Fetch Cross-Student Analysis Summary when selected exam changes
  const fetchSummary = async (examId: string, p: number = 1) => {
    if (!examId) return;
    setLoadingSummary(true);
    setError(null);
    try {
      const data = await crossStudentAPI.getSummary(examId, {
        page: p,
        page_size: 10,
        min_similarity: minSimFilter,
        cluster_id: selectedClusterFilter,
      });
      setSummaryData(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load cross-student analysis.');
    } finally {
      setLoadingSummary(false);
    }
  };

  useEffect(() => {
    if (selectedExamId) {
      setPage(1);
      fetchSummary(selectedExamId, 1);
    }
  }, [selectedExamId, minSimFilter, selectedClusterFilter]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    if (selectedExamId) {
      fetchSummary(selectedExamId, newPage);
    }
  };

  // 3. Trigger Analysis Run
  const handleRunAnalysis = async () => {
    if (!selectedExamId) return;
    setRunningAnalysis(true);
    setError(null);
    setNotice(null);
    try {
      const res = await crossStudentAPI.runAnalysis(selectedExamId);
      setNotice(res.message);
      await fetchSummary(selectedExamId, 1);
    } catch (err: any) {
      setError(err?.message || 'Failed to execute cross-student analysis.');
    } finally {
      setRunningAnalysis(false);
    }
  };

  // 4. Open Pair Detail Modal
  const handleOpenPairDetail = async (analysisId: string) => {
    if (!selectedExamId) return;
    setSelectedAnalysisId(analysisId);
    setLoadingDetail(true);
    setPairDetail(null);
    try {
      const data = await crossStudentAPI.getPairDetail(selectedExamId, analysisId);
      setPairDetail(data);
    } catch (err: any) {
      console.warn('Failed to load pair detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleClosePairDetail = () => {
    setSelectedAnalysisId(null);
    setPairDetail(null);
  };

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case 'HIGH_SIMILARITY':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider bg-rose-950/80 text-rose-300 border border-rose-800/80 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> High Similarity
          </span>
        );
      case 'MODERATE_SIMILARITY':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider bg-amber-950/80 text-amber-300 border border-amber-800/80 flex items-center gap-1">
            <Info className="w-3 h-3" /> Moderate Similarity
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Low Similarity
          </span>
        );
    }
  };

  return (
    <AppShell title="Cross-Student Integrity" allowedRoles={['EXAMINER', 'ADMIN']}>
      <div className="max-w-6xl mx-auto space-y-6 pb-16">
        <PageHeader
          title="Cross-Student Integrity Analysis 👥"
          subtitle="Compare behavioural and answer similarity patterns across students who attempted the same examination."
        />

        {/* Exam Selection & Action Control Bar */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 shadow-xl">
          <div className="flex-1 max-w-md">
            <label className="text-[10px] font-mono font-bold uppercase text-slate-400 block mb-1.5">
              Select Examination
            </label>
            {loadingExams ? (
              <div className="text-xs text-slate-500 font-mono">Loading exams list...</div>
            ) : (
              <select
                value={selectedExamId}
                onChange={(e) => setSelectedExamId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                {exams.map((ex) => (
                  <option key={ex.id} value={ex.id}>
                    {ex.title} ({ex.subject})
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="flex items-center gap-3 self-end sm:self-center">
            {summaryData?.last_analyzed_at && (
              <span className="text-[11px] text-slate-400 font-mono hidden md:inline-block">
                Last analyzed:{' '}
                <span className="text-slate-200">
                  {new Date(summaryData.last_analyzed_at).toLocaleString()}
                </span>
              </span>
            )}

            <button
              onClick={handleRunAnalysis}
              disabled={runningAnalysis || !selectedExamId}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50"
            >
              {runningAnalysis ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Analyzing Sessions...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" /> Run Cross-Student Analysis
                </>
              )}
            </button>
          </div>
        </div>

        {notice && (
          <div className="p-4 bg-emerald-950/60 border border-emerald-800 text-emerald-300 rounded-2xl text-xs flex items-center gap-2 shadow-lg">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{notice}</span>
          </div>
        )}

        {error && (
          <div className="p-4 bg-rose-950/60 border border-rose-800 text-rose-300 rounded-2xl text-xs flex items-center gap-2 shadow-lg">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Summary Stat Cards */}
        {summaryData && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl space-y-1 shadow-lg">
              <span className="text-[10px] font-mono uppercase text-slate-400">Students Analyzed</span>
              <p className="text-2xl font-bold text-white tracking-tight">
                {summaryData.analyzed_students_count}
              </p>
            </div>

            <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl space-y-1 shadow-lg">
              <span className="text-[10px] font-mono uppercase text-slate-400">Evaluated Pairs</span>
              <p className="text-2xl font-bold text-indigo-400 tracking-tight">
                {summaryData.total_pairs_count}
              </p>
            </div>

            <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl space-y-1 shadow-lg">
              <span className="text-[10px] font-mono uppercase text-slate-400">High Similarity Pairs</span>
              <p className="text-2xl font-bold text-rose-400 tracking-tight">
                {summaryData.high_similarity_pairs_count}
              </p>
            </div>

            <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl space-y-1 shadow-lg">
              <span className="text-[10px] font-mono uppercase text-slate-400">Candidate Clusters</span>
              <p className="text-2xl font-bold text-amber-400 tracking-tight">
                {summaryData.clusters.length}
              </p>
            </div>
          </div>
        )}

        {/* CANDIDATE SIMILARITY CLUSTERS SECTION */}
        {summaryData && summaryData.clusters.length > 0 && (
          <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <Network className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
                  High Similarity Clusters
                </h3>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">
                Threshold: &ge; 70% Pairwise Similarity
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {summaryData.clusters.map((cluster: CrossStudentClusterItem) => (
                <div
                  key={cluster.cluster_id}
                  className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                    <span className="text-xs font-bold text-amber-300 font-mono">
                      {cluster.cluster_id} ({cluster.student_count} Students)
                    </span>
                    <span className="px-2.5 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">
                      Avg Similarity: {cluster.average_similarity}%
                    </span>
                  </div>

                  {/* Student List */}
                  <div className="space-y-1 text-xs">
                    <span className="text-[10px] font-mono text-slate-500 block">Members:</span>
                    <div className="flex flex-wrap gap-1.5">
                      {cluster.students.map((st) => (
                        <span
                          key={st.student_id}
                          className="px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-200 text-[11px] font-semibold"
                        >
                          {st.student_name}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Key Evidence */}
                  {cluster.key_evidence.length > 0 && (
                    <div className="space-y-1 text-[11px] text-slate-400 pt-1">
                      <span className="text-[10px] font-mono text-slate-500 block">Evidence Summary:</span>
                      <ul className="list-disc list-inside space-y-0.5">
                        {cluster.key_evidence.map((ev, idx) => (
                          <li key={idx} className="line-clamp-1">{ev}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <button
                    onClick={() => setSelectedClusterFilter(cluster.cluster_id)}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold underline pt-1 block"
                  >
                    Filter Pairwise Table by {cluster.cluster_id} &rarr;
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* PAIRWISE SIMILARITY TABLE */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-950/60">
            <h3 className="text-xs font-bold text-white font-mono uppercase tracking-wider">
              Pairwise Session Similarity Assessments
            </h3>

            {selectedClusterFilter && (
              <button
                onClick={() => setSelectedClusterFilter(undefined)}
                className="text-[11px] text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-1 self-start sm:self-center"
              >
                Clear Cluster Filter ({selectedClusterFilter}) <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {loadingSummary ? (
            <div className="p-12 text-center text-slate-500 font-mono text-xs">
              Loading pairwise analysis results...
            </div>
          ) : !summaryData || summaryData.items.length === 0 ? (
            <div className="p-12 text-center text-slate-500 space-y-3">
              <Users className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-xs">
                {summaryData?.total_pairs_count === 0
                  ? 'Not enough student attempts for cross-student analysis.'
                  : 'No pairwise results matching selected criteria.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Student A</th>
                    <th className="py-3 px-4">Student B</th>
                    <th className="py-3 px-4">Overall Score</th>
                    <th className="py-3 px-4">Answer Sim</th>
                    <th className="py-3 px-4">Same Wrong</th>
                    <th className="py-3 px-4">Timing Sim</th>
                    <th className="py-3 px-4">Assessment</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {summaryData.items.map((pair: CrossStudentPairSummaryItem) => (
                    <tr key={pair.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">{pair.source_student_name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{pair.source_student_email}</div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">{pair.target_student_name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{pair.target_student_email}</div>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold text-indigo-300">
                        {pair.similarity_score}%
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {pair.answer_similarity}%
                      </td>
                      <td className="py-3.5 px-4 font-mono">
                        {pair.same_incorrect_answers_count > 0 ? (
                          <span className="text-rose-400 font-bold bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800">
                            {pair.same_incorrect_answers_count} questions
                          </span>
                        ) : (
                          <span className="text-slate-500">0</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-400">
                        {pair.timing_similarity !== null ? `${pair.timing_similarity}%` : 'N/A'}
                      </td>
                      <td className="py-3.5 px-4">{getCategoryBadge(pair.category)}</td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => handleOpenPairDetail(pair.id)}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs font-semibold rounded-xl transition inline-flex items-center gap-1"
                        >
                          View Evidence <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer */}
          {summaryData && summaryData.pages > 1 && (
            <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-between items-center text-xs">
              <span className="text-slate-400">
                Page {summaryData.page} of {summaryData.pages}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 1}
                  onClick={() => handlePageChange(page - 1)}
                  className="px-3 py-1 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg hover:bg-slate-800 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={page === summaryData.pages}
                  onClick={() => handlePageChange(page + 1)}
                  className="px-3 py-1 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg hover:bg-slate-800 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* DETAILED EVIDENCE MODAL */}
        {selectedAnalysisId && (
          <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 space-y-6 shadow-2xl relative max-h-[92vh] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                    <Users className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">Cross-Student Evidence Detail</h3>
                    <p className="text-xs text-slate-400 font-mono">
                      {pairDetail ? pairDetail.exam_title : 'Loading pair evidence...'}
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleClosePairDetail}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {loadingDetail || !pairDetail ? (
                <div className="p-12 text-center text-slate-500 font-mono text-xs">
                  Loading detailed pair evidence breakdown...
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Students Comparison Banner */}
                  <div className="grid grid-cols-2 gap-4 p-4 bg-slate-950 border border-slate-800 rounded-xl">
                    <div className="space-y-1">
                      <span className="text-[10px] font-mono text-slate-400 uppercase">Student A</span>
                      <p className="text-sm font-bold text-white">{pairDetail.source_student_name}</p>
                      <p className="text-xs text-slate-400 font-mono">{pairDetail.source_student_email}</p>
                    </div>

                    <div className="space-y-1 border-l border-slate-800 pl-4">
                      <span className="text-[10px] font-mono text-slate-400 uppercase">Student B</span>
                      <p className="text-sm font-bold text-white">{pairDetail.target_student_name}</p>
                      <p className="text-xs text-slate-400 font-mono">{pairDetail.target_student_email}</p>
                    </div>
                  </div>

                  {/* Similarity Metrics Overview */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1 text-center">
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">Overall Similarity</span>
                      <span className="text-lg font-bold text-indigo-400 font-mono">
                        {pairDetail.similarity_score}%
                      </span>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1 text-center">
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">Answer Similarity</span>
                      <span className="text-lg font-bold text-slate-200 font-mono">
                        {pairDetail.answer_similarity}%
                      </span>
                    </div>

                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1 text-center">
                      <span className="text-[10px] font-mono text-slate-400 uppercase block">Same Wrong Answers</span>
                      <span className="text-lg font-bold text-rose-400 font-mono">
                        {pairDetail.same_incorrect_answers_count}
                      </span>
                    </div>
                  </div>

                  {/* Explainable Evidence List */}
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3">
                    <span className="text-xs font-bold text-white font-mono uppercase block">
                      Observational Evidence Items
                    </span>
                    <ul className="list-disc list-inside space-y-1.5 text-xs text-slate-300">
                      {pairDetail.evidence_items.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Common Wrong Answers Table */}
                  {pairDetail.common_wrong_answers.length > 0 && (
                    <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3">
                      <span className="text-xs font-bold text-rose-300 font-mono uppercase block">
                        Same Incorrect Option Selections ({pairDetail.common_wrong_answers.length})
                      </span>
                      <div className="space-y-2 text-xs">
                        {pairDetail.common_wrong_answers.map((wa) => (
                          <div key={wa.question_id} className="p-3 bg-slate-900 border border-slate-800 rounded-lg space-y-1">
                            <span className="font-semibold text-white">
                              Question #{wa.question_number}: {wa.question_text}
                            </span>
                            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
                              <span className="text-rose-300">
                                Both Selected: <strong>{wa.student_a_option}</strong>
                              </span>
                              <span className="text-emerald-400">
                                Correct Answer: <strong>{wa.correct_option}</strong>
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Subjective Text Similarity */}
                  {pairDetail.text_matches.length > 0 && (
                    <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-3">
                      <span className="text-xs font-bold text-indigo-300 font-mono uppercase block">
                        Subjective Answer Text Similarity ({pairDetail.text_matches.length})
                      </span>
                      <div className="space-y-3 text-xs">
                        {pairDetail.text_matches.map((tm) => (
                          <div key={tm.question_id} className="p-3 bg-slate-900 border border-slate-800 rounded-lg space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-white">
                                Question #{tm.question_number}: {tm.question_text}
                              </span>
                              <span className="text-indigo-400 font-mono font-bold">{tm.similarity_score}% Match</span>
                            </div>
                            <div className="grid grid-cols-2 gap-2 text-[11px]">
                              <div className="p-2 bg-slate-950 rounded border border-slate-800">
                                <span className="text-[10px] font-mono text-slate-500 block mb-1">Student A Response:</span>
                                <p className="text-slate-300 italic">{tm.student_a_text}</p>
                              </div>
                              <div className="p-2 bg-slate-950 rounded border border-slate-800">
                                <span className="text-[10px] font-mono text-slate-500 block mb-1">Student B Response:</span>
                                <p className="text-slate-300 italic">{tm.student_b_text}</p>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Disclaimer Footer */}
                  <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-xl text-[11px] text-slate-400 leading-relaxed flex items-start gap-2">
                    <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                    <span>
                      Similarity evidence is informational and should be reviewed alongside the complete examination record.
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
