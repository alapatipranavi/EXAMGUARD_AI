'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ExamQuestionInput, examsAPI, academicAPI, Department, Section, User, ExamTargetType } from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import QuestionPicker from '@/components/exams/QuestionPicker';
import { ArrowLeft, Save, Send, BookOpen, Clock, Settings, HelpCircle, Users, Building2, Check } from 'lucide-react';

export default function CreateExamPage() {
  const router = useRouter();

  // Basic Details
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');

  // Duration & Schedule
  const [durationMinutes, setDurationMinutes] = useState<number>(60);
  const [startAt, setStartAt] = useState('');
  const [endAt, setEndAt] = useState('');

  // Settings
  const [passingMarks, setPassingMarks] = useState<number>(0.0);
  const [negativeMarkingEnabled, setNegativeMarkingEnabled] = useState(false);
  const [randomizeQuestions, setRandomizeQuestions] = useState(false);
  const [randomizeOptions, setRandomizeOptions] = useState(false);
  const [proctoringEnabled, setProctoringEnabled] = useState(true);
  const [maxTabSwitches, setMaxTabSwitches] = useState<number>(3);

  // Question Selection
  const [questionInputs, setQuestionInputs] = useState<ExamQuestionInput[]>([]);

  // Targeting Details
  const [targetType, setTargetType] = useState<ExamTargetType>('COLLEGE');
  const [targetDepartmentId, setTargetDepartmentId] = useState<string>('');
  const [targetYearOfStudy, setTargetYearOfStudy] = useState<number | undefined>(undefined);
  const [targetSectionId, setTargetSectionId] = useState<string>('');
  const [targetStudentIds, setTargetStudentIds] = useState<string[]>([]);

  // Targeting Dropdowns
  const [deptList, setDeptList] = useState<Department[]>([]);
  const [secList, setSecList] = useState<Section[]>([]);
  const [studentList, setStudentList] = useState<User[]>([]);

  React.useEffect(() => {
    academicAPI.getPublicDepartments().then(setDeptList).catch(console.error);
  }, []);

  React.useEffect(() => {
    if (targetDepartmentId) {
      academicAPI.getPublicSections(targetDepartmentId, targetYearOfStudy).then(setSecList).catch(console.error);
    } else {
      setSecList([]);
    }
  }, [targetDepartmentId, targetYearOfStudy]);

  React.useEffect(() => {
    if (targetType === 'SPECIFIC_STUDENTS') {
      academicAPI.getCollegeStudents({
        department_id: targetDepartmentId || undefined,
        year_of_study: targetYearOfStudy,
        section_id: targetSectionId || undefined,
      }).then(setStudentList).catch(console.error);
    }
  }, [targetType, targetDepartmentId, targetYearOfStudy, targetSectionId]);

  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const validateForm = () => {
    if (!title.trim()) return 'Exam Title is required.';
    if (!subject.trim()) return 'Subject is required.';
    if (durationMinutes <= 0) return 'Duration must be greater than 0 minutes.';
    if (startAt && endAt && new Date(endAt) <= new Date(startAt)) {
      return 'End time must be after start time.';
    }
    if (passingMarks < 0) return 'Passing marks cannot be negative.';
    if (maxTabSwitches < 0 || maxTabSwitches > 20) return 'Max Tab Switches must be between 0 and 20.';
    return null;
  };

  const buildTargetPayload = () => ({
    target_type: targetType,
    target_department_id: targetDepartmentId || undefined,
    target_year_of_study: targetYearOfStudy || undefined,
    target_section_id: targetSectionId || undefined,
    target_student_ids: targetType === 'SPECIFIC_STUDENTS' ? targetStudentIds : undefined,
  });

  const handleSaveDraft = async () => {
    setFormError(null);
    const err = validateForm();
    if (err) {
      setFormError(err);
      return;
    }

    setSaving(true);
    try {
      await examsAPI.create({
        title: title.trim(),
        subject: subject.trim(),
        description: description.trim() || undefined,
        instructions: instructions.trim() || undefined,
        duration_minutes: durationMinutes,
        start_at: startAt ? new Date(startAt).toISOString() : undefined,
        end_at: endAt ? new Date(endAt).toISOString() : undefined,
        passing_marks: passingMarks,
        negative_marking_enabled: negativeMarkingEnabled,
        randomize_questions: randomizeQuestions,
        randomize_options: randomizeOptions,
        proctoring_enabled: proctoringEnabled,
        max_tab_switches: maxTabSwitches,
        questions: questionInputs,
        ...buildTargetPayload(),
      });
      router.push('/exams');
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to save draft exam.');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    setFormError(null);
    const err = validateForm();
    if (err) {
      setFormError(err);
      return;
    }

    if (questionInputs.length === 0) {
      setFormError('At least one question must be selected before publishing an exam.');
      return;
    }

    setPublishing(true);
    try {
      const created = await examsAPI.create({
        title: title.trim(),
        subject: subject.trim(),
        description: description.trim() || undefined,
        instructions: instructions.trim() || undefined,
        duration_minutes: durationMinutes,
        start_at: startAt ? new Date(startAt).toISOString() : undefined,
        end_at: endAt ? new Date(endAt).toISOString() : undefined,
        passing_marks: passingMarks,
        negative_marking_enabled: negativeMarkingEnabled,
        randomize_questions: randomizeQuestions,
        randomize_options: randomizeOptions,
        proctoring_enabled: proctoringEnabled,
        max_tab_switches: maxTabSwitches,
        questions: questionInputs,
        ...buildTargetPayload(),
      });

      await examsAPI.publish(created.id);
      router.push('/exams');
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to publish exam.');
    } finally {
      setPublishing(false);
    }
  };

  return (
    <AppShell title="Create Exam" allowedRoles={['EXAMINER']}>
      <PageHeader
        title="Author New Exam 📝"
        subtitle="Configure exam details, duration, settings, and select questions from your bank."
        actions={
          <button
            onClick={() => router.push('/exams')}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Exams
          </button>
        }
      />

      {formError && (
        <div className="p-4 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs">
          {formError}
        </div>
      )}

      <div className="space-y-6">
        {/* Section 1: Basic Details */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-indigo-400" /> 1. Basic Exam Details
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">
                Exam Title <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Midterm Examination 2026"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">
                Subject <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Computer Science"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Description</label>
              <textarea
                rows={2}
                placeholder="Brief summary of the exam content..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Instructions for Students</label>
              <textarea
                rows={2}
                placeholder="Specific exam rules, permitted materials, or notes..."
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Duration & Schedule */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-400" /> 2. Duration & Schedule
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">
                Duration (Minutes) <span className="text-red-400">*</span>
              </label>
              <input
                type="number"
                min="1"
                required
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 1)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Start Time (Optional)</label>
              <input
                type="datetime-local"
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">End Time (Optional)</label>
              <input
                type="datetime-local"
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Section 3: Exam Settings */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <Settings className="w-4 h-4 text-indigo-400" /> 3. Exam Settings
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Passing Marks</label>
              <input
                type="number"
                step="0.5"
                min="0"
                value={passingMarks}
                onChange={(e) => setPassingMarks(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="randomize_q"
                checked={randomizeQuestions}
                onChange={(e) => setRandomizeQuestions(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="randomize_q" className="text-xs text-slate-300 cursor-pointer">
                Randomize Question Order
              </label>
            </div>

            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="randomize_opts"
                checked={randomizeOptions}
                onChange={(e) => setRandomizeOptions(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="randomize_opts" className="text-xs text-slate-300 cursor-pointer">
                Randomize MCQ Options
              </label>
            </div>

            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="proctoring"
                checked={proctoringEnabled}
                onChange={(e) => setProctoringEnabled(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-indigo-500"
              />
              <label htmlFor="proctoring" className="text-xs text-slate-300 cursor-pointer">
                Enable Integrity Proctoring
              </label>
            </div>

            {proctoringEnabled && (
              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Max Allowed Tab Switches (0–20)</label>
                <input
                  type="number"
                  min="0"
                  max="20"
                  value={maxTabSwitches}
                  onChange={(e) => setMaxTabSwitches(Math.min(20, Math.max(0, parseInt(e.target.value) || 0)))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}
          </div>
        </div>

        {/* Section 4: Target Audience & Student Scope */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-bold text-white text-xs flex items-center gap-2">
              <Users className="w-4 h-4 text-indigo-400" /> 4. Target Audience & Scope
            </h3>
            <span className="px-2.5 py-1 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 text-[11px] font-mono">
              Target Mode: {targetType}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Target Scope Type</label>
              <select
                value={targetType}
                onChange={(e) => {
                  setTargetType(e.target.value as ExamTargetType);
                  setTargetStudentIds([]);
                }}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="COLLEGE">Entire College</option>
                <option value="DEPARTMENT">Specific Department</option>
                <option value="YEAR">Department & Year of Study</option>
                <option value="SECTION">Specific Section</option>
                <option value="SPECIFIC_STUDENTS">Selected Specific Students</option>
              </select>
            </div>

            {(targetType === 'DEPARTMENT' || targetType === 'YEAR' || targetType === 'SECTION' || targetType === 'SPECIFIC_STUDENTS') && (
              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Department</label>
                <select
                  value={targetDepartmentId}
                  onChange={(e) => setTargetDepartmentId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- All Departments --</option>
                  {deptList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.code})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {(targetType === 'YEAR' || targetType === 'SECTION' || targetType === 'SPECIFIC_STUDENTS') && (
              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Year of Study</label>
                <select
                  value={targetYearOfStudy || ''}
                  onChange={(e) => setTargetYearOfStudy(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- All Years --</option>
                  <option value={1}>1st Year</option>
                  <option value={2}>2nd Year</option>
                  <option value={3}>3rd Year</option>
                  <option value={4}>4th Year</option>
                </select>
              </div>
            )}

            {(targetType === 'SECTION' || targetType === 'SPECIFIC_STUDENTS') && (
              <div>
                <label className="block font-semibold text-slate-300 mb-1.5">Section</label>
                <select
                  value={targetSectionId}
                  onChange={(e) => setTargetSectionId(e.target.value)}
                  disabled={!targetDepartmentId}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-40"
                >
                  <option value="">-- Select Section --</option>
                  {secList.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Specific Student Selection List */}
          {targetType === 'SPECIFIC_STUDENTS' && (
            <div className="space-y-2 pt-2">
              <label className="block font-semibold text-slate-300 text-xs">
                Select Students ({targetStudentIds.length} selected)
              </label>
              {studentList.length === 0 ? (
                <p className="text-slate-500 text-xs py-2">No students match current filter criteria.</p>
              ) : (
                <div className="max-h-48 overflow-y-auto bg-slate-950 border border-slate-800 rounded-xl p-2 space-y-1">
                  {studentList.map((s) => {
                    const isChecked = targetStudentIds.includes(s.id);
                    return (
                      <div
                        key={s.id}
                        onClick={() => {
                          if (isChecked) {
                            setTargetStudentIds(targetStudentIds.filter((id) => id !== s.id));
                          } else {
                            setTargetStudentIds([...targetStudentIds, s.id]);
                          }
                        }}
                        className={`p-2 rounded-lg text-xs cursor-pointer flex items-center justify-between border transition ${
                          isChecked
                            ? 'bg-indigo-600/20 border-indigo-500/40 text-white'
                            : 'bg-slate-900 border-slate-800/80 text-slate-300 hover:bg-slate-800'
                        }`}
                      >
                        <div>
                          <span className="font-semibold">{s.first_name} {s.last_name}</span>
                          <span className="text-slate-400 text-[10px] font-mono ml-2">({s.email})</span>
                        </div>
                        {isChecked && <Check className="w-4 h-4 text-indigo-400" />}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Section 5: Question Selection */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <HelpCircle className="w-4 h-4 text-indigo-400" /> 5. Question Selection
          </h3>

          <QuestionPicker
            selectedInputs={questionInputs}
            onChange={setQuestionInputs}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={() => router.push('/exams')}
            className="px-4 py-2.5 text-xs font-semibold text-slate-300 bg-slate-800 rounded-xl hover:bg-slate-700 transition"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={saving || publishing}
            onClick={handleSaveDraft}
            className="px-5 py-2.5 text-xs font-semibold text-slate-200 bg-slate-800 border border-slate-700 rounded-xl hover:bg-slate-700 disabled:opacity-50 transition flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving Draft...' : 'Save Draft'}
          </button>
          <button
            type="button"
            disabled={saving || publishing}
            onClick={handlePublish}
            className="px-5 py-2.5 text-xs font-semibold text-white bg-emerald-600 rounded-xl hover:bg-emerald-500 disabled:opacity-50 transition shadow-lg shadow-emerald-600/25 flex items-center gap-2"
          >
            <Send className="w-4 h-4" />
            {publishing ? 'Publishing...' : 'Publish Exam'}
          </button>
        </div>
      </div>
    </AppShell>
  );
}
