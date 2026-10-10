'use client';

import React, { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { Exam, ExamStatus, ExamQuestionInput, examsAPI, proctoringAPI, ExaminerProctoringEventItem, ProctoringEventType, ExamProctoringSummary, academicAPI, Department, Section, User as UserModel, ExamTargetType } from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import QuestionPicker from '@/components/exams/QuestionPicker';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { ArrowLeft, Save, Send, Archive, BookOpen, Clock, Settings, HelpCircle, Lock, RotateCcw, Trash2, ShieldCheck, Eye, Filter, Activity, User, AlertTriangle, AlertOctagon, Users, Check } from 'lucide-react';


export default function ExamDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const resolvedParams = use(params);
  const examId = resolvedParams.id;

  const [exam, setExam] = useState<Exam | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [instructions, setInstructions] = useState('');
  const [durationMinutes, setDurationMinutes] = useState<number>(60);
  const [startAt, setStartAt] = useState('');
  const [endAt, setEndAt] = useState('');
  const [passingMarks, setPassingMarks] = useState<number>(0.0);
  const [negativeMarkingEnabled, setNegativeMarkingEnabled] = useState(false);
  const [randomizeQuestions, setRandomizeQuestions] = useState(false);
  const [randomizeOptions, setRandomizeOptions] = useState(false);
  const [proctoringEnabled, setProctoringEnabled] = useState(true);
  const [maxTabSwitches, setMaxTabSwitches] = useState<number>(3);
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
  const [studentList, setStudentList] = useState<UserModel[]>([]);

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
  const [showArchiveModal, setShowArchiveModal] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [showUnarchiveModal, setShowUnarchiveModal] = useState(false);
  const [unarchiving, setUnarchiving] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Proctoring Events Log State
  const [proctoringEvents, setProctoringEvents] = useState<ExaminerProctoringEventItem[]>([]);
  const [eventsSummary, setEventsSummary] = useState<ExamProctoringSummary | null>(null);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsPage, setEventsPage] = useState(1);
  const [eventsTotalPages, setEventsTotalPages] = useState(1);
  const [eventFilter, setEventFilter] = useState<string>('');
  const [studentFilter, setStudentFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [studentOptions, setStudentOptions] = useState<{ id: string; name: string; email: string }[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(false);

  const fetchProctoringEvents = async () => {
    if (!examId) return;
    setLoadingEvents(true);
    try {
      const res = await proctoringAPI.getExamEvents(examId, {
        page: eventsPage,
        page_size: 10,
        event_type: eventFilter ? (eventFilter as ProctoringEventType) : undefined,
        student_id: studentFilter || undefined,
        severity: severityFilter || undefined,
        session_status: statusFilter || undefined,
      });
      setProctoringEvents(res.items);
      setEventsTotal(res.total);
      setEventsTotalPages(res.total_pages);
      if (res.summary) {
        setEventsSummary(res.summary);
      }

      // Collect unique student list for dropdown filter
      setStudentOptions((prev) => {
        const map = new Map(prev.map((s) => [s.id, s]));
        res.items.forEach((item) => {
          if (item.student_id) {
            map.set(item.student_id, {
              id: item.student_id,
              name: item.student_name || item.student_email,
              email: item.student_email,
            });
          }
        });
        return Array.from(map.values());
      });
    } catch (err) {
      console.warn('Failed to load proctoring events:', err);
    } finally {
      setLoadingEvents(false);
    }
  };

  useEffect(() => {
    if (exam) {
      fetchProctoringEvents();
    }
  }, [examId, eventsPage, eventFilter, studentFilter, severityFilter, statusFilter, exam]);

  const fetchExam = async () => {

    setLoading(true);
    setError(null);
    try {
      const data = await examsAPI.get(examId);
      setExam(data);

      // Populate Form State
      setTitle(data.title);
      setSubject(data.subject);
      setDescription(data.description || '');
      setInstructions(data.instructions || '');
      setDurationMinutes(data.duration_minutes);
      setStartAt(data.start_at ? data.start_at.slice(0, 16) : '');
      setEndAt(data.end_at ? data.end_at.slice(0, 16) : '');
      setPassingMarks(data.passing_marks);
      setNegativeMarkingEnabled(data.negative_marking_enabled);
      setRandomizeQuestions(data.randomize_questions);
      setRandomizeOptions(data.randomize_options);
      setProctoringEnabled(data.proctoring_enabled);
      setMaxTabSwitches(data.max_tab_switches ?? 3);

      setTargetType((data.target_type as ExamTargetType) || 'COLLEGE');
      setTargetDepartmentId(data.target_department_id || '');
      setTargetYearOfStudy(data.target_year_of_study ?? undefined);
      setTargetSectionId(data.target_section_id || '');
      setTargetStudentIds(data.target_student_ids || []);

      if (data.questions) {
        setQuestionInputs(
          data.questions.map((eq) => ({
            question_id: eq.question_id,
            question_order: eq.question_order,
            marks_override: eq.marks_override !== null && eq.marks_override !== undefined ? Number(eq.marks_override) : undefined,
          }))
        );
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load exam detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExam();
  }, [examId]);

  const isEditable = exam?.status === 'DRAFT';

  const buildTargetPayload = () => ({
    target_type: targetType,
    target_department_id: targetDepartmentId || undefined,
    target_year_of_study: targetYearOfStudy || undefined,
    target_section_id: targetSectionId || undefined,
    target_student_ids: targetType === 'SPECIFIC_STUDENTS' ? targetStudentIds : undefined,
  });

  const handleSaveChanges = async () => {
    if (!isEditable) return;
    setFormError(null);
    setSuccessMessage(null);

    if (!title.trim() || !subject.trim()) {
      setFormError('Title and Subject are required.');
      return;
    }

    setSaving(true);
    try {
      await examsAPI.update(examId, {
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
      setSuccessMessage('Exam updated successfully.');
      fetchExam();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to update exam.');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!isEditable) return;
    setFormError(null);
    setSuccessMessage(null);

    setPublishing(true);
    try {
      // First save changes
      await examsAPI.update(examId, {
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

      await examsAPI.publish(examId);
      setSuccessMessage('Exam published successfully.');
      fetchExam();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to publish exam.');
    } finally {
      setPublishing(false);
    }
  };

  const handleArchive = async () => {
    setArchiving(true);
    setFormError(null);
    setSuccessMessage(null);
    try {
      await examsAPI.archive(examId);
      setShowArchiveModal(false);
      setSuccessMessage('Exam archived successfully.');
      fetchExam();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to archive exam.');
    } finally {
      setArchiving(false);
    }
  };

  const handleUnarchive = async () => {
    setUnarchiving(true);
    setFormError(null);
    setSuccessMessage(null);
    try {
      await examsAPI.unarchive(examId);
      setShowUnarchiveModal(false);
      setSuccessMessage('Exam unarchived successfully and restored to Draft status.');
      fetchExam();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to unarchive exam.');
    } finally {
      setUnarchiving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    setFormError(null);
    try {
      await examsAPI.delete(examId);
      router.push('/exams');
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : 'Failed to delete exam.');
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <AppShell title="Exam Detail" allowedRoles={['EXAMINER']}>
        <div className="p-12 text-center text-slate-500 font-mono text-xs">Loading exam details...</div>
      </AppShell>
    );
  }

  if (error || !exam) {
    return (
      <AppShell title="Exam Detail" allowedRoles={['EXAMINER']}>
        <div className="p-6 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs space-y-3">
          <p><strong>Error:</strong> {error || 'Exam not found.'}</p>
          <button
            onClick={() => router.push('/exams')}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 text-white rounded-xl"
          >
            Back to Exams
          </button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={exam.title} allowedRoles={['EXAMINER']}>
      <PageHeader
        title={`${exam.title} ${exam.status !== 'DRAFT' ? '🔒' : '✏️'}`}
        subtitle={`Exam ID: ${exam.id} | Subject: ${exam.subject}`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.push('/exams')}
              className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Exams
            </button>
          </div>
        }
      />

      {/* Lock Notice for Published/Archived */}
      {!isEditable && (
        <div className="p-4 bg-indigo-950/60 border border-indigo-800/80 rounded-2xl text-indigo-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-indigo-400" />
            <span>
              This exam is <strong>{exam.status}</strong>. Structural editing is locked to preserve exam integrity.
            </span>
          </div>
          {exam.status === 'PUBLISHED' && (
            <button
              onClick={() => setShowArchiveModal(true)}
              className="px-3 py-1 bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-300 rounded-lg text-[11px]"
            >
              Archive Exam
            </button>
          )}
          {exam.status === 'ARCHIVED' && (
            <button
              onClick={() => setShowUnarchiveModal(true)}
              className="px-3 py-1 bg-amber-950/80 border border-amber-800 hover:bg-amber-900 text-amber-300 rounded-lg text-[11px] flex items-center gap-1 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Unarchive Exam
            </button>
          )}
        </div>
      )}

      {successMessage && (
        <div className="p-4 bg-emerald-950/60 border border-emerald-800 text-emerald-300 rounded-2xl text-xs">
          {successMessage}
        </div>
      )}

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
              <label className="block font-semibold text-slate-300 mb-1.5">Exam Title</label>
              <input
                type="text"
                disabled={!isEditable}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Subject</label>
              <input
                type="text"
                disabled={!isEditable}
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Description</label>
              <textarea
                rows={2}
                disabled={!isEditable}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Instructions</label>
              <textarea
                rows={2}
                disabled={!isEditable}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Schedule & Duration */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-400" /> 2. Duration & Schedule
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Duration (Minutes)</label>
              <input
                type="number"
                disabled={!isEditable}
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(parseInt(e.target.value) || 1)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Start Time</label>
              <input
                type="datetime-local"
                disabled={!isEditable}
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">End Time</label>
              <input
                type="datetime-local"
                disabled={!isEditable}
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>
          </div>
        </div>

        {/* Section 3: Exam Settings */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <Settings className="w-4 h-4 text-indigo-400" /> 3. Settings & Total Marks
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1.5">Passing Marks</label>
              <input
                type="number"
                step="0.5"
                min="0"
                disabled={!isEditable}
                value={passingMarks}
                onChange={(e) => setPassingMarks(parseFloat(e.target.value) || 0)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
              />
            </div>

            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="randomize_q"
                disabled={!isEditable}
                checked={randomizeQuestions}
                onChange={(e) => setRandomizeQuestions(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-indigo-500 disabled:opacity-60"
              />
              <label htmlFor="randomize_q" className="text-xs text-slate-300 cursor-pointer">
                Randomize Question Order
              </label>
            </div>

            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="randomize_opts"
                disabled={!isEditable}
                checked={randomizeOptions}
                onChange={(e) => setRandomizeOptions(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-indigo-500 disabled:opacity-60"
              />
              <label htmlFor="randomize_opts" className="text-xs text-slate-300 cursor-pointer">
                Randomize MCQ Options
              </label>
            </div>

            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="proctoring"
                disabled={!isEditable}
                checked={proctoringEnabled}
                onChange={(e) => setProctoringEnabled(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-indigo-500 disabled:opacity-60"
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
                  disabled={!isEditable}
                  value={maxTabSwitches}
                  onChange={(e) => setMaxTabSwitches(Math.min(20, Math.max(0, parseInt(e.target.value) || 0)))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
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
                disabled={!isEditable}
                value={targetType}
                onChange={(e) => {
                  setTargetType(e.target.value as ExamTargetType);
                  setTargetStudentIds([]);
                }}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
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
                  disabled={!isEditable}
                  value={targetDepartmentId}
                  onChange={(e) => setTargetDepartmentId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
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
                  disabled={!isEditable}
                  value={targetYearOfStudy || ''}
                  onChange={(e) => setTargetYearOfStudy(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60"
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
                  disabled={!isEditable || !targetDepartmentId}
                  value={targetSectionId}
                  onChange={(e) => setTargetSectionId(e.target.value)}
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
                          if (!isEditable) return;
                          if (isChecked) {
                            setTargetStudentIds(targetStudentIds.filter((id) => id !== s.id));
                          } else {
                            setTargetStudentIds([...targetStudentIds, s.id]);
                          }
                        }}
                        className={`p-2 rounded-lg text-xs flex items-center justify-between border transition ${
                          isEditable ? 'cursor-pointer' : 'cursor-not-allowed opacity-75'
                        } ${
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
            <HelpCircle className="w-4 h-4 text-indigo-400" /> 5. Linked Exam Questions
          </h3>

          <QuestionPicker
            selectedInputs={questionInputs}
            onChange={setQuestionInputs}
            readOnly={!isEditable}
          />
        </div>

        {/* Section 6: Proctoring Activity Log */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <h3 className="font-bold text-white text-xs flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" /> 6. Proctoring & System Event Monitoring
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Real-time integrity activity log, student session monitoring, and flag metrics.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={fetchProctoringEvents}
                disabled={loadingEvents}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-xl border border-slate-700 transition flex items-center gap-1.5 disabled:opacity-50 font-medium"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${loadingEvents ? 'animate-spin' : ''}`} /> Refresh Feed
              </button>
            </div>
          </div>

          {/* Metric Summary Cards */}
          {eventsSummary && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex items-center justify-between text-slate-400 text-[11px]">
                  <span>Total Events</span>
                  <Activity className="w-3.5 h-3.5 text-indigo-400" />
                </div>
                <div className="text-xl font-bold text-white font-mono">{eventsSummary.total_events}</div>
              </div>

              <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex items-center justify-between text-slate-400 text-[11px]">
                  <span>Monitored Students</span>
                  <User className="w-3.5 h-3.5 text-blue-400" />
                </div>
                <div className="text-xl font-bold text-white font-mono">{eventsSummary.monitored_students}</div>
              </div>

              <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex items-center justify-between text-slate-400 text-[11px]">
                  <span>Flagged Sessions</span>
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                </div>
                <div className="text-xl font-bold text-amber-300 font-mono">{eventsSummary.flagged_sessions}</div>
              </div>

              <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-1">
                <div className="flex items-center justify-between text-slate-400 text-[11px]">
                  <span>Auto-Submitted</span>
                  <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
                </div>
                <div className="text-xl font-bold text-rose-300 font-mono">{eventsSummary.auto_submitted_sessions}</div>
              </div>
            </div>
          )}

          {/* Filter Toolbar */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 pt-2">
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase mb-1">Student</label>
              <select
                value={studentFilter}
                onChange={(e) => {
                  setStudentFilter(e.target.value);
                  setEventsPage(1);
                }}
                className="w-full bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Students</option>
                {studentOptions.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.name} ({st.email})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase mb-1">Event Type</label>
              <select
                value={eventFilter}
                onChange={(e) => {
                  setEventFilter(e.target.value);
                  setEventsPage(1);
                }}
                className="w-full bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Event Types</option>
                <option value="CAMERA_READY">Camera Ready</option>
                <option value="MICROPHONE_READY">Microphone Ready</option>
                <option value="FACE_NOT_DETECTED">Face Not Detected</option>
                <option value="MULTIPLE_FACES_DETECTED">Multiple Faces</option>
                <option value="TAB_HIDDEN">Tab Switch (Hidden)</option>
                <option value="TAB_VISIBLE">Tab Returned (Visible)</option>
                <option value="FULLSCREEN_EXITED">Fullscreen Exited</option>
                <option value="FULLSCREEN_ENTERED">Fullscreen Entered</option>
                <option value="CAMERA_DISCONNECTED">Camera Disconnected</option>
                <option value="MICROPHONE_DISCONNECTED">Microphone Disconnected</option>
                <option value="TAB_SWITCH_LIMIT_EXCEEDED">Tab Switch Limit Exceeded</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase mb-1">Severity</label>
              <select
                value={severityFilter}
                onChange={(e) => {
                  setSeverityFilter(e.target.value);
                  setEventsPage(1);
                }}
                className="w-full bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Severities</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-slate-400 uppercase mb-1">Session Status</label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setEventsPage(1);
                }}
                className="w-full bg-slate-950 border border-slate-800 text-slate-300 text-xs rounded-xl px-2.5 py-1.5 focus:outline-none focus:border-indigo-500"
              >
                <option value="">All Session Statuses</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="SUBMITTED">Submitted</option>
                <option value="AUTO_SUBMITTED">Auto-Submitted (Limit Exceeded)</option>
                <option value="FLAGGED">Flagged Sessions</option>
              </select>
            </div>
          </div>

          {loadingEvents ? (
            <div className="p-8 text-center text-slate-500 font-mono text-xs">Loading event logs...</div>
          ) : proctoringEvents.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs border border-slate-800/60 rounded-xl bg-slate-950/40">
              No proctoring events match the selected filters.
            </div>
          ) : studentFilter ? (
            /* Student Timeline View */
            <div className="space-y-4 pt-2">
              <div className="p-3 bg-indigo-950/40 border border-indigo-900/60 rounded-xl flex items-center justify-between text-xs text-indigo-300">
                <span className="font-medium">
                  Timeline Mode: Showing events for {studentOptions.find((s) => s.id === studentFilter)?.name || 'Selected Student'}
                </span>
                <span className="font-mono text-[11px] text-indigo-400">{eventsTotal} events logged</span>
              </div>

              <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                {proctoringEvents.map((evt) => (
                  <div key={evt.id} className="relative flex items-start space-x-3 text-xs">
                    <span
                      className={`absolute -left-6 top-1 w-3 h-3 rounded-full border-2 border-slate-900 ${
                        evt.severity === 'CRITICAL' || evt.event_type === 'TAB_SWITCH_LIMIT_EXCEEDED'
                          ? 'bg-rose-500'
                          : evt.severity === 'HIGH' || evt.event_type.includes('HIDDEN') || evt.event_type.includes('NOT_DETECTED')
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                    />
                    <div className="flex-1 bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white">{evt.event_type}</span>
                        <span className="font-mono text-[10px] text-slate-400">
                          {new Date(evt.occurred_at || (evt as any).timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-[11px]">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${
                            evt.severity === 'CRITICAL' || evt.severity === 'HIGH'
                              ? 'bg-rose-950 text-rose-300 border-rose-800'
                              : evt.severity === 'MEDIUM'
                              ? 'bg-amber-950 text-amber-300 border-amber-800'
                              : 'bg-slate-800 text-slate-300 border-slate-700'
                          }`}
                        >
                          {evt.severity} SEVERITY
                        </span>

                        <span className="text-slate-400 font-mono text-[10px]">
                          Tabs: {evt.tab_switch_count}/{evt.max_tab_switches}
                        </span>

                        {evt.is_flagged && (
                          <span className="text-rose-400 font-medium text-[10px]">
                            Flagged: {evt.flag_reason || 'Flagged'}
                          </span>
                        )}
                      </div>

                      {evt.event_metadata && Object.keys(evt.event_metadata).length > 0 && (
                        <p className="font-mono text-[10px] text-slate-400 bg-slate-900/80 p-1.5 rounded border border-slate-800 truncate">
                          {JSON.stringify(evt.event_metadata)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Main Event Table */
            <div className="space-y-3">
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950 text-slate-400 font-mono text-[10px] uppercase border-b border-slate-800">
                    <tr>
                      <th className="px-4 py-2.5">Timestamp</th>
                      <th className="px-4 py-2.5">Student</th>
                      <th className="px-4 py-2.5">Event & Severity</th>
                      <th className="px-4 py-2.5">Tab Switches</th>
                      <th className="px-4 py-2.5">Session Status</th>
                      <th className="px-4 py-2.5">Metadata</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-slate-900/40">
                    {proctoringEvents.map((evt) => (
                      <tr key={evt.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-2.5 font-mono text-slate-400 text-[11px] whitespace-nowrap">
                          {new Date(evt.occurred_at || (evt as any).timestamp).toLocaleString()}
                        </td>
                        <td className="px-4 py-2.5 font-medium text-white whitespace-nowrap">
                          {evt.student_name || evt.student_email}
                          <span className="block text-[10px] text-slate-500 font-normal">{evt.student_email}</span>
                        </td>
                        <td className="px-4 py-2.5 whitespace-nowrap space-x-1.5">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                              evt.event_type.includes('NOT_DETECTED') || evt.event_type.includes('HIDDEN') || evt.event_type.includes('EXITED')
                                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                                : evt.event_type.includes('DISCONNECTED') || evt.event_type.includes('DENIED') || evt.event_type.includes('EXCEEDED')
                                ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            }`}
                          >
                            {evt.event_type}
                          </span>
                          <span
                            className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-mono border ${
                              evt.severity === 'CRITICAL' || evt.severity === 'HIGH'
                                ? 'bg-rose-950 text-rose-300 border-rose-800'
                                : evt.severity === 'MEDIUM'
                                ? 'bg-amber-950 text-amber-300 border-amber-800'
                                : 'bg-slate-800 text-slate-400 border-slate-700'
                            }`}
                          >
                            {evt.severity}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 font-mono text-[11px] text-slate-300 whitespace-nowrap">
                          <span className={evt.tab_switch_count > evt.max_tab_switches ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                            {evt.tab_switch_count} / {evt.max_tab_switches}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 whitespace-nowrap">
                          {evt.is_flagged ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-700">
                              <AlertOctagon className="w-3 h-3 text-rose-400" />
                              {evt.session_status} • FLAGGED
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                              {evt.session_status}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 font-mono text-[10px] text-slate-400 max-w-xs truncate">
                          {evt.event_metadata ? JSON.stringify(evt.event_metadata) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {eventsTotalPages > 1 && (
                <div className="flex items-center justify-between text-xs text-slate-400 pt-2">
                  <span>
                    Page {eventsPage} of {eventsTotalPages}
                  </span>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      disabled={eventsPage <= 1}
                      onClick={() => setEventsPage((p) => Math.max(1, p - 1))}
                      className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg disabled:opacity-50 transition"
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      disabled={eventsPage >= eventsTotalPages}
                      onClick={() => setEventsPage((p) => Math.min(eventsTotalPages, p + 1))}
                      className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg disabled:opacity-50 transition"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>


        {/* Action Buttons for Draft */}
        {isEditable && (
          <div className="flex justify-between items-center pt-4 border-t border-slate-800">
            <button
              type="button"
              disabled={saving || publishing || deleting}
              onClick={() => setShowDeleteModal(true)}
              className="px-4 py-2.5 text-xs font-semibold text-red-400 bg-red-950/40 border border-red-900/60 rounded-xl hover:bg-red-900/60 disabled:opacity-50 transition flex items-center gap-1.5"
            >
              <Trash2 className="w-4 h-4" /> Delete Draft
            </button>
            <div className="flex gap-3">
              <button
                type="button"
                disabled={saving || publishing || deleting}
                onClick={handleSaveChanges}
                className="px-5 py-2.5 text-xs font-semibold text-slate-200 bg-slate-800 border border-slate-700 rounded-xl hover:bg-slate-700 disabled:opacity-50 transition flex items-center gap-2"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button
                type="button"
                disabled={saving || publishing || deleting}
                onClick={handlePublish}
                className="px-5 py-2.5 text-xs font-semibold text-white bg-emerald-600 rounded-xl hover:bg-emerald-500 disabled:opacity-50 transition shadow-lg shadow-emerald-600/25 flex items-center gap-2"
              >
                <Send className="w-4 h-4" />
                {publishing ? 'Publishing...' : 'Publish Exam'}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Archive Confirmation Dialog */}
      <ConfirmDialog
        open={showArchiveModal}
        title="Archive Exam"
        description="Are you sure you want to archive this exam? Students will no longer be able to take archived exams."
        confirmLabel="Archive Exam"
        cancelLabel="Cancel"
        variant="warning"
        loading={archiving}
        onConfirm={handleArchive}
        onCancel={() => setShowArchiveModal(false)}
      />

      {/* Unarchive Confirmation Dialog */}
      <ConfirmDialog
        open={showUnarchiveModal}
        title="Unarchive Exam"
        description="Unarchive this exam and move it back to Draft?"
        confirmLabel="Unarchive"
        cancelLabel="Cancel"
        variant="warning"
        loading={unarchiving}
        onConfirm={handleUnarchive}
        onCancel={() => setShowUnarchiveModal(false)}
      />

      {/* Delete Draft Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteModal}
        title="Delete this draft exam permanently?"
        description="All exam configuration and question selections for this draft will be removed. Questions in your Question Bank will NOT be deleted."
        confirmLabel="Delete Exam"
        cancelLabel="Cancel"
        variant="danger"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteModal(false)}
      />
    </AppShell>
  );
}
