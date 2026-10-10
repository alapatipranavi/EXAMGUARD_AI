'use client';

import React, { useEffect, useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import {
  Award,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  ChevronRight,
  BarChart3,
  AlertCircle,
  TrendingUp,
  Save,
  CheckSquare,
  Lock,
  UserCheck,
} from 'lucide-react';
import {
  resultsAPI,
  StudentResultResponse,
  QuestionEvaluationDetail,
  authAPI,
  User,
} from '@/lib/api';

export default function ResultsPage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [results, setResults] = useState<StudentResultResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [detailModalResult, setDetailModalResult] = useState<StudentResultResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Examiner Review Form State per Answer ID
  const [reviewScores, setReviewScores] = useState<{ [answerId: string]: number }>({});
  const [reviewComments, setReviewComments] = useState<{ [answerId: string]: string }>({});
  const [submittingAnswerId, setSubmittingAnswerId] = useState<string | null>(null);

  // In-App Finalize Confirmation Modal State
  const [confirmFinalizeTarget, setConfirmFinalizeTarget] = useState<{
    q: QuestionEvaluationDetail;
    score: number;
    comment: string;
  } | null>(null);

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    authAPI
      .getMe()
      .then((u) => {
        setCurrentUser(u);
        fetchResults(u.role, search, 1);
      })
      .catch(() => {
        setCurrentUser(null);
      });
  }, []);

  const fetchResults = async (userRole: string, searchQuery: string, pageNum: number) => {
    setLoading(true);
    setError(null);
    try {
      let data;
      if (userRole === 'STUDENT') {
        data = await resultsAPI.getStudentResults({ page: pageNum, page_size: 10, search: searchQuery });
      } else {
        data = await resultsAPI.getAllResults({ page: pageNum, page_size: 10, search: searchQuery });
      }
      setResults(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err: any) {
      setError(err.message || 'Failed to load exam results.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    if (currentUser) {
      fetchResults(currentUser.role, search, 1);
    }
  };

  const handleOpenDetail = async (resItem: StudentResultResponse) => {
    setSelectedSessionId(resItem.session_id);
    setLoadingDetail(true);
    setError(null);
    try {
      let detail: StudentResultResponse;
      if (currentUser?.role === 'STUDENT') {
        detail = await resultsAPI.getStudentResultDetail(resItem.session_id);
      } else {
        detail = await resultsAPI.getExaminerResultDetail(resItem.exam_id, resItem.session_id);
      }
      setDetailModalResult(detail);

      // Pre-fill score & comment inputs
      const initialScores: { [ansId: string]: number } = {};
      const initialComments: { [ansId: string]: string } = {};
      detail.question_evaluations?.forEach((q) => {
        if (q.answer_id) {
          const defaultScore =
            q.earned_score !== undefined && q.earned_score !== null && q.earned_score > 0
              ? q.earned_score
              : q.suggested_score !== undefined && q.suggested_score !== null
              ? q.suggested_score
              : 0;
          initialScores[q.answer_id] = defaultScore;
          initialComments[q.answer_id] = q.examiner_comment || '';
        }
      });
      setReviewScores(initialScores);
      setReviewComments(initialComments);
    } catch (err: any) {
      console.error('Failed to load result detail:', err);
      setError(err.message || 'Failed to load evaluation details.');
      setSelectedSessionId(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseDetail = () => {
    setSelectedSessionId(null);
    setDetailModalResult(null);
    setReviewScores({});
    setReviewComments({});
  };

  const handleScoreChange = (answerId: string, value: string, maxMarks: number) => {
    const numeric = parseFloat(value);
    setReviewScores((prev) => ({
      ...prev,
      [answerId]: isNaN(numeric) ? 0 : numeric,
    }));
  };

  const handleCommentChange = (answerId: string, value: string) => {
    setReviewComments((prev) => ({
      ...prev,
      [answerId]: value,
    }));
  };

  const executeSubmitReview = async (
    q: QuestionEvaluationDetail,
    isFinalized: boolean,
    customScore?: number,
    customComment?: string
  ) => {
    if (!detailModalResult || !q.answer_id) return;

    const defaultScore =
      q.earned_score !== undefined && q.earned_score !== null && q.earned_score > 0
        ? q.earned_score
        : q.suggested_score !== undefined && q.suggested_score !== null
        ? q.suggested_score
        : 0;

    const finalScore = customScore !== undefined ? customScore : (reviewScores[q.answer_id] ?? defaultScore);
    const comment = customComment !== undefined ? customComment : (reviewComments[q.answer_id] ?? q.examiner_comment ?? '');

    // Frontend Score Bounds Validation
    if (isNaN(finalScore) || finalScore < 0 || finalScore > q.marks) {
      setToastMessage({
        type: 'error',
        text: `Score must be a valid number between 0 and ${q.marks}.`,
      });
      return;
    }

    setSubmittingAnswerId(q.answer_id);
    setToastMessage(null);

    try {
      let updatedDetail: StudentResultResponse;
      if (isFinalized) {
        updatedDetail = await resultsAPI.finalizeSubjectiveAnswer(
          detailModalResult.exam_id,
          detailModalResult.session_id,
          q.answer_id,
          { final_score: finalScore, comment }
        );
      } else {
        updatedDetail = await resultsAPI.reviewSubjectiveAnswer(
          detailModalResult.exam_id,
          detailModalResult.session_id,
          q.answer_id,
          { final_score: finalScore, comment, is_finalized: false }
        );
      }

      setDetailModalResult(updatedDetail);

      // Update inputs with newly saved scores
      setReviewScores((prev) => ({
        ...prev,
        [q.answer_id!]: finalScore,
      }));
      setReviewComments((prev) => ({
        ...prev,
        [q.answer_id!]: comment,
      }));

      // Refresh list results
      if (currentUser) {
        fetchResults(currentUser.role, search, page);
      }

      setToastMessage({
        type: 'success',
        text: isFinalized
          ? 'Subjective evaluation finalized successfully!'
          : 'Review saved successfully.',
      });
    } catch (err: any) {
      console.error('Failed to submit evaluation review:', err);
      setToastMessage({
        type: 'error',
        text: err.message || 'Failed to update evaluation review.',
      });
    } finally {
      setSubmittingAnswerId(null);
      setConfirmFinalizeTarget(null);
    }
  };

  const isStudent = currentUser?.role === 'STUDENT';
  const isExaminer = currentUser?.role === 'EXAMINER' || currentUser?.role === 'ADMIN' || !isStudent;

  // Aggregate stats
  const totalSubmissions = total;
  const passedCount = results.filter((r) => r.pass_fail_status === 'PASSED').length;
  const passRate = results.length > 0 ? Math.round((passedCount / results.length) * 100) : 0;
  const avgPercentage =
    results.length > 0
      ? Math.round(results.reduce((acc, r) => acc + r.percentage, 0) / results.length)
      : 0;

  return (
    <AppShell title="Exam Results">
      <div className="space-y-6 max-w-7xl mx-auto pb-12">
        {/* Header */}
        <PageHeader
          title={isStudent ? 'My Exam Results' : 'Exam Performance & Evaluation Results'}
          subtitle={
            isStudent
              ? 'View score breakdowns, percentages, pass/fail status, and question analytics for your submitted examinations.'
              : 'Track exam performance across all students, review objective scores, and perform manual evaluation for subjective answers.'
          }
          actions={
            <div className="flex items-center gap-2">
              <span className="text-xs px-3 py-1.5 rounded-full font-mono bg-slate-900 text-indigo-400 border border-indigo-500/30">
                Stage 8.3 Examiner Review
              </span>
            </div>
          }
        />

        {/* Toast Notification Banner */}
        {toastMessage && (
          <div
            className={`p-4 rounded-xl text-xs flex items-center justify-between gap-3 border transition ${
              toastMessage.type === 'success'
                ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-200'
                : 'bg-rose-950/60 border-rose-800/80 text-rose-200'
            }`}
          >
            <div className="flex items-center gap-2">
              {toastMessage.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              )}
              <span>{toastMessage.text}</span>
            </div>
            <button
              onClick={() => setToastMessage(null)}
              className="text-slate-400 hover:text-white text-xs font-bold"
            >
              ✕
            </button>
          </div>
        )}

        {/* Top Stat Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center gap-4">
            <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20 text-indigo-400">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">
                {isStudent ? 'Total Exams Taken' : 'Total Evaluated Sessions'}
              </p>
              <p className="text-2xl font-bold text-white mt-0.5">{totalSubmissions}</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Passed Exams</p>
              <p className="text-2xl font-bold text-white mt-0.5">{passedCount}</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center gap-4">
            <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20 text-amber-400">
              <TrendingUp className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Average Percentage</p>
              <p className="text-2xl font-bold text-white mt-0.5">{avgPercentage}%</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center gap-4">
            <div className="p-3 bg-purple-500/10 rounded-xl border border-purple-500/20 text-purple-400">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Pass Rate</p>
              <p className="text-2xl font-bold text-white mt-0.5">{passRate}%</p>
            </div>
          </div>
        </div>

        {/* Filter & Search Toolbar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <form onSubmit={handleSearchSubmit} className="relative flex-1 w-full sm:w-auto">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder={
                isStudent
                  ? 'Search by exam title or subject...'
                  : 'Search by student name, email, or exam...'
              }
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </form>
          <button
            type="button"
            onClick={() => {
              setPage(1);
              if (currentUser) fetchResults(currentUser.role, search, 1);
            }}
            className="w-full sm:w-auto px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition"
          >
            Search
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-3">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Results Table */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
          {loading ? (
            <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span>Loading exam evaluation results...</span>
            </div>
          ) : results.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center gap-3">
              <Award className="w-10 h-10 text-slate-600" />
              <p className="font-semibold text-slate-300 text-sm">No Evaluation Results Found</p>
              <p className="text-slate-500 max-w-md">
                {isStudent
                  ? 'You have not submitted any completed exams yet.'
                  : 'No student exam submissions match your filter.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 font-mono">
                    {!isStudent && <th className="py-3 px-4">Student</th>}
                    <th className="py-3 px-4">Exam Title</th>
                    <th className="py-3 px-4">Subject</th>
                    <th className="py-3 px-4">Submitted At</th>
                    <th className="py-3 px-4 text-center">Score</th>
                    <th className="py-3 px-4 text-center">Percentage</th>
                    <th className="py-3 px-4 text-center">Result</th>
                    <th className="py-3 px-4 text-center">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {results.map((res) => (
                    <tr
                      key={res.id}
                      className="hover:bg-slate-800/30 transition text-slate-300"
                    >
                      {!isStudent && (
                        <td className="py-3.5 px-4 font-medium text-white">
                          <div>{res.student_name}</div>
                          <div className="text-[10px] text-slate-500">{res.student_email}</div>
                        </td>
                      )}
                      <td className="py-3.5 px-4 font-semibold text-white">
                        {res.exam_title}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                          {res.exam_subject}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                        {res.submitted_at
                          ? new Date(res.submitted_at).toLocaleString()
                          : 'N/A'}
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold font-mono">
                        <span className="text-indigo-400">{res.total_score}</span> /{' '}
                        <span className="text-slate-400">{res.maximum_marks}</span>
                      </td>
                      <td className="py-3.5 px-4 text-center font-bold font-mono">
                        <span
                          className={
                            res.percentage >= 50 ? 'text-emerald-400' : 'text-rose-400'
                          }
                        >
                          {res.percentage}%
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {res.pass_fail_status === 'PASSED' ? (
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
                        {res.status === 'FINALIZED' || res.status === 'COMPLETED' ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                            {res.status === 'FINALIZED' ? 'Finalized' : 'Completed'}
                          </span>
                        ) : res.status === 'MANUAL_REVIEW' ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
                            Manual Review
                          </span>
                        ) : res.status === 'AI_EVALUATED' ? (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-purple-500/10 text-purple-400 border border-purple-500/30">
                            AI Evaluated
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
                            Pending Review
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <button
                          onClick={() => handleOpenDetail(res)}
                          className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 rounded-lg font-medium transition inline-flex items-center gap-1"
                        >
                          Details <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
              <span>
                Showing Page {page} of {totalPages} ({total} items)
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => {
                    const newPage = Math.max(1, page - 1);
                    setPage(newPage);
                    if (currentUser) fetchResults(currentUser.role, search, newPage);
                  }}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg disabled:opacity-50 transition"
                >
                  Previous
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => {
                    const newPage = Math.min(totalPages, page + 1);
                    setPage(newPage);
                    if (currentUser) fetchResults(currentUser.role, search, newPage);
                  }}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg disabled:opacity-50 transition"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Detailed Question Breakdown & Examiner Review Modal */}
        {selectedSessionId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
              <div className="p-4 sm:p-6 border-b border-slate-800 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-lg text-white">
                    {detailModalResult?.exam_title || 'Evaluation Breakdown'}
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Subject: {detailModalResult?.exam_subject} • Student: {detailModalResult?.student_name}
                  </p>
                </div>
                <button
                  onClick={handleCloseDetail}
                  className="p-1 text-slate-400 hover:text-white rounded-lg transition"
                >
                  ✕
                </button>
              </div>

              <div className="p-6 overflow-y-auto space-y-6">
                {/* Modal Toast Notification Banner */}
                {toastMessage && (
                  <div
                    className={`p-4 rounded-xl text-xs flex items-center justify-between gap-3 border transition ${
                      toastMessage.type === 'success'
                        ? 'bg-emerald-950/60 border-emerald-800/80 text-emerald-200'
                        : 'bg-rose-950/60 border-rose-800/80 text-rose-200'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {toastMessage.type === 'success' ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                      )}
                      <span>{toastMessage.text}</span>
                    </div>
                    <button
                      onClick={() => setToastMessage(null)}
                      className="text-slate-400 hover:text-white text-xs font-bold"
                    >
                      ✕
                    </button>
                  </div>
                )}

                {loadingDetail || !detailModalResult ? (
                  <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center gap-2">
                    <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <span>Loading detailed question breakdown...</span>
                  </div>
                ) : (
                  <>
                    {/* Session Score Summary Cards */}
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 bg-slate-950/80 p-4 rounded-xl border border-slate-800 text-xs">
                      <div>
                        <span className="text-slate-500 block">Total Score</span>
                        <span className="font-bold text-indigo-400 text-base font-mono">
                          {detailModalResult.total_score} / {detailModalResult.maximum_marks}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Objective Marks</span>
                        <span className="font-bold text-slate-300 text-base font-mono">
                          {detailModalResult.objective_marks}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Subjective Marks</span>
                        <span className="font-bold text-purple-400 text-base font-mono">
                          {detailModalResult.subjective_marks ?? 0}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Percentage</span>
                        <span className="font-bold text-white text-base font-mono">
                          {detailModalResult.percentage}%
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Result</span>
                        <span
                          className={`font-bold text-base ${
                            detailModalResult.pass_fail_status === 'PASSED'
                              ? 'text-emerald-400'
                              : 'text-rose-400'
                          }`}
                        >
                          {detailModalResult.pass_fail_status}
                        </span>
                      </div>
                    </div>

                    {/* Questions Breakdown List */}
                    <div className="space-y-6">
                      <h4 className="font-bold text-sm text-slate-200">
                        Per-Question Performance & Examiner Review
                      </h4>
                      {detailModalResult.question_evaluations?.map((q, idx) => {
                        const qTypeUpper = (q.question_type || '').toString().toUpperCase();
                        const isSubjective = ['SHORT_ANSWER', 'LONG_ANSWER', 'HANDWRITTEN'].includes(qTypeUpper);
                        const statusUpper = (q.status || '').toString().toUpperCase();
                        const isFinalized = statusUpper === 'FINALIZED';
                        const ansKey = q.answer_id || q.question_id;
                        const isSubmitting = ansKey ? submittingAnswerId === ansKey : false;
                        const keyPoints = q.matched_concepts?.key_points_covered || [];
                        const missingPoints = q.missed_concepts?.missing_key_points || [];

                        return (
                          <div
                            key={q.question_id || idx}
                            className="p-5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-4 text-xs"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="px-2.5 py-1 rounded text-[10px] font-mono bg-slate-800 text-slate-300 font-semibold">
                                  Q{idx + 1} • {q.question_type}
                                </span>

                                {/* Status Tag */}
                                {isFinalized ? (
                                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 inline-flex items-center gap-1">
                                    <Lock className="w-3 h-3" /> Finalized
                                  </span>
                                ) : statusUpper === 'MANUAL_REVIEW' ? (
                                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 inline-flex items-center gap-1">
                                    <UserCheck className="w-3 h-3" /> Manual Review
                                  </span>
                                ) : statusUpper === 'AI_EVALUATED' || q.evaluator_type === 'AI' ? (
                                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30">
                                    AI Evaluated
                                  </span>
                                ) : (
                                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                                    Pending Review
                                  </span>
                                )}

                                <span className="text-slate-400 font-mono text-[11px]">
                                  Max Marks: {q.marks}
                                </span>
                              </div>

                              {/* Earned Score Header Badge */}
                              <div className="font-bold font-mono text-sm">
                                {q.is_correct === true && (
                                  <span className="text-emerald-400 inline-flex items-center gap-1">
                                    <CheckCircle2 className="w-3.5 h-3.5" /> +{q.earned_score} / {q.marks}
                                  </span>
                                )}
                                {q.is_correct === false && (
                                  <span className="text-rose-400 inline-flex items-center gap-1">
                                    <XCircle className="w-3.5 h-3.5" /> {q.earned_score} / {q.marks}
                                  </span>
                                )}
                                {(q.is_correct === null || q.is_correct === undefined) && (
                                  <span className="text-amber-400 inline-flex items-center gap-1">
                                    <Clock className="w-3.5 h-3.5" /> {q.earned_score} / {q.marks}
                                  </span>
                                )}
                              </div>
                            </div>

                            <p className="font-semibold text-white text-sm">{q.question_text}</p>

                            {/* Render Student Text Answer for subjective questions */}
                            {isSubjective && (
                              <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-300">
                                <span className="text-[10px] uppercase tracking-wider text-indigo-400 font-mono font-bold block">
                                  Student Answer Text
                                </span>
                                <p className="whitespace-pre-wrap font-sans text-xs">
                                  {q.text_answer && q.text_answer.trim()
                                    ? q.text_answer
                                    : qTypeUpper === 'HANDWRITTEN'
                                    ? 'No handwritten text extracted or submission empty.'
                                    : '(No answer submitted)'}
                                </p>
                              </div>
                            )}

                            {/* Render Original Handwritten Submission Image & OCR Details */}
                            {qTypeUpper === 'HANDWRITTEN' && (
                              <div className="space-y-3 p-4 rounded-xl bg-slate-900/90 border border-slate-800">
                                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                                  <span className="text-xs font-bold text-white font-mono uppercase tracking-wider flex items-center gap-1.5">
                                    📷 Original Handwritten Submission Sheet
                                  </span>
                                  {q.ocr_status && (
                                    <span className="px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase bg-slate-950 text-indigo-300 border border-slate-800">
                                      OCR: {q.ocr_status} {q.ocr_confidence ? `(${Math.round(q.ocr_confidence * 100)}% Confidence)` : ''}
                                    </span>
                                  )}
                                </div>

                                {q.answer_image_url ? (
                                  <div className="relative border border-slate-800 rounded-lg overflow-hidden bg-slate-950 max-h-80 flex items-center justify-center p-2">
                                    <img
                                      src={
                                        q.answer_image_url.startsWith('data:') || q.answer_image_url.startsWith('http')
                                          ? q.answer_image_url
                                          : `http://localhost:8000${q.answer_image_url}`
                                      }
                                      alt="Handwritten Answer Sheet"
                                      className="max-h-72 object-contain rounded"
                                    />
                                  </div>
                                ) : (
                                  <p className="text-xs text-amber-400 italic">No handwritten image sheet submitted.</p>
                                )}

                                {q.text_answer && (
                                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-1">
                                    <span className="text-[10px] font-mono text-slate-400 uppercase block">OCR Extracted Text Output:</span>
                                    <p className="text-xs text-slate-200 font-mono whitespace-pre-wrap">{q.text_answer}</p>
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Render Model Answer / Rubric if present */}
                            {isSubjective && q.model_answer && (
                              <div className="space-y-1.5 p-3 rounded-lg bg-slate-900/40 border border-slate-800/60 text-slate-400">
                                <span className="text-[10px] uppercase tracking-wider text-emerald-400 font-mono font-bold block">
                                  Model Answer / Rubric
                                </span>
                                <p className="whitespace-pre-wrap font-sans text-xs">{q.model_answer}</p>
                              </div>
                            )}

                            {/* AI Evaluation Output (Preserved AI Suggested Score & Concepts) */}
                            {isSubjective && (q.suggested_score !== null || q.matched_concepts || q.justification || q.evaluator_type === 'AI') && (
                              <div className="p-3.5 rounded-lg bg-purple-950/20 border border-purple-900/40 space-y-2 text-xs">
                                <div className="flex items-center justify-between text-purple-300 font-mono text-[11px]">
                                  <span className="font-bold uppercase tracking-wider">AI Evaluation Reference</span>
                                  <span>
                                    Suggested Score:{' '}
                                    <strong className="text-purple-200">
                                      {q.suggested_score !== null && q.suggested_score !== undefined
                                        ? `${q.suggested_score} / ${q.marks}`
                                        : 'N/A'}
                                    </strong>
                                  </span>
                                </div>

                                {keyPoints.length > 0 && (
                                  <div className="space-y-1">
                                    <span className="text-[10px] text-emerald-400 font-mono font-bold">
                                      Key Points Covered:
                                    </span>
                                    <ul className="list-disc list-inside text-slate-300 space-y-0.5 pl-1">
                                      {keyPoints.map((kp: string, kIdx: number) => (
                                        <li key={kIdx}>{kp}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {missingPoints.length > 0 && (
                                  <div className="space-y-1">
                                    <span className="text-[10px] text-amber-400 font-mono font-bold">
                                      Missing / Incomplete Concepts:
                                    </span>
                                    <ul className="list-disc list-inside text-slate-400 space-y-0.5 pl-1">
                                      {missingPoints.map((mp: string, mIdx: number) => (
                                        <li key={mIdx}>{mp}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                                {q.justification && (
                                  <p className="text-[11px] text-purple-300/80 font-mono">
                                    AI Feedback: {q.justification}
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Objective Justification Note (ONLY for non-subjective questions) */}
                            {!isSubjective && q.justification && (
                              <p className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded-lg border border-slate-800/50 font-mono">
                                Evaluation Note: {q.justification}
                              </p>
                            )}

                            {/* EXAMINER MANUAL REVIEW SECTION */}
                            {isSubjective && isExaminer && (
                              <div className="pt-3 border-t border-slate-800/80 space-y-3">
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-200 font-mono text-[11px] uppercase tracking-wider flex items-center gap-1.5">
                                    <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
                                    Examiner Manual Review & Finalization
                                  </span>
                                  {isFinalized && (
                                    <span className="text-[10px] text-emerald-400 font-mono flex items-center gap-1">
                                      <Lock className="w-3 h-3" /> Locked & Finalized
                                    </span>
                                  )}
                                </div>

                                {isFinalized ? (
                                  /* READ-ONLY FINALIZED VIEW */
                                  <div className="p-3.5 rounded-xl bg-emerald-950/20 border border-emerald-900/40 space-y-2 text-xs">
                                    <div className="flex items-center justify-between text-emerald-300 font-mono">
                                      <span className="font-bold">Final Score: {q.earned_score} / {q.marks}</span>
                                      <span className="text-[10px] text-emerald-400">
                                        Reviewed by: {q.reviewer_name || 'Examiner'}
                                        {q.reviewed_at ? ` on ${new Date(q.reviewed_at).toLocaleString()}` : ''}
                                      </span>
                                    </div>
                                    {q.examiner_comment ? (
                                      <p className="text-slate-300 font-sans italic">
                                        &quot;{q.examiner_comment}&quot;
                                      </p>
                                    ) : (
                                      <p className="text-slate-500 font-sans italic">No examiner comment attached.</p>
                                    )}
                                  </div>
                                ) : (
                                  /* EDITABLE REVIEW FORM */
                                  <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3">
                                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-center">
                                      <div>
                                        <label className="text-[10px] uppercase font-mono font-bold text-slate-400 block mb-1">
                                          Examiner Final Score (0 - {q.marks})
                                        </label>
                                        <input
                                          type="number"
                                          step="any"
                                          min="0"
                                          max={q.marks}
                                          disabled={isSubmitting}
                                          value={
                                            ansKey && reviewScores[ansKey] !== undefined
                                              ? reviewScores[ansKey]
                                              : q.earned_score !== undefined && q.earned_score !== null && q.earned_score > 0
                                              ? q.earned_score
                                              : q.suggested_score !== undefined && q.suggested_score !== null
                                              ? q.suggested_score
                                              : 0
                                          }
                                          onChange={(e) =>
                                            ansKey &&
                                            handleScoreChange(ansKey, e.target.value, q.marks)
                                          }
                                          className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono font-bold text-indigo-400 focus:outline-none focus:border-indigo-500 transition disabled:opacity-50"
                                        />
                                      </div>

                                      <div className="sm:col-span-2">
                                        <label className="text-[10px] uppercase font-mono font-bold text-slate-400 block mb-1">
                                          Examiner Comment (Optional)
                                        </label>
                                        <input
                                          type="text"
                                          placeholder="Enter grading justification or comment..."
                                          disabled={isSubmitting}
                                          value={
                                            ansKey && reviewComments[ansKey] !== undefined
                                              ? reviewComments[ansKey]
                                              : q.examiner_comment || ''
                                          }
                                          onChange={(e) =>
                                            ansKey && handleCommentChange(ansKey, e.target.value)
                                          }
                                          className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition disabled:opacity-50"
                                        />
                                      </div>
                                    </div>

                                    <div className="flex items-center justify-end gap-2 pt-1">
                                      <button
                                        type="button"
                                        disabled={isSubmitting}
                                        onClick={() => executeSubmitReview(q, false)}
                                        className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg font-semibold text-xs transition inline-flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                                      >
                                        <Save className="w-3.5 h-3.5" /> Save Review
                                      </button>
                                      <button
                                        type="button"
                                        disabled={isSubmitting}
                                        onClick={() => {
                                          const score =
                                            ansKey && reviewScores[ansKey] !== undefined
                                              ? reviewScores[ansKey]
                                              : q.earned_score || q.suggested_score || 0;
                                          const comment =
                                            ansKey && reviewComments[ansKey] !== undefined
                                              ? reviewComments[ansKey]
                                              : q.examiner_comment || '';
                                          setConfirmFinalizeTarget({ q, score, comment });
                                        }}
                                        className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold text-xs transition inline-flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                                      >
                                        <CheckSquare className="w-3.5 h-3.5" /> Finalize Evaluation
                                      </button>
                                    </div>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>

              <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex justify-end">
                <button
                  onClick={handleCloseDetail}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold transition"
                >
                  Close Breakdown
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CUSTOM IN-APP FINALIZE CONFIRMATION MODAL */}
        {confirmFinalizeTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl">
              <div className="flex items-center gap-3 text-indigo-400">
                <CheckSquare className="w-6 h-6 flex-shrink-0" />
                <h3 className="font-bold text-base text-white">Finalize Evaluation?</h3>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                Finalize this evaluation? The examiner score of{' '}
                <strong className="text-indigo-400 font-mono">
                  {confirmFinalizeTarget.score} / {confirmFinalizeTarget.q.marks}
                </strong>{' '}
                will become the permanent final score and recalculate the student&apos;s exam result.
              </p>

              {confirmFinalizeTarget.comment && (
                <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-400 italic">
                  &quot;{confirmFinalizeTarget.comment}&quot;
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setConfirmFinalizeTarget(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  onClick={() =>
                    executeSubmitReview(
                      confirmFinalizeTarget.q,
                      true,
                      confirmFinalizeTarget.score,
                      confirmFinalizeTarget.comment
                    )
                  }
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition inline-flex items-center gap-1.5"
                >
                  Confirm Finalize
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
