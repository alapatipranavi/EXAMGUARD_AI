'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Exam, ExamStatus, examsAPI } from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { PlusCircle, Search, Filter, BookOpen, Clock, Award, Send, Archive, Eye, Edit3, RotateCcw, Trash2 } from 'lucide-react';

export default function ExamsIndexPage() {
  const router = useRouter();

  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Action modal states
  const [examToPublish, setExamToPublish] = useState<Exam | null>(null);
  const [publishing, setPublishing] = useState(false);

  const [examToArchive, setExamToArchive] = useState<Exam | null>(null);
  const [archiving, setArchiving] = useState(false);

  const [examToUnarchive, setExamToUnarchive] = useState<Exam | null>(null);
  const [unarchiving, setUnarchiving] = useState(false);

  const [examToDelete, setExamToDelete] = useState<Exam | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [subject, setSubject] = useState('');
  const [statusFilter, setStatusFilter] = useState<ExamStatus | ''>('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalExams, setTotalExams] = useState(0);

  // Stats
  const [stats, setStats] = useState({
    total: 0,
    drafts: 0,
    published: 0,
    archived: 0,
  });

  const fetchExams = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await examsAPI.list({
        search: search.trim() || undefined,
        subject: subject.trim() || undefined,
        status: statusFilter || undefined,
        page,
        page_size: 10,
      });

      setExams(res.items);
      setTotalPages(res.total_pages);
      setTotalExams(res.total);

      // Compute stats breakdown
      const draftCount = res.items.filter((e) => e.status === 'DRAFT').length;
      const pubCount = res.items.filter((e) => e.status === 'PUBLISHED').length;
      const arcCount = res.items.filter((e) => e.status === 'ARCHIVED').length;
      setStats({
        total: res.total,
        drafts: draftCount,
        published: pubCount,
        archived: arcCount,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch exams.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExams();
  }, [search, subject, statusFilter, page]);

  const handlePublish = async (examId: string) => {
    setPublishing(true);
    setSuccessMessage(null);
    setError(null);
    try {
      await examsAPI.publish(examId);
      setExamToPublish(null);
      setSuccessMessage('Exam published successfully.');
      fetchExams();
    } catch (err: unknown) {
      setExamToPublish(null);
      setError(err instanceof Error ? err.message : 'Failed to publish exam.');
    } finally {
      setPublishing(false);
    }
  };

  const handleArchive = async (examId: string) => {
    setArchiving(true);
    setSuccessMessage(null);
    setError(null);
    try {
      await examsAPI.archive(examId);
      setExamToArchive(null);
      setSuccessMessage('Exam archived successfully.');
      fetchExams();
    } catch (err: unknown) {
      setExamToArchive(null);
      setError(err instanceof Error ? err.message : 'Failed to archive exam.');
    } finally {
      setArchiving(false);
    }
  };

  const handleUnarchive = async (examId: string) => {
    setUnarchiving(true);
    setSuccessMessage(null);
    setError(null);
    try {
      await examsAPI.unarchive(examId);
      setExamToUnarchive(null);
      setSuccessMessage('Exam unarchived and restored to Draft.');
      fetchExams();
    } catch (err: unknown) {
      setExamToUnarchive(null);
      setError(err instanceof Error ? err.message : 'Failed to unarchive exam.');
    } finally {
      setUnarchiving(false);
    }
  };

  const handleDelete = async (examId: string) => {
    setDeleting(true);
    setSuccessMessage(null);
    setError(null);
    try {
      await examsAPI.delete(examId);
      setExamToDelete(null);
      setSuccessMessage('Exam deleted successfully.');
      fetchExams();
    } catch (err: unknown) {
      setExamToDelete(null);
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('404') || msg.toLowerCase().includes('not found')) {
        setError('Exam no longer exists.');
        fetchExams();
      } else {
        setError(msg || 'Failed to delete exam.');
      }
    } finally {
      setDeleting(false);
    }
  };

  const renderStatusBadge = (status: ExamStatus) => {
    switch (status) {
      case 'DRAFT':
        return (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-amber-950/80 text-amber-300 border border-amber-800/60">
            Draft
          </span>
        );
      case 'PUBLISHED':
        return (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
            Published
          </span>
        );
      case 'ARCHIVED':
        return (
          <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-slate-900 text-slate-400 border border-slate-800">
            Archived
          </span>
        );
    }
  };

  return (
    <AppShell title="Exams Management" allowedRoles={['EXAMINER']}>
      <PageHeader
        title="Exams Management 📚"
        subtitle="Author, configure, and manage your assessment examinations."
        actions={
          <button
            onClick={() => router.push('/exams/create')}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2"
          >
            <PlusCircle className="w-4 h-4" /> Create Exam
          </button>
        }
      />

      {/* Metrics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl backdrop-blur-sm">
          <p className="text-[11px] font-mono text-slate-400 uppercase">Total Exams</p>
          <p className="text-xl font-bold text-white mt-1">{totalExams}</p>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl backdrop-blur-sm">
          <p className="text-[11px] font-mono text-amber-400 uppercase">Drafts</p>
          <p className="text-xl font-bold text-amber-300 mt-1">{stats.drafts}</p>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl backdrop-blur-sm">
          <p className="text-[11px] font-mono text-emerald-400 uppercase">Published</p>
          <p className="text-xl font-bold text-emerald-300 mt-1">{stats.published}</p>
        </div>
        <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl backdrop-blur-sm">
          <p className="text-[11px] font-mono text-slate-500 uppercase">Archived</p>
          <p className="text-xl font-bold text-slate-400 mt-1">{stats.archived}</p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
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

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ExamStatus | '')}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">Draft</option>
            <option value="PUBLISHED">Published</option>
            <option value="ARCHIVED">Archived</option>
          </select>
        </div>
      </div>

      {successMessage && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-800 text-emerald-300 rounded-2xl text-xs">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs">
          {error}
        </div>
      )}

      {/* Exam Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        {loading ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">Loading exams...</div>
        ) : exams.length === 0 ? (
          <div className="p-12 text-center text-slate-500 space-y-3">
            <BookOpen className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs">No exams found. Click &quot;Create Exam&quot; to author your first assessment.</p>
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
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {exams.map((exam) => (
                  <tr key={exam.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-4">
                      <div>
                        <p className="font-semibold text-white">{exam.title}</p>
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
                    <td className="py-3.5 px-4 font-mono">{exam.questions ? exam.questions.length : 0}</td>
                    <td className="py-3.5 px-4 font-mono text-indigo-300 font-bold">{exam.total_marks} pts</td>
                    <td className="py-3.5 px-4">{renderStatusBadge(exam.status)}</td>
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => router.push(`/exams/${exam.id}`)}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-lg transition flex items-center gap-1 text-[11px]"
                        >
                          {exam.status === 'DRAFT' ? (
                            <>
                              <Edit3 className="w-3.5 h-3.5" /> Edit
                            </>
                          ) : (
                            <>
                              <Eye className="w-3.5 h-3.5" /> View
                            </>
                          )}
                        </button>

                        {exam.status === 'DRAFT' && (
                          <>
                            <button
                              onClick={() => setExamToDelete(exam)}
                              className="p-1 text-slate-400 hover:text-red-400 hover:bg-slate-950 rounded-lg transition"
                              title="Delete Draft Exam"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => setExamToPublish(exam)}
                              className="px-2.5 py-1 bg-emerald-950/80 border border-emerald-800 hover:bg-emerald-900 text-emerald-300 rounded-lg transition flex items-center gap-1 text-[11px]"
                            >
                              <Send className="w-3.5 h-3.5" /> Publish
                            </button>
                          </>
                        )}

                        {exam.status === 'PUBLISHED' && (
                          <button
                            onClick={() => setExamToArchive(exam)}
                            className="p-1 text-slate-400 hover:text-red-400 hover:bg-slate-950 rounded-lg transition"
                            title="Archive Exam"
                          >
                            <Archive className="w-3.5 h-3.5" />
                          </button>
                        )}

                        {exam.status === 'ARCHIVED' && (
                          <button
                            onClick={() => setExamToUnarchive(exam)}
                            className="px-2.5 py-1 bg-amber-950/80 border border-amber-800 hover:bg-amber-900 text-amber-300 rounded-lg transition flex items-center gap-1 text-[11px]"
                          >
                            <RotateCcw className="w-3.5 h-3.5" /> Unarchive
                          </button>
                        )}
                      </div>
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

      {/* Confirmation Dialogs */}
      <ConfirmDialog
        open={!!examToPublish}
        title="Publish Exam"
        description="Are you sure you want to publish this exam? Once published, structural settings cannot be edited."
        confirmLabel="Publish Exam"
        cancelLabel="Cancel"
        variant="default"
        loading={publishing}
        onConfirm={() => examToPublish && handlePublish(examToPublish.id)}
        onCancel={() => setExamToPublish(null)}
      />

      <ConfirmDialog
        open={!!examToArchive}
        title="Archive Exam"
        description="Are you sure you want to archive this exam? Students will no longer be able to take archived exams."
        confirmLabel="Archive Exam"
        cancelLabel="Cancel"
        variant="warning"
        loading={archiving}
        onConfirm={() => examToArchive && handleArchive(examToArchive.id)}
        onCancel={() => setExamToArchive(null)}
      />

      <ConfirmDialog
        open={!!examToUnarchive}
        title="Unarchive Exam"
        description="Unarchive this exam and move it back to Draft?"
        confirmLabel="Unarchive"
        cancelLabel="Cancel"
        variant="warning"
        loading={unarchiving}
        onConfirm={() => examToUnarchive && handleUnarchive(examToUnarchive.id)}
        onCancel={() => setExamToUnarchive(null)}
      />

      <ConfirmDialog
        open={!!examToDelete}
        title="Delete this draft exam permanently?"
        description="All exam configuration and question selections for this draft will be removed. Questions in your Question Bank will NOT be deleted."
        confirmLabel="Delete Exam"
        cancelLabel="Cancel"
        variant="danger"
        loading={deleting}
        onConfirm={() => examToDelete && handleDelete(examToDelete.id)}
        onCancel={() => setExamToDelete(null)}
      />
    </AppShell>
  );
}
