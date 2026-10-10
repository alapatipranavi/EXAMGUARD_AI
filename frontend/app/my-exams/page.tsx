'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { StudentExamItem, studentExamsAPI } from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import { Search, BookOpen, Clock, Award, Play, CheckCircle2, RotateCcw } from 'lucide-react';

export default function StudentExamsPage() {
  const router = useRouter();

  const [exams, setExams] = useState<StudentExamItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [subject, setSubject] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalExams, setTotalExams] = useState(0);

  const fetchExams = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await studentExamsAPI.listExams({
        search: search.trim() || undefined,
        subject: subject.trim() || undefined,
        page,
        page_size: 10,
      });

      setExams(res.items);
      setTotalPages(res.total_pages);
      setTotalExams(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch available exams.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, [search, subject, page]);

  const renderSessionBadge = (status: 'AVAILABLE' | 'IN_PROGRESS' | 'COMPLETED') => {
    switch (status) {
      case 'AVAILABLE':
        return (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
            Available
          </span>
        );
      case 'IN_PROGRESS':
        return (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-amber-950/80 text-amber-300 border border-amber-800/60">
            In Progress
          </span>
        );
      case 'COMPLETED':
        return (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-slate-900 text-slate-400 border border-slate-800">
            Submitted
          </span>
        );
    }
  };

  return (
    <AppShell title="My Exams" allowedRoles={['STUDENT']}>
      <PageHeader
        title="My Examinations 📚"
        subtitle="View and take your registered assessment examinations."
      />

      {/* Filter Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search title, subject, description..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <input
            type="text"
            placeholder="Filter by subject..."
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs">
          {error}
        </div>
      )}

      {/* Exams Grid */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">Loading available exams...</div>
        ) : exams.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-3">
            <BookOpen className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs">No active published exams are currently available for taking.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="py-3 px-4">Exam Title</th>
                  <th className="py-3 px-4">Subject</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Questions</th>
                  <th className="py-3 px-4">Total Marks</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {exams.map((exam) => (
                  <tr key={exam.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4">
                      <div>
                        <button
                          onClick={() => router.push(`/my-exams/${exam.id}`)}
                          className="font-semibold text-white hover:text-indigo-400 transition text-left"
                        >
                          {exam.title}
                        </button>
                        {exam.description && (
                          <p className="text-[11px] text-slate-400 line-clamp-1">{exam.description}</p>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-medium">{exam.subject}</td>
                    <td className="py-3.5 px-4 font-mono">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5 text-slate-500" /> {exam.duration_minutes} min
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono">{exam.question_count}</td>
                    <td className="py-3.5 px-4 font-mono text-indigo-300 font-bold">{exam.total_marks} pts</td>
                    <td className="py-3.5 px-4">{renderSessionBadge(exam.student_session_status)}</td>
                    <td className="py-3.5 px-4 text-right">
                      {exam.student_session_status === 'AVAILABLE' && (
                        <button
                          onClick={() => router.push(`/my-exams/${exam.id}`)}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl transition shadow-md shadow-indigo-600/20 text-xs font-semibold inline-flex items-center gap-1.5"
                        >
                          <Play className="w-3.5 h-3.5" /> Start Exam
                        </button>
                      )}

                      {exam.student_session_status === 'IN_PROGRESS' && (
                        <button
                          onClick={() => router.push(`/my-exams/${exam.id}`)}
                          className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-xl transition shadow-md shadow-amber-600/20 text-xs font-semibold inline-flex items-center gap-1.5"
                        >
                          <RotateCcw className="w-3.5 h-3.5" />
                          {exam.identity_verification_status === 'VERIFIED' ? 'Continue Exam' : 'Verify Identity & Continue'}
                        </button>
                      )}

                      {exam.student_session_status === 'COMPLETED' && (
                        <span className="px-3 py-1.5 text-slate-400 text-xs font-medium inline-flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Submitted
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-between items-center text-xs">
            <span className="text-slate-400">
              Page {page} of {totalPages}
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg hover:bg-slate-800 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                disabled={page === totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1 bg-slate-900 border border-slate-800 text-slate-300 rounded-lg hover:bg-slate-800 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
