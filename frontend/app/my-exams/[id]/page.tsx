'use client';

import React, { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { StudentExamDetail, studentExamsAPI, authAPI } from '@/lib/api';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { ArrowLeft, BookOpen, Clock, Award, Play, RotateCcw, CheckCircle2, AlertCircle, FileText } from 'lucide-react';
import { ProctoringSetup } from '@/components/proctoring/ProctoringSetup';

export default function StudentExamDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter();
  const resolvedParams = use(params);
  const examId = resolvedParams.id;

  const [exam, setExam] = useState<StudentExamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [showProctoringSetup, setShowProctoringSetup] = useState(false);
  const [error, setError] = useState<string | null>(null);


  const [showIdentityGuard, setShowIdentityGuard] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | undefined>(undefined);

  const fetchExamDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await studentExamsAPI.getExamDetail(examId);
      setExam(data);
      if (data.active_session_id) {
        setActiveSessionId(data.active_session_id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load exam details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExamDetail();
  }, [examId]);

  const handleInitiateExam = async () => {
    setStarting(true);
    setError(null);
    try {
      const me = await authAPI.getMe();
      if (!me.is_face_registered) {
        setShowIdentityGuard(true);
        setStarting(false);
        return;
      }
      if (!exam) return;
      const session = await studentExamsAPI.startSession(exam.id);
      setActiveSessionId(session.id);
      setShowProctoringSetup(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to initialize exam session.');
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return (
      <AppShell title="Exam Preview" allowedRoles={['STUDENT']}>
        <div className="p-12 text-center text-slate-500 font-mono text-xs">Loading exam details...</div>
      </AppShell>
    );
  }

  if (error || !exam) {
    return (
      <AppShell title="Exam Preview" allowedRoles={['STUDENT']}>
        <div className="p-6 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs space-y-3">
          <p><strong>Error:</strong> {error || 'Exam not found or unavailable.'}</p>
          <button
            onClick={() => router.push('/my-exams')}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 text-white rounded-xl"
          >
            Back to My Exams
          </button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title={exam.title} allowedRoles={['STUDENT']}>
      <PageHeader
        title={exam.title}
        subtitle={`Subject: ${exam.subject} | Duration: ${exam.duration_minutes} minutes`}
        actions={
          <button
            onClick={() => router.push('/my-exams')}
            className="px-3.5 py-2 bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" /> Back to My Exams
          </button>
        }
      />

      <div className="max-w-4xl mx-auto space-y-6">
        {/* Overview Banner */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-6">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <span className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                {exam.subject}
              </span>
              <h2 className="text-xl font-bold text-white pt-1">{exam.title}</h2>
              {exam.description && (
                <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">{exam.description}</p>
              )}
            </div>

            <div>
              {exam.student_session_status === 'AVAILABLE' && (
                <button
                  onClick={handleInitiateExam}
                  disabled={starting}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50"
                >
                  <Play className="w-4 h-4" /> {starting ? 'Preparing Exam...' : 'Start Exam'}
                </button>
              )}

              {exam.student_session_status === 'IN_PROGRESS' && (
                <button
                  onClick={handleInitiateExam}
                  disabled={starting}
                  className="px-5 py-2.5 bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-amber-600/25 flex items-center gap-2 disabled:opacity-50"
                >
                  <RotateCcw className="w-4 h-4" />
                  {starting ? 'Initializing...' : exam.identity_verification_status === 'VERIFIED' ? 'Continue Active Exam' : 'Verify Identity & Continue'}
                </button>
              )}

              {exam.student_session_status === 'COMPLETED' && (
                <div className="px-4 py-2 bg-slate-950 border border-slate-800 text-slate-400 text-xs font-semibold rounded-xl flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Exam Submitted
                </div>
              )}
            </div>
          </div>

          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-800">
            <div className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-xl">
              <p className="text-[10px] text-slate-500 uppercase font-mono">Duration</p>
              <p className="text-base font-bold text-white mt-0.5 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" /> {exam.duration_minutes} min
              </p>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-xl">
              <p className="text-[10px] text-slate-500 uppercase font-mono">Total Questions</p>
              <p className="text-base font-bold text-white mt-0.5 flex items-center gap-1">
                <FileText className="w-3.5 h-3.5 text-slate-400" /> {exam.question_count}
              </p>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-xl">
              <p className="text-[10px] text-slate-500 uppercase font-mono">Total Marks</p>
              <p className="text-base font-bold text-indigo-400 mt-0.5 flex items-center gap-1">
                <Award className="w-3.5 h-3.5 text-indigo-400" /> {exam.total_marks} pts
              </p>
            </div>

            <div className="p-3 bg-slate-950/60 border border-slate-800/60 rounded-xl">
              <p className="text-[10px] text-slate-500 uppercase font-mono">Passing Marks</p>
              <p className="text-base font-bold text-emerald-400 mt-0.5">
                {exam.passing_marks} pts
              </p>
            </div>
          </div>
        </div>

        {/* Instructions Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-4">
          <h3 className="font-bold text-white text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-indigo-400" /> Important Examination Instructions
          </h3>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-300 leading-relaxed space-y-2">
            {exam.instructions ? (
              <p className="whitespace-pre-wrap">{exam.instructions}</p>
            ) : (
              <ul className="list-disc list-inside space-y-1.5 text-slate-400">
                <li>Read each question carefully before submitting your answer.</li>
                <li>You can navigate between questions freely using the question panel.</li>
                <li>Your answers are automatically saved as you select options or type.</li>
                <li>The exam timer runs continuously once started.</li>
                <li>Click <strong>Submit Exam</strong> when you have completed all questions.</li>
              </ul>
            )}
          </div>
        </div>

        {/* Safe Config Settings Preview */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-3">
          <h3 className="font-bold text-white text-xs">Exam Configuration</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${exam.negative_marking_enabled ? 'bg-amber-400' : 'bg-slate-600'}`} />
              <span>Negative Marking: <strong>{exam.negative_marking_enabled ? 'Enabled' : 'Disabled'}</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${exam.randomize_questions ? 'bg-indigo-400' : 'bg-slate-600'}`} />
              <span>Question Order: <strong>{exam.randomize_questions ? 'Randomized' : 'Standard'}</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${exam.proctoring_enabled ? 'bg-emerald-400' : 'bg-slate-600'}`} />
              <span>Session Monitoring: <strong>{exam.proctoring_enabled ? 'Active' : 'Standard'}</strong></span>
            </div>
          </div>
        </div>
      </div>

      <ProctoringSetup
        open={showProctoringSetup}
        examTitle={exam.title}
        examInstructions={exam.instructions}
        sessionId={activeSessionId || exam.active_session_id}
        onProceed={() => {
          setShowProctoringSetup(false);
          const sId = activeSessionId || exam.active_session_id;
          if (sId) {
            router.push(`/exam/${sId}`);
          }
        }}
        onCancel={() => setShowProctoringSetup(false)}
      />

      <ConfirmDialog
        open={showIdentityGuard}
        title="Identity verification setup required"
        description="You must register your face reference before attempting a proctored examination."
        confirmLabel="Register Face"
        cancelLabel="Cancel"
        variant="warning"
        onConfirm={() => {
          setShowIdentityGuard(false);
          router.push('/profile');
        }}
        onCancel={() => setShowIdentityGuard(false)}
      />
    </AppShell>
  );
}
