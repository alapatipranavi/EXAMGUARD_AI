'use client';

import React, { useState, useEffect } from 'react';
import {
  Question,
  QuestionType,
  DifficultyLevel,
  QuestionOptionInput,
  QuestionCreateInput,
  QuestionUpdateInput,
  questionsAPI,
} from '@/lib/api';

interface QuestionFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialData?: Question | null;
}

export default function QuestionFormModal({
  isOpen,
  onClose,
  onSuccess,
  initialData,
}: QuestionFormModalProps) {
  const [questionText, setQuestionText] = useState('');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [questionType, setQuestionType] = useState<QuestionType>('MCQ');
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('MEDIUM');
  const [marks, setMarks] = useState<number>(1);
  const [negativeMarks, setNegativeMarks] = useState<number>(0);
  const [modelAnswer, setModelAnswer] = useState('');
  const [explanation, setExplanation] = useState('');
  const [options, setOptions] = useState<QuestionOptionInput[]>([
    { option_text: '', option_order: 1, is_correct: true },
    { option_text: '', option_order: 2, is_correct: false },
  ]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setQuestionText(initialData.question_text || '');
      setSubject(initialData.subject || '');
      setTopic(initialData.topic || '');
      setQuestionType(initialData.question_type || 'MCQ');
      setDifficulty(initialData.difficulty || 'MEDIUM');
      setMarks(initialData.marks ?? 1);
      setNegativeMarks(initialData.negative_marks ?? 0);
      setModelAnswer(initialData.model_answer || '');
      setExplanation(initialData.explanation || '');
      if (initialData.options && initialData.options.length > 0) {
        setOptions(
          initialData.options.map((o) => ({
            option_text: o.option_text,
            option_order: o.option_order,
            is_correct: o.is_correct,
          }))
        );
      } else {
        setOptions([
          { option_text: '', option_order: 1, is_correct: true },
          { option_text: '', option_order: 2, is_correct: false },
        ]);
      }
    } else {
      setQuestionText('');
      setSubject('');
      setTopic('');
      setQuestionType('MCQ');
      setDifficulty('MEDIUM');
      setMarks(1);
      setNegativeMarks(0);
      setModelAnswer('');
      setExplanation('');
      setOptions([
        { option_text: '', option_order: 1, is_correct: true },
        { option_text: '', option_order: 2, is_correct: false },
      ]);
    }
    setError(null);
  }, [initialData, isOpen]);

  if (!isOpen) return null;

  const handleAddOption = () => {
    setOptions((prev) => [
      ...prev,
      { option_text: '', option_order: prev.length + 1, is_correct: false },
    ]);
  };

  const handleRemoveOption = (index: number) => {
    if (options.length <= 2) {
      setError('A minimum of 2 options is required for choice-based questions.');
      return;
    }
    const updated = options.filter((_, i) => i !== index).map((opt, i) => ({
      ...opt,
      option_order: i + 1,
    }));
    setOptions(updated);
  };

  const handleOptionTextChange = (index: number, text: string) => {
    const updated = [...options];
    updated[index].option_text = text;
    setOptions(updated);
  };

  const handleOptionCorrectChange = (index: number, isCorrect: boolean) => {
    if (questionType === 'MCQ') {
      const updated = options.map((opt, i) => ({
        ...opt,
        is_correct: i === index ? isCorrect : false,
      }));
      setOptions(updated);
    } else if (questionType === 'MULTI_SELECT') {
      const updated = [...options];
      updated[index].is_correct = isCorrect;
      setOptions(updated);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!questionText.trim()) {
      setError('Question text is required.');
      return;
    }
    if (!subject.trim()) {
      setError('Subject is required.');
      return;
    }
    if (marks <= 0) {
      setError('Marks must be greater than 0.');
      return;
    }

    let payloadOptions: QuestionOptionInput[] | undefined = undefined;

    if (questionType === 'MCQ') {
      if (options.length < 2) {
        setError('MCQ questions require at least 2 options.');
        return;
      }
      if (options.some((o) => !o.option_text.trim())) {
        setError('All option text fields must be filled.');
        return;
      }
      const correctCount = options.filter((o) => o.is_correct).length;
      if (correctCount !== 1) {
        setError('MCQ questions must have exactly 1 correct option selected.');
        return;
      }
      payloadOptions = options;
    } else if (questionType === 'MULTI_SELECT') {
      if (options.length < 2) {
        setError('MULTI_SELECT questions require at least 2 options.');
        return;
      }
      if (options.some((o) => !o.option_text.trim())) {
        setError('All option text fields must be filled.');
        return;
      }
      const correctCount = options.filter((o) => o.is_correct).length;
      if (correctCount < 2) {
        setError('MULTI_SELECT questions require at least 2 correct options selected.');
        return;
      }
      payloadOptions = options;
    }

    setLoading(true);

    try {
      if (initialData) {
        const updateData: QuestionUpdateInput = {
          question_text: questionText,
          subject,
          topic: topic.trim() || undefined,
          question_type: questionType,
          difficulty,
          marks,
          negative_marks: negativeMarks,
          model_answer: modelAnswer.trim() || undefined,
          explanation: explanation.trim() || undefined,
          options: payloadOptions,
        };
        await questionsAPI.update(initialData.id, updateData);
      } else {
        const createData: QuestionCreateInput = {
          question_text: questionText,
          subject,
          topic: topic.trim() || undefined,
          question_type: questionType,
          difficulty,
          marks,
          negative_marks: negativeMarks,
          model_answer: modelAnswer.trim() || undefined,
          explanation: explanation.trim() || undefined,
          options: payloadOptions,
        };
        await questionsAPI.create(createData);
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col my-8">
        <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-950/60 rounded-t-2xl">
          <h2 className="text-lg font-bold text-white">
            {initialData ? 'Edit Question' : 'Create New Question'}
          </h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-2xl font-bold leading-none"
          >
            &times;
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto flex-1 space-y-5 text-xs">
          {error && (
            <div className="p-3 bg-red-950/60 border border-red-800 text-red-300 rounded-xl">
              {error}
            </div>
          )}

          {/* Question Text */}
          <div>
            <label className="block font-semibold text-slate-300 mb-1">
              Question Text <span className="text-red-400">*</span>
            </label>
            <textarea
              rows={3}
              required
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              placeholder="Enter the question statement..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Metadata Row 1 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Subject <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Computer Networks"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-300 mb-1">Topic</label>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. TCP Congestion"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-300 mb-1">Question Type</label>
              <select
                value={questionType}
                onChange={(e) => setQuestionType(e.target.value as QuestionType)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="MCQ">MCQ (Single Choice)</option>
                <option value="MULTI_SELECT">Multi-Select Choice</option>
                <option value="SHORT_ANSWER">Short Answer</option>
                <option value="LONG_ANSWER">Long Answer</option>
                <option value="HANDWRITTEN">Handwritten Answer</option>
              </select>
            </div>
          </div>

          {/* Metadata Row 2 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">Difficulty</label>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value as DifficultyLevel)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="EASY">Easy</option>
                <option value="MEDIUM">Medium</option>
                <option value="HARD">Hard</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Marks <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                required
                value={marks}
                onChange={(e) => setMarks(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-300 mb-1">Negative Marks</label>
              <input
                type="number"
                step="0.25"
                min="0"
                value={negativeMarks}
                onChange={(e) => setNegativeMarks(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Question Options for MCQ & MULTI_SELECT */}
          {(questionType === 'MCQ' || questionType === 'MULTI_SELECT') && (
            <div className="border border-slate-800 bg-slate-950/60 rounded-xl p-4 space-y-3">
              <div className="flex justify-between items-center">
                <h3 className="text-xs font-bold text-indigo-300">
                  Options Configuration ({questionType === 'MCQ' ? 'Exactly 1 correct' : 'At least 2 correct'})
                </h3>
                <button
                  type="button"
                  onClick={handleAddOption}
                  className="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-semibold rounded-lg transition"
                >
                  + Add Option
                </button>
              </div>

              <div className="space-y-2">
                {options.map((opt, idx) => (
                  <div key={idx} className="flex items-center gap-2 bg-slate-900 p-2 rounded-xl border border-slate-800">
                    <span className="text-[10px] font-mono text-slate-400 w-6 text-center">
                      #{idx + 1}
                    </span>

                    <input
                      type="text"
                      required
                      placeholder={`Option ${idx + 1} text`}
                      value={opt.option_text}
                      onChange={(e) => handleOptionTextChange(idx, e.target.value)}
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                    />

                    <label className="flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded hover:bg-slate-800">
                      {questionType === 'MCQ' ? (
                        <input
                          type="radio"
                          name="mcq_correct"
                          checked={opt.is_correct}
                          onChange={(e) => handleOptionCorrectChange(idx, e.target.checked)}
                          className="text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700"
                        />
                      ) : (
                        <input
                          type="checkbox"
                          checked={opt.is_correct}
                          onChange={(e) => handleOptionCorrectChange(idx, e.target.checked)}
                          className="text-indigo-600 rounded focus:ring-indigo-500 bg-slate-950 border-slate-700"
                        />
                      )}
                      <span className="text-[11px] font-medium text-slate-300">Correct</span>
                    </label>

                    <button
                      type="button"
                      onClick={() => handleRemoveOption(idx)}
                      className="text-red-400 hover:text-red-300 p-1 text-sm font-bold"
                      title="Remove Option"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Notice for Handwritten */}
          {questionType === 'HANDWRITTEN' && (
            <div className="p-3 bg-amber-950/40 border border-amber-800/60 rounded-xl text-xs text-amber-300">
              <strong>Handwritten Answer Note:</strong> Student will write their response on paper and upload a photo/scan during the exam. Answer upload, scanning, and OCR features belong to future stage implementations.
            </div>
          )}

          {/* Model Answer & Explanation */}
          {(questionType === 'SHORT_ANSWER' || questionType === 'LONG_ANSWER' || questionType === 'HANDWRITTEN') && (
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Model Answer / Key Points
              </label>
              <textarea
                rows={3}
                value={modelAnswer}
                onChange={(e) => setModelAnswer(e.target.value)}
                placeholder="Key points expected in the answer..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}

          <div>
            <label className="block font-semibold text-slate-300 mb-1">Explanation</label>
            <textarea
              rows={2}
              value={explanation}
              onChange={(e) => setExplanation(e.target.value)}
              placeholder="Explanatory notes for students/evaluators..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-300 bg-slate-800 rounded-xl hover:bg-slate-700 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-500 disabled:opacity-50 transition shadow-md shadow-indigo-600/20"
            >
              {loading ? 'Saving...' : initialData ? 'Update Question' : 'Save Question'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
