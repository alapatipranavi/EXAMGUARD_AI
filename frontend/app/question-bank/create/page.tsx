'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  QuestionType,
  DifficultyLevel,
  QuestionOptionInput,
  QuestionCreateInput,
  questionsAPI,
  aiQuestionsAPI,
} from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import { Sparkles, Save, ArrowLeft, Bot } from 'lucide-react';

export default function CreateQuestionPage() {
  const router = useRouter();

  // Form state
  const [questionText, setQuestionText] = useState('');
  const [subject, setSubject] = useState('');
  const [topic, setTopic] = useState('');
  const [questionType, setQuestionType] = useState<QuestionType>('MCQ');
  const [difficulty, setDifficulty] = useState<DifficultyLevel>('MEDIUM');
  const [marks, setMarks] = useState<number>(2.0);
  const [negativeMarks, setNegativeMarks] = useState<number>(0.0);
  const [modelAnswer, setModelAnswer] = useState('');
  const [explanation, setExplanation] = useState('');
  const [options, setOptions] = useState<QuestionOptionInput[]>([
    { option_text: '', option_order: 1, is_correct: true },
    { option_text: '', option_order: 2, is_correct: false },
  ]);

  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // AI Assistant state
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const handleAddOption = () => {
    setOptions((prev) => [
      ...prev,
      { option_text: '', option_order: prev.length + 1, is_correct: false },
    ]);
  };

  const handleRemoveOption = (index: number) => {
    if (options.length <= 2) {
      setFormError('A minimum of 2 options is required for choice-based questions.');
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

  const handleAIAssistantAction = async (action: string) => {
    setAiError(null);
    if (!questionText.trim()) {
      setAiError('Please enter a question statement first before using AI Assistant.');
      return;
    }

    setAiLoading(true);
    try {
      const res = await aiQuestionsAPI.assist({
        action,
        question_text: questionText,
        subject: subject.trim() || undefined,
        topic: topic.trim() || undefined,
        question_type: questionType,
        current_options: options,
        current_model_answer: modelAnswer.trim() || undefined,
      });

      if (res.improved_question_text) {
        setQuestionText(res.improved_question_text);
      }
      if (res.suggested_options && res.suggested_options.length > 0) {
        setOptions(res.suggested_options);
      }
      if (res.suggested_explanation) {
        setExplanation(res.suggested_explanation);
      }
      if (res.suggested_model_answer) {
        setModelAnswer(res.suggested_model_answer);
      }
    } catch (err: unknown) {
      setAiError(err instanceof Error ? err.message : 'AI Assistant action failed.');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!questionText.trim()) {
      setFormError('Question statement is required.');
      return;
    }
    if (!subject.trim()) {
      setFormError('Subject is required.');
      return;
    }
    if (marks <= 0) {
      setFormError('Marks must be greater than 0.');
      return;
    }

    let payloadOptions: QuestionOptionInput[] | undefined = undefined;

    if (questionType === 'MCQ') {
      if (options.length < 2) {
        setFormError('MCQ questions require at least 2 options.');
        return;
      }
      if (options.some((o) => !o.option_text.trim())) {
        setFormError('All option fields must be filled.');
        return;
      }
      const correctCount = options.filter((o) => o.is_correct).length;
      if (correctCount !== 1) {
        setFormError('MCQ questions must have exactly 1 correct option selected.');
        return;
      }
      payloadOptions = options;
    } else if (questionType === 'MULTI_SELECT') {
      if (options.length < 2) {
        setFormError('MULTI_SELECT questions require at least 2 options.');
        return;
      }
      if (options.some((o) => !o.option_text.trim())) {
        setFormError('All option fields must be filled.');
        return;
      }
      const correctCount = options.filter((o) => o.is_correct).length;
      if (correctCount < 2) {
        setFormError('MULTI_SELECT questions require at least 2 correct options selected.');
        return;
      }
      payloadOptions = options;
    }

    setSaving(true);
    try {
      const createData: QuestionCreateInput = {
        question_text: questionText,
        subject,
        topic: topic.trim() || undefined,
        question_type: questionType,
        difficulty,
        source: 'MANUAL',
        marks,
        negative_marks: negativeMarks,
        model_answer: modelAnswer.trim() || undefined,
        explanation: explanation.trim() || undefined,
        options: payloadOptions,
      };
      await questionsAPI.create(createData);
      router.push('/question-bank');
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to create question.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell title="Create Question" allowedRoles={['EXAMINER']}>
      <PageHeader
        title="Create Question"
        subtitle="Author a new assessment question with manual precision or AI assistance."
        actions={
          <button
            onClick={() => router.push('/question-bank')}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" /> Question Bank
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: Question Form */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-6">
          {formError && (
            <div className="p-4 bg-red-950/60 border border-red-800 text-red-300 rounded-xl text-xs">
              {formError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6 text-xs">
            {/* Question Statement */}
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">
                Question Statement <span className="text-red-400">*</span>
              </label>
              <textarea
                rows={4}
                required
                value={questionText}
                onChange={(e) => setQuestionText(e.target.value)}
                placeholder="Enter the full question statement..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Metadata Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">
                  Subject <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. Computer Science"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Topic</label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Data Structures"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Question Type</label>
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

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Difficulty</label>
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
                <label className="block font-semibold text-slate-300 mb-1.5">
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
                <label className="block font-semibold text-slate-300 mb-1.5">Negative Marks</label>
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

            {/* Option Editor for Choice Types */}
            {(questionType === 'MCQ' || questionType === 'MULTI_SELECT') && (
              <div className="border border-slate-800 bg-slate-950/60 rounded-xl p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="text-xs font-bold text-indigo-300">
                    Option Choices ({questionType === 'MCQ' ? 'Exactly 1 correct' : 'At least 2 correct'})
                  </h4>
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
                            name="manual_mcq_correct"
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
              <div className="p-3.5 bg-amber-950/40 border border-amber-800/60 rounded-xl text-xs text-amber-300 leading-relaxed">
                <strong>Handwritten Response Notice:</strong> Handwritten responses will be captured through the future secure exam-session workflow. Camera scanning and upload are not part of Question Bank creation.
              </div>
            )}

            {/* Model Answer & Explanation */}
            {(questionType === 'SHORT_ANSWER' || questionType === 'LONG_ANSWER' || questionType === 'HANDWRITTEN') && (
              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Model Answer / Key Rubrics</label>
                <textarea
                  rows={3}
                  value={modelAnswer}
                  onChange={(e) => setModelAnswer(e.target.value)}
                  placeholder="Key points expected in the answer..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Explanation</label>
              <textarea
                rows={2}
                value={explanation}
                onChange={(e) => setExplanation(e.target.value)}
                placeholder="Explanatory notes for students/evaluators..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => router.push('/question-bank')}
                className="px-4 py-2.5 text-xs font-semibold text-slate-300 bg-slate-800 rounded-xl hover:bg-slate-700 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-5 py-2.5 text-xs font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-500 disabled:opacity-50 transition shadow-lg shadow-indigo-600/25 flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save Question'}
              </button>
            </div>
          </form>
        </div>

        {/* Right Side: AI Authoring Assistant Panel */}
        <div className="space-y-4">
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm space-y-4">
            <div className="flex items-center gap-2 text-purple-400">
              <Bot className="w-5 h-5" />
              <h3 className="text-sm font-bold text-white">AI Authoring Assistant ✨</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Use AI suggestions to enhance, format, or generate options for your current question draft.
            </p>

            {aiError && (
              <div className="p-3 bg-red-950/60 border border-red-800 text-red-300 rounded-xl text-xs leading-normal">
                {aiError}
              </div>
            )}

            <div className="space-y-2">
              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('improve')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Improve Question Statement</span>
              </button>

              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('generate_options')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Generate Option Choices</span>
              </button>

              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('suggest_explanation')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Suggest Explanation</span>
              </button>

              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('suggest_model_answer')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Generate Model Answer</span>
              </button>

              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('increase_difficulty')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Increase Difficulty</span>
              </button>

              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('simplify')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Simplify Language</span>
              </button>

              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('make_application_based')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Make Application-Based</span>
              </button>

              <button
                type="button"
                disabled={aiLoading}
                onClick={() => handleAIAssistantAction('generate_similar')}
                className="w-full text-left p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900 text-xs text-slate-200 hover:text-white transition flex items-center justify-between group disabled:opacity-50"
              >
                <span>✨ Generate Similar Variation</span>
              </button>
            </div>

            {aiLoading && (
              <p className="text-xs text-purple-400 font-mono flex items-center gap-2 animate-pulse pt-2">
                <Sparkles className="w-4 h-4 animate-spin" /> Processing AI suggestion...
              </p>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
