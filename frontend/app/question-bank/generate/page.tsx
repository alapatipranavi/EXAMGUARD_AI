'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  QuestionType,
  DifficultyLevel,
  AIGeneratedDraft,
  aiQuestionsAPI,
  questionsAPI,
} from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import { Sparkles, Check, Trash2, ArrowLeft, CheckSquare, Square } from 'lucide-react';

export default function AIQuestionGeneratorPage() {
  const router = useRouter();

  // Config Form
  const [subject, setSubject] = useState('Computer Networks');
  const [topic, setTopic] = useState('TCP Congestion Control');
  const [questionTypes, setQuestionTypes] = useState<QuestionType[]>(['MCQ', 'SHORT_ANSWER']);
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('MEDIUM');
  const [count, setCount] = useState<number>(5);
  const [marks, setMarks] = useState<number>(2.0);
  const [learningObjective, setLearningObjective] = useState('');
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Generated Drafts Review state
  const [drafts, setDrafts] = useState<AIGeneratedDraft[]>([]);
  const [selectedDraftIds, setSelectedDraftIds] = useState<Set<string>>(new Set());
  const [accepting, setAccepting] = useState(false);

  const toggleQuestionType = (type: QuestionType) => {
    if (questionTypes.includes(type)) {
      if (questionTypes.length > 1) {
        setQuestionTypes(questionTypes.filter((t) => t !== type));
      }
    } else {
      setQuestionTypes([...questionTypes, type]);
    }
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!subject.trim() || !topic.trim()) {
      setError('Subject and Topic are required.');
      return;
    }

    setGenerating(true);
    try {
      const res = await aiQuestionsAPI.generate({
        subject,
        topic,
        question_types: questionTypes,
        difficulty,
        count,
        marks,
        learning_objective: learningObjective.trim() || undefined,
        additional_instructions: additionalInstructions.trim() || undefined,
      });
      setDrafts(res.drafts);
      setSelectedDraftIds(new Set(res.drafts.map((d) => d.draft_id)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'AI Question Generation failed.');
    } finally {
      setGenerating(false);
    }
  };

  const handleToggleSelectDraft = (id: string) => {
    const next = new Set(selectedDraftIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedDraftIds(next);
  };

  const handleToggleSelectAll = () => {
    if (selectedDraftIds.size === drafts.length) {
      setSelectedDraftIds(new Set());
    } else {
      setSelectedDraftIds(new Set(drafts.map((d) => d.draft_id)));
    }
  };

  const handleRemoveDraft = (id: string) => {
    setDrafts(drafts.filter((d) => d.draft_id !== id));
    const next = new Set(selectedDraftIds);
    next.delete(id);
    setSelectedDraftIds(next);
  };

  const handleAcceptSelected = async () => {
    const selectedDrafts = drafts.filter((d) => selectedDraftIds.has(d.draft_id));
    if (selectedDrafts.length === 0) {
      setError('Please select at least one draft question to accept.');
      return;
    }

    setAccepting(true);
    setError(null);
    try {
      for (const d of selectedDrafts) {
        await questionsAPI.create({
          question_text: d.question_text,
          subject: d.subject,
          topic: d.topic || undefined,
          question_type: d.question_type,
          difficulty: d.difficulty,
          source: 'AI_GENERATED',
          marks: d.marks,
          negative_marks: d.negative_marks,
          model_answer: d.model_answer || undefined,
          explanation: d.explanation || undefined,
          options: d.options && d.options.length > 0 ? d.options : undefined,
        });
      }
      router.push('/question-bank');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save accepted questions.');
    } finally {
      setAccepting(false);
    }
  };

  return (
    <AppShell title="AI Question Generator" allowedRoles={['EXAMINER']}>
      <PageHeader
        title="AI Question Generator ✨"
        subtitle="Specify topics and objectives to generate structured question drafts for review."
        actions={
          <button
            onClick={() => router.push('/question-bank')}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" /> Question Bank
          </button>
        }
      />

      {error && (
        <div className="p-4 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs leading-normal">
          <strong>Service Alert:</strong> {error}
        </div>
      )}

      {/* Configuration Form */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-6">
        <form onSubmit={handleGenerate} className="space-y-6 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">
                Subject <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Computer Networks"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">
                Topic <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                required
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. TCP Congestion Control"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as DifficultyLevel)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
              >
                <option value="EASY">Easy</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Number of Questions</label>
              <input
                type="number"
                min="1"
                max="20"
                value={count}
                onChange={(e) => setCount(parseInt(e.target.value) || 1)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1.5">Allowed Question Types</label>
            <div className="flex flex-wrap gap-2">
              {(['MCQ', 'MULTI_SELECT', 'SHORT_ANSWER', 'LONG_ANSWER', 'HANDWRITTEN'] as QuestionType[]).map((t) => {
                const isSelected = questionTypes.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleQuestionType(t)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition border ${
                      isSelected
                        ? 'bg-purple-950 border-purple-600 text-purple-300'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                    }`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Learning Objective</label>
              <input
                type="text"
                value={learningObjective}
                onChange={(e) => setLearningObjective(e.target.value)}
                placeholder="e.g. Understand congestion window dynamics..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Additional Instructions</label>
              <input
                type="text"
                value={additionalInstructions}
                onChange={(e) => setAdditionalInstructions(e.target.value)}
                placeholder="e.g. Include real-world scenarios..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-500"
              />
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={generating}
              className="px-6 py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-purple-600/25 flex items-center gap-2 disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              {generating ? 'Generating Drafts...' : 'Generate Questions ✨'}
            </button>
          </div>
        </form>
      </div>

      {/* Draft Review Section */}
      {drafts.length > 0 && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm">
            <div className="flex items-center gap-3">
              <button
                onClick={handleToggleSelectAll}
                className="flex items-center gap-1.5 text-xs font-semibold text-purple-300 hover:text-white"
              >
                {selectedDraftIds.size === drafts.length ? (
                  <CheckSquare className="w-4 h-4 text-purple-400" />
                ) : (
                  <Square className="w-4 h-4 text-slate-500" />
                )}
                <span>Select All ({selectedDraftIds.size}/{drafts.length})</span>
              </button>
              <span className="text-xs text-slate-400">
                Draft questions are transient and require Examiner acceptance.
              </span>
            </div>

            <button
              onClick={handleAcceptSelected}
              disabled={accepting || selectedDraftIds.size === 0}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition shadow-lg shadow-emerald-600/20 flex items-center gap-1.5 disabled:opacity-50"
            >
              <Check className="w-4 h-4" />
              {accepting ? 'Saving to Bank...' : `Accept Selected (${selectedDraftIds.size})`}
            </button>
          </div>

          <div className="space-y-4">
            {drafts.map((d, idx) => {
              const isSelected = selectedDraftIds.has(d.draft_id);
              return (
                <div
                  key={d.draft_id}
                  className={`p-5 rounded-2xl border transition backdrop-blur-sm ${
                    isSelected
                      ? 'bg-slate-900/90 border-purple-500/50 shadow-lg'
                      : 'bg-slate-900/40 border-slate-800/80 opacity-80'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <button
                        onClick={() => handleToggleSelectDraft(d.draft_id)}
                        className="mt-1"
                      >
                        {isSelected ? (
                          <CheckSquare className="w-5 h-5 text-purple-400" />
                        ) : (
                          <Square className="w-5 h-5 text-slate-600" />
                        )}
                      </button>

                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-slate-400">
                            Draft #{idx + 1}
                          </span>
                          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-950 text-purple-300 border border-purple-800/60 inline-flex items-center gap-1">
                            <Sparkles className="w-3 h-3" /> AI Draft
                          </span>
                          <span className="px-2 py-0.5 text-[10px] font-mono rounded bg-slate-950 text-indigo-300 border border-slate-800">
                            {d.question_type}
                          </span>
                        </div>

                        <p className="text-sm font-semibold text-white leading-relaxed">
                          {d.question_text}
                        </p>

                        {/* Options */}
                        {d.options && d.options.length > 0 && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                            {d.options.map((opt, oIdx) => (
                              <div
                                key={oIdx}
                                className={`p-2 rounded-xl text-xs border ${
                                  opt.is_correct
                                    ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300 font-semibold'
                                    : 'bg-slate-950 border-slate-800 text-slate-300'
                                }`}
                              >
                                {opt.option_text} {opt.is_correct && '✓'}
                              </div>
                            ))}
                          </div>
                        )}

                        {d.explanation && (
                          <p className="text-xs text-slate-400 italic pt-1">
                            <strong>Explanation:</strong> {d.explanation}
                          </p>
                        )}
                      </div>
                    </div>

                    <button
                      onClick={() => handleRemoveDraft(d.draft_id)}
                      className="p-2 text-slate-400 hover:text-red-400 hover:bg-slate-950 rounded-xl transition"
                      title="Remove Draft"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </AppShell>
  );
}
