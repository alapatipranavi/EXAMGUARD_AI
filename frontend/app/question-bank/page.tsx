'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Question,
  QuestionType,
  DifficultyLevel,
  QuestionSource,
  questionsAPI,
} from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import QuestionFormModal from '@/components/question-bank/QuestionFormModal';
import ArchiveConfirmModal from '@/components/question-bank/ArchiveConfirmModal';
import { PlusCircle, Sparkles, FileSpreadsheet, Search } from 'lucide-react';

export default function QuestionBankPage() {
  // Filter States
  const [search, setSearch] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('true');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Data States
  const [questions, setQuestions] = useState<Question[]>([]);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [dataLoading, setDataLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modal States
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null);
  const [isArchiveModalOpen, setIsArchiveModalOpen] = useState(false);
  const [questionToArchive, setQuestionToArchive] = useState<Question | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);

  const loadQuestions = useCallback(async () => {
    setDataLoading(true);
    setError(null);
    try {
      const res = await questionsAPI.list({
        search: search.trim() || undefined,
        subject: subjectFilter.trim() || undefined,
        question_type: (typeFilter as QuestionType) || undefined,
        difficulty: (difficultyFilter as DifficultyLevel) || undefined,
        source: (sourceFilter as QuestionSource) || undefined,
        is_active: statusFilter === 'all' ? undefined : statusFilter === 'true',
        page,
        page_size: pageSize,
      });
      setQuestions(res.items);
      setTotalQuestions(res.total);
      setTotalPages(res.total_pages);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch questions.');
    } finally {
      setDataLoading(false);
    }
  }, [search, subjectFilter, typeFilter, difficultyFilter, sourceFilter, statusFilter, page, pageSize]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const handleOpenCreateModal = () => {
    setSelectedQuestion(null);
    setIsFormModalOpen(true);
  };

  const handleOpenEditModal = (q: Question) => {
    setSelectedQuestion(q);
    setIsFormModalOpen(true);
  };

  const handleOpenArchiveModal = (q: Question) => {
    setQuestionToArchive(q);
    setIsArchiveModalOpen(true);
  };

  const handleConfirmArchive = async () => {
    if (!questionToArchive) return;
    setArchiveLoading(true);
    setError(null);
    try {
      await questionsAPI.archive(questionToArchive.id);
      setIsArchiveModalOpen(false);
      setQuestionToArchive(null);
      loadQuestions();
    } catch (err: unknown) {
      setIsArchiveModalOpen(false);
      setQuestionToArchive(null);
      setError(err instanceof Error ? err.message : 'Failed to archive question.');
    } finally {
      setArchiveLoading(false);
    }
  };

  const renderSourceBadge = (src: QuestionSource) => {
    switch (src) {
      case 'AI_GENERATED':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-950 text-purple-300 border border-purple-800/60 inline-flex items-center gap-1">
            <Sparkles className="w-3 h-3" /> AI Generated
          </span>
        );
      case 'CSV_IMPORT':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/60 inline-flex items-center gap-1">
            <FileSpreadsheet className="w-3 h-3" /> CSV Import
          </span>
        );
      case 'PDF_IMPORT':
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-950 text-amber-300 border border-amber-800/60 inline-flex items-center gap-1">
            <FileSpreadsheet className="w-3 h-3" /> PDF Import
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            Manual
          </span>
        );
    }
  };

  return (
    <AppShell title="Question Bank" allowedRoles={['EXAMINER']}>
      <PageHeader
        title="Question Bank"
        subtitle="Create, organize, import, and enhance your examination questions."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/question-bank/create"
              className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-md shadow-indigo-600/20 flex items-center gap-1.5"
            >
              <PlusCircle className="w-4 h-4" /> Create Question
            </Link>

            <Link
              href="/question-bank/generate"
              className="px-3.5 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-xl transition shadow-md shadow-purple-600/20 flex items-center gap-1.5"
            >
              <Sparkles className="w-4 h-4" /> Generate with AI ✨
            </Link>

            <Link
              href="/question-bank/import"
              className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition shadow-md shadow-emerald-600/20 flex items-center gap-1.5"
            >
              <FileSpreadsheet className="w-4 h-4" /> Import Questions 📥
            </Link>
          </div>
        }
      />

      {/* Filters Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {/* Search */}
          <div className="lg:col-span-2 relative">
            <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
              Search Statement
            </label>
            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                placeholder="Search text, subject, topic..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Subject */}
          <div>
            <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
              Subject
            </label>
            <input
              type="text"
              value={subjectFilter}
              onChange={(e) => {
                setSubjectFilter(e.target.value);
                setPage(1);
              }}
              placeholder="Filter subject..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Type */}
          <div>
            <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
              Question Type
            </label>
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Types</option>
              <option value="MCQ">MCQ</option>
              <option value="MULTI_SELECT">Multi-Select</option>
              <option value="SHORT_ANSWER">Short Answer</option>
              <option value="LONG_ANSWER">Long Answer</option>
              <option value="HANDWRITTEN">Handwritten</option>
            </select>
          </div>

          {/* Difficulty */}
          <div>
            <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
              Difficulty
            </label>
            <select
              value={difficultyFilter}
              onChange={(e) => {
                setDifficultyFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Difficulties</option>
              <option value="EASY">Easy</option>
              <option value="MEDIUM">Medium</option>
              <option value="HARD">Hard</option>
            </select>
          </div>

          {/* Source Filter */}
          <div>
            <label className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
              Source
            </label>
            <select
              value={sourceFilter}
              onChange={(e) => {
                setSourceFilter(e.target.value);
                setPage(1);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Sources</option>
              <option value="MANUAL">Manual</option>
              <option value="AI_GENERATED">AI Generated</option>
              <option value="CSV_IMPORT">CSV Import</option>
              <option value="PDF_IMPORT">PDF Import</option>
            </select>
          </div>
        </div>

        <div className="flex flex-wrap justify-between items-center pt-2 border-t border-slate-800/80 text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <span className="font-mono text-[10px] uppercase">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-white"
            >
              <option value="true">Active Only</option>
              <option value="false">Archived Only</option>
              <option value="all">All Statuses</option>
            </select>
          </div>

          <div>
            Total Questions: <strong className="text-white">{totalQuestions}</strong>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-red-950/50 border border-red-800/80 text-red-300 rounded-2xl text-xs">
          {error}
        </div>
      )}

      {/* Questions Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
        {dataLoading ? (
          <div className="p-12 text-center text-slate-400 font-mono text-xs">
            Loading question items...
          </div>
        ) : questions.length === 0 ? (
          <div className="p-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center mx-auto text-slate-500">
              📝
            </div>
            <h3 className="text-base font-bold text-white">No Questions Found</h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              No questions match your current search or filter criteria. Click &quot;Create Question&quot; to add items to your bank.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-950/60 border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Question</th>
                  <th className="py-3 px-4">Subject / Topic</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Difficulty</th>
                  <th className="py-3 px-4 text-center">Marks</th>
                  <th className="py-3 px-4">Source</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 text-xs">
                {questions.map((q) => (
                  <tr key={q.id} className="hover:bg-slate-950/40 transition">
                    <td className="py-3.5 px-4 max-w-md">
                      <p className="font-semibold text-white line-clamp-2">{q.question_text}</p>
                      {q.options && q.options.length > 0 && (
                        <span className="text-[10px] text-slate-400 mt-0.5 block">
                          {q.options.length} options ({q.options.filter((o) => o.is_correct).length} correct)
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className="font-bold text-slate-200">{q.subject}</span>
                      {q.topic && <span className="block text-[10px] text-slate-400">{q.topic}</span>}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                        {q.question_type}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                          q.difficulty === 'EASY'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60'
                            : q.difficulty === 'MEDIUM'
                            ? 'bg-amber-950 text-amber-300 border border-amber-800/60'
                            : 'bg-red-950 text-red-300 border border-red-800/60'
                        }`}
                      >
                        {q.difficulty}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap font-bold text-slate-200">
                      {q.marks} {q.negative_marks > 0 && <span className="text-[10px] text-red-400">(-{q.negative_marks})</span>}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      {renderSourceBadge(q.source)}
                    </td>
                    <td className="py-3.5 px-4 text-center whitespace-nowrap">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${
                          q.is_active
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {q.is_active ? 'Active' : 'Archived'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap space-x-2">
                      <button
                        onClick={() => handleOpenEditModal(q)}
                        className="px-2.5 py-1 text-[11px] font-semibold text-indigo-400 border border-indigo-800/60 rounded-lg hover:bg-indigo-950/40 transition"
                      >
                        Edit
                      </button>
                      {q.is_active && (
                        <button
                          onClick={() => handleOpenArchiveModal(q)}
                          className="px-2.5 py-1 text-[11px] font-semibold text-red-400 border border-red-800/60 rounded-lg hover:bg-red-950/40 transition"
                        >
                          Archive
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {totalPages > 0 && (
          <div className="p-4 bg-slate-950/60 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span>Items per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-xs text-white"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div>
              Page <strong className="text-white">{page}</strong> of <strong className="text-white">{totalPages}</strong> ({totalQuestions} items)
            </div>

            <div className="flex items-center space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1 border border-slate-800 bg-slate-900 rounded-lg font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition"
              >
                Previous
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1 border border-slate-800 bg-slate-900 rounded-lg font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <QuestionFormModal
        isOpen={isFormModalOpen}
        onClose={() => setIsFormModalOpen(false)}
        onSuccess={loadQuestions}
        initialData={selectedQuestion}
      />

      <ArchiveConfirmModal
        isOpen={isArchiveModalOpen}
        onClose={() => setIsArchiveModalOpen(false)}
        onConfirm={handleConfirmArchive}
        questionText={questionToArchive?.question_text}
        loading={archiveLoading}
      />
    </AppShell>
  );
}
