'use client';

import React, { useState, useEffect } from 'react';
import {
  Question,
  QuestionType,
  DifficultyLevel,
  QuestionSource,
  ExamQuestionInput,
  questionsAPI,
} from '@/lib/api';
import { Search, Filter, CheckSquare, Square, ChevronUp, ChevronDown, Trash2, HelpCircle } from 'lucide-react';

interface QuestionPickerProps {
  selectedInputs: ExamQuestionInput[];
  onChange: (inputs: ExamQuestionInput[]) => void;
  readOnly?: boolean;
}

export default function QuestionPicker({ selectedInputs, onChange, readOnly = false }: QuestionPickerProps) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [subject, setSubject] = useState('');
  const [questionType, setQuestionType] = useState<QuestionType | ''>('');
  const [difficulty, setDifficulty] = useState<DifficultyLevel | ''>('');
  const [source, setSource] = useState<QuestionSource | ''>('');

  // Map of loaded questions by ID for fast lookup
  const [questionMap, setQuestionMap] = useState<Record<string, Question>>({});

  const fetchQuestions = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await questionsAPI.list({
        search: search.trim() || undefined,
        subject: subject.trim() || undefined,
        question_type: questionType || undefined,
        difficulty: difficulty || undefined,
        source: source || undefined,
        is_active: true,
        page: 1,
        page_size: 50,
      });
      setQuestions(res.items);

      // Accumulate into questionMap
      setQuestionMap((prev) => {
        const next = { ...prev };
        res.items.forEach((q) => {
          next[q.id] = q;
        });
        return next;
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch questions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuestions();
  }, [search, subject, questionType, difficulty, source]);

  const selectedIds = new Set(selectedInputs.map((i) => i.question_id));

  const handleToggleSelect = (q: Question) => {
    if (readOnly) return;
    if (selectedIds.has(q.id)) {
      // Remove
      const filtered = selectedInputs
        .filter((i) => i.question_id !== q.id)
        .map((item, idx) => ({ ...item, question_order: idx + 1 }));
      onChange(filtered);
    } else {
      // Add
      const nextInputs = [
        ...selectedInputs,
        {
          question_id: q.id,
          question_order: selectedInputs.length + 1,
        },
      ];
      onChange(nextInputs);
    }
  };

  const handleMoveUp = (index: number) => {
    if (readOnly || index <= 0) return;
    const next = [...selectedInputs];
    const temp = next[index - 1];
    next[index - 1] = next[index];
    next[index] = temp;

    // Update orders
    const reordered = next.map((item, idx) => ({ ...item, question_order: idx + 1 }));
    onChange(reordered);
  };

  const handleMoveDown = (index: number) => {
    if (readOnly || index >= selectedInputs.length - 1) return;
    const next = [...selectedInputs];
    const temp = next[index + 1];
    next[index + 1] = next[index];
    next[index] = temp;

    const reordered = next.map((item, idx) => ({ ...item, question_order: idx + 1 }));
    onChange(reordered);
  };

  const handleRemove = (questionId: string) => {
    if (readOnly) return;
    const filtered = selectedInputs
      .filter((i) => i.question_id !== questionId)
      .map((item, idx) => ({ ...item, question_order: idx + 1 }));
    onChange(filtered);
  };

  const handleMarksOverrideChange = (questionId: string, value: string) => {
    if (readOnly) return;
    const num = parseFloat(value);
    const updated = selectedInputs.map((item) => {
      if (item.question_id === questionId) {
        return {
          ...item,
          marks_override: isNaN(num) || num <= 0 ? undefined : num,
        };
      }
      return item;
    });
    onChange(updated);
  };

  // Calculate live total marks
  const totalSelectedMarks = selectedInputs.reduce((acc, input) => {
    const q = questionMap[input.question_id];
    const marks = input.marks_override !== undefined && input.marks_override !== null
      ? input.marks_override
      : (q ? q.marks : 0);
    return acc + marks;
  }, 0);

  return (
    <div className="space-y-6 text-xs">
      {/* Metrics Summary Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-slate-900 border border-slate-800 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="px-3 py-1.5 bg-indigo-950/80 border border-indigo-800/60 rounded-xl">
            <span className="text-slate-400">Selected Questions: </span>
            <span className="font-bold text-indigo-300">{selectedInputs.length}</span>
          </div>
          <div className="px-3 py-1.5 bg-purple-950/80 border border-purple-800/60 rounded-xl">
            <span className="text-slate-400">Total Calculated Marks: </span>
            <span className="font-bold text-purple-300">{totalSelectedMarks.toFixed(2)}</span>
          </div>
        </div>
        <p className="text-[11px] text-slate-400">
          Select questions from your bank below. Reorder or override marks in the Selected Panel.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Side: Question Bank Search & Selection List */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 space-y-4 backdrop-blur-sm">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-indigo-400" /> Question Bank Catalog
          </h3>

          {/* Filters */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search statement, subject, topic..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <select
                value={questionType}
                onChange={(e) => setQuestionType(e.target.value as QuestionType | '')}
                className="bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Types</option>
                <option value="MCQ">MCQ</option>
                <option value="MULTI_SELECT">Multi-Select</option>
                <option value="SHORT_ANSWER">Short Answer</option>
                <option value="LONG_ANSWER">Long Answer</option>
                <option value="HANDWRITTEN">Handwritten</option>
              </select>

              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as DifficultyLevel | '')}
                className="bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Difficulties</option>
                <option value="EASY">Easy</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard</option>
              </select>

              <select
                value={source}
                onChange={(e) => setSource(e.target.value as QuestionSource | '')}
                className="bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Sources</option>
                <option value="MANUAL">Manual</option>
                <option value="AI_GENERATED">AI Generated</option>
                <option value="CSV_IMPORT">CSV Import</option>
                <option value="PDF_IMPORT">PDF Import</option>
              </select>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-950/60 border border-red-800 text-red-300 rounded-xl text-xs">
              {error}
            </div>
          )}

          {/* Catalog List */}
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {loading ? (
              <p className="p-4 text-center text-slate-500 font-mono">Loading questions...</p>
            ) : questions.length === 0 ? (
              <p className="p-4 text-center text-slate-500">No active questions found in your bank.</p>
            ) : (
              questions.map((q) => {
                const isSelected = selectedIds.has(q.id);
                return (
                  <div
                    key={q.id}
                    onClick={() => !readOnly && handleToggleSelect(q)}
                    className={`p-3 rounded-xl border transition cursor-pointer flex items-start gap-3 ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-600/60 text-indigo-200'
                        : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                    }`}
                  >
                    <div className="mt-0.5">
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-indigo-400" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-600" />
                      )}
                    </div>

                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-white text-xs">{q.subject}</span>
                        {q.topic && <span className="text-slate-500">({q.topic})</span>}
                        <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-slate-900 border border-slate-800 text-slate-400">
                          {q.question_type}
                        </span>
                        <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-slate-900 border border-slate-800 text-slate-400">
                          {q.difficulty}
                        </span>
                        <span className="ml-auto font-mono text-xs font-bold text-indigo-300">
                          {q.marks} pts
                        </span>
                      </div>
                      <p className="text-xs line-clamp-2">{q.question_text}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Side: Selected Questions Panel with Order & Override Controls */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 space-y-4 backdrop-blur-sm">
          <h3 className="font-bold text-white text-xs flex items-center justify-between">
            <span>Selected Exam Questions ({selectedInputs.length})</span>
            {selectedInputs.length > 0 && !readOnly && (
              <button
                type="button"
                onClick={() => onChange([])}
                className="text-[11px] text-red-400 hover:text-red-300 transition"
              >
                Clear All
              </button>
            )}
          </h3>

          <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
            {selectedInputs.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-slate-800 rounded-xl text-slate-500">
                No questions selected yet. Pick questions from the catalog on the left.
              </div>
            ) : (
              selectedInputs.map((input, idx) => {
                const q = questionMap[input.question_id];
                const currentMarks = input.marks_override !== undefined && input.marks_override !== null
                  ? input.marks_override
                  : (q ? q.marks : 0);

                return (
                  <div
                    key={input.question_id}
                    className="p-3 bg-slate-950 border border-indigo-500/30 rounded-xl space-y-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-indigo-950 border border-indigo-700 text-indigo-300 font-mono text-[10px] font-bold flex items-center justify-center">
                          #{idx + 1}
                        </span>
                        <span className="font-semibold text-white text-xs">
                          {q ? q.subject : 'Question'}
                        </span>
                        {q?.topic && <span className="text-slate-500 text-[11px]">({q.topic})</span>}
                        {q && (
                          <span className="px-1.5 py-0.5 text-[9px] font-mono rounded bg-slate-900 text-slate-400 border border-slate-800">
                            {q.question_type}
                          </span>
                        )}
                      </div>

                      {!readOnly && (
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            disabled={idx === 0}
                            onClick={() => handleMoveUp(idx)}
                            className="p-1 hover:bg-slate-800 rounded text-slate-400 disabled:opacity-30"
                            title="Move Up"
                          >
                            <ChevronUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            disabled={idx === selectedInputs.length - 1}
                            onClick={() => handleMoveDown(idx)}
                            className="p-1 hover:bg-slate-800 rounded text-slate-400 disabled:opacity-30"
                            title="Move Down"
                          >
                            <ChevronDown className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRemove(input.question_id)}
                            className="p-1 hover:bg-red-950/50 text-slate-400 hover:text-red-400 rounded transition"
                            title="Remove"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {q ? q.question_text : `Question ID: ${input.question_id}`}
                    </p>

                    <div className="flex items-center justify-between border-t border-slate-900 pt-2 text-[11px]">
                      <span className="text-slate-400">
                        Base Marks: <strong className="text-slate-200">{q ? q.marks : 0}</strong>
                      </span>

                      {!readOnly ? (
                        <div className="flex items-center gap-1.5">
                          <label className="text-slate-400">Override Marks:</label>
                          <input
                            type="number"
                            step="0.5"
                            min="0.5"
                            placeholder={q ? String(q.marks) : '0'}
                            value={input.marks_override !== undefined ? input.marks_override : ''}
                            onChange={(e) => handleMarksOverrideChange(input.question_id, e.target.value)}
                            className="w-16 bg-slate-900 border border-slate-800 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
                          />
                        </div>
                      ) : (
                        <span className="font-mono font-bold text-indigo-300">
                          {currentMarks} pts
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
