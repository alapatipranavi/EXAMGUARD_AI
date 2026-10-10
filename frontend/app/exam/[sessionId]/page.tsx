'use client';

import React, { useState, useEffect, use, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { ExamSessionResponse, StudentQuestion, studentExamsAPI, proctoringAPI, ProctoringEventType } from '@/lib/api';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { ProctoringCamera } from '@/components/proctoring/ProctoringCamera';
import { ProctoringSetup } from '@/components/proctoring/ProctoringSetup';
import HandwrittenAnswerSection from '@/components/exam/HandwrittenAnswerSection';
import {
  ShieldCheck,
  Clock,
  ArrowLeft,
  ArrowRight,
  Bookmark,
  CheckCircle2,
  AlertTriangle,
  Send,
  HelpCircle,
  FileText,
  AlertCircle,
  Eye,
  RotateCcw,
  Sparkles,
  X,
} from 'lucide-react';

export default function ExamTakingPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const router = useRouter();
  const resolvedParams = use(params);
  const sessionId = resolvedParams.sessionId;

  const [session, setSession] = useState<ExamSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Question navigation state
  const [currentIndex, setCurrentIndex] = useState(0);

  // Answers State: question_id -> { selected_option_ids: string[]; text_answer: string; answer_image_url?: string | null; ocr_status?: string | null; ocr_confidence?: number | null }
  const [answersMap, setAnswersMap] = useState<
    Record<
      string,
      {
        selected_option_ids: string[];
        text_answer: string;
        answer_image_url?: string | null;
        ocr_status?: string | null;
        ocr_confidence?: number | null;
      }
    >
  >({});

  // Marked for Review State: Set of question_ids
  const [markedSet, setMarkedSet] = useState<Set<string>>(new Set());

  // Auto-save Status: "saved" | "saving" | "error"
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'error'>('saved');

  // Timer State (seconds remaining)
  const [remainingSeconds, setRemainingSeconds] = useState<number>(0);

  // Modals & Proctoring State
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [noticeMessage, setNoticeMessage] = useState<string | null>(null);
  const [proctoringWarning, setProctoringWarning] = useState<string | null>(null);

  // Handwritten Capture Mode State for Proctoring Warning Suppression
  const [isHandwrittenCaptureActive, setIsHandwrittenCaptureActive] = useState(false);
  const isHandwrittenCaptureActiveRef = useRef(isHandwrittenCaptureActive);

  useEffect(() => {
    isHandwrittenCaptureActiveRef.current = isHandwrittenCaptureActive;
    if (isHandwrittenCaptureActive) {
      // Clear active Face Not Detected or Book/Notes warning banners when student enters paper capture mode
      setProctoringWarning((prev) => {
        if (!prev) return null;
        const lower = prev.toLowerCase();
        if (lower.includes('face not detected') || lower.includes('book') || lower.includes('notes')) {
          return null;
        }
        return prev;
      });
    }
  }, [isHandwrittenCaptureActive]);

  // Custom Tab Switch Warning Dialog State
  const [showTabSwitchDialog, setShowTabSwitchDialog] = useState(false);
  const [tabSwitchDialogData, setTabSwitchDialogData] = useState<{
    count: number;
    max: number;
    isFinalWarning: boolean;
  } | null>(null);

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastBrowserEventTimeRef = useRef<Record<string, number>>({});
  const isFinalizedRef = useRef<boolean>(false);
  const lastVisibilityStateRef = useRef<string>('visible');
  const visibilityHandlerRef = useRef<(() => void) | null>(null);
  const fullscreenHandlerRef = useRef<(() => void) | null>(null);
  const previousTabCountRef = useRef<number>(0);
  const pendingMaxSwitchesRef = useRef<number>(3);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // Behavioral event tracking refs
  const prevQuestionIdRef = useRef<string | null>(null);
  const prevIndexRef = useRef<number | null>(null);
  const lastLoggedViewQuestionIdRef = useRef<string | null>(null);

  // Centralized Proctoring Cleanup Function
  const cleanupProctoring = useCallback(() => {
    isFinalizedRef.current = true;

    // 1. Synchronously stop active MediaStream tracks (camera video & microphone audio)
    if (mediaStreamRef.current) {
      try {
        const tracks = mediaStreamRef.current.getTracks();
        tracks.forEach((track) => {
          try {
            track.enabled = false;
            track.stop();
          } catch (err) {
            console.warn('Error stopping track during cleanupProctoring:', err);
          }
        });
      } catch (err) {
        console.warn('Error stopping mediaStreamRef tracks during cleanup:', err);
      }
      mediaStreamRef.current = null;
    }

    // 2. Exit Fullscreen if currently active
    if (typeof document !== 'undefined' && document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }

    // 3. Remove event listeners from document
    if (typeof document !== 'undefined') {
      if (visibilityHandlerRef.current) {
        document.removeEventListener('visibilitychange', visibilityHandlerRef.current);
        visibilityHandlerRef.current = null;
      }
      if (fullscreenHandlerRef.current) {
        document.removeEventListener('fullscreenchange', fullscreenHandlerRef.current);
        fullscreenHandlerRef.current = null;
      }
    }

    // 4. Dismiss warnings & dialogs
    setProctoringWarning(null);
    setShowTabSwitchDialog(false);

    // 5. Set local session status to non-IN_PROGRESS so ProctoringCamera unmounts cleanly
    setSession((prev) => {
      if (!prev || prev.status !== 'IN_PROGRESS') return prev;
      return { ...prev, status: 'SUBMITTED' };
    });
  }, []);

  // Guarantee MediaStream hardware teardown when page component unmounts (navigating away)
  useEffect(() => {
    return () => {
      if (mediaStreamRef.current) {
        try {
          const tracks = mediaStreamRef.current.getTracks();
          tracks.forEach((track) => {
            try {
              track.enabled = false;
              track.stop();
            } catch (err) {
              console.warn('Error stopping track on page unmount:', err);
            }
          });
        } catch (err) {
          console.warn('Error stopping mediaStreamRef on page unmount:', err);
        }
        mediaStreamRef.current = null;
      }
    };
  }, []);

  const handleProctoringEventLogged = useCallback((type: ProctoringEventType, msg: string) => {
    if ((type === 'FACE_NOT_DETECTED' || type === 'BOOK_DETECTED') && isHandwrittenCaptureActiveRef.current) {
      return; // Suppress Face Not Detected and Book/Notes warning banners while handwritten capture mode is active
    }
    setProctoringWarning(msg);
  }, []);

  const handleProctoringStreamReady = useCallback((stream: MediaStream | null) => {
    mediaStreamRef.current = stream;
  }, []);

  const handleAutoSubmit = useCallback(
    (reason?: string) => {
      cleanupProctoring();
      const userMsg =
        reason === 'TAB_SWITCH_LIMIT_EXCEEDED'
          ? 'Your exam was automatically submitted because the maximum allowed tab switches was exceeded. Status: Flagged'
          : `Exam auto-submitted: ${reason || 'TAB_SWITCH_LIMIT_EXCEEDED'}`;
      setNoticeMessage(userMsg);
      setTimeout(() => {
        router.push('/dashboard');
      }, 2500);
    },
    [cleanupProctoring, router]
  );

  // Fetch Session Data
  const fetchSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await studentExamsAPI.getSession(sessionId);
      if (data.identity_verification_status !== 'VERIFIED') {
        setShowSetupModal(true);
        setLoading(false);
        return;
      }

      setSession(data);
      setShowSetupModal(false);
      setRemainingSeconds(data.remaining_seconds);
      previousTabCountRef.current = data.tab_switch_count || 0;
      pendingMaxSwitchesRef.current = data.max_tab_switches || 3;

      // Populate answers map
      const initialAnswers: Record<
        string,
        {
          selected_option_ids: string[];
          text_answer: string;
          answer_image_url?: string | null;
          ocr_status?: string | null;
          ocr_confidence?: number | null;
        }
      > = {};
      data.answers.forEach((ans) => {
        initialAnswers[ans.question_id] = {
          selected_option_ids: ans.selected_option_ids || [],
          text_answer: ans.text_answer || '',
          answer_image_url: ans.answer_image_url || null,
          ocr_status: ans.ocr_status || null,
          ocr_confidence: ans.ocr_confidence ?? null,
        };
      });
      setAnswersMap(initialAnswers);

      // Populate marked set
      const initialMarked = new Set(data.marked_for_review_question_ids || []);
      setMarkedSet(initialMarked);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : 'Failed to load exam session.';
      if (errMsg.includes('identity verification') || errMsg.includes('IDENTITY_VERIFICATION_REQUIRED')) {
        setShowSetupModal(true);
      } else {
        setError(errMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSession();
  }, [sessionId]);

  // Countdown Timer
  useEffect(() => {
    if (!session || session.status !== 'IN_PROGRESS' || remainingSeconds <= 0 || isFinalizedRef.current) return;

    const timer = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          cleanupProctoring();
          setNoticeMessage('Time is up. Your exam has been submitted automatically.');
          setTimeout(() => {
            router.push('/dashboard');
          }, 2000);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [session?.status, remainingSeconds, router, cleanupProctoring]);

  // Record Browser Proctoring Event
  const recordBrowserEvent = useCallback(
    async (eventType: ProctoringEventType, customWarningMsg?: string) => {
      if (isFinalizedRef.current || !session || session.status !== 'IN_PROGRESS') return;

      const isTabHidden = eventType === 'TAB_HIDDEN';
      const now = Date.now();
      const lastTime = lastBrowserEventTimeRef.current[eventType] || 0;

      // 30-second deduplication ONLY for non-TAB_HIDDEN events
      if (!isTabHidden && now - lastTime < 30000) return;
      lastBrowserEventTimeRef.current[eventType] = now;

      try {
        const res = await proctoringAPI.recordEvent(session.id, { event_type: eventType });

        let currentSwitches = session.tab_switch_count;
        if (res.tab_switch_count !== undefined) {
          currentSwitches = res.tab_switch_count;
          if (res.max_tab_switches !== undefined) {
            pendingMaxSwitchesRef.current = res.max_tab_switches;
          }
          setSession((prev) => (prev ? { ...prev, tab_switch_count: res.tab_switch_count! } : prev));
        }

        if (res.auto_submitted) {
          handleAutoSubmit(res.flag_reason || 'TAB_SWITCH_LIMIT_EXCEEDED');
          return;
        }

        if (eventType === 'TAB_HIDDEN') {
          const maxAllowed = res.max_tab_switches || session.max_tab_switches || 3;
          if (currentSwitches === maxAllowed) {
            setProctoringWarning('One more tab switch will automatically submit your exam.');
          } else if (currentSwitches < maxAllowed) {
            setProctoringWarning(`Exam window was left. Tab switch ${currentSwitches} of ${maxAllowed} recorded.`);
          }
        } else if (customWarningMsg) {
          setProctoringWarning(customWarningMsg);
        }
      } catch (err) {
        console.warn(`Failed to log browser event ${eventType}:`, err);
      }
    },
    [session, handleAutoSubmit]
  );

  // Monitor Tab Switching & Fullscreen Changes
  useEffect(() => {
    if (!session || session.status !== 'IN_PROGRESS' || isFinalizedRef.current) return;

    const handleVisibilityChange = async () => {
      if (isFinalizedRef.current) return;

      if (document.visibilityState === 'hidden') {
        if (lastVisibilityStateRef.current !== 'hidden') {
          lastVisibilityStateRef.current = 'hidden';
          recordBrowserEvent('TAB_HIDDEN');
        }
      } else if (document.visibilityState === 'visible') {
        if (lastVisibilityStateRef.current !== 'visible') {
          lastVisibilityStateRef.current = 'visible';
          recordBrowserEvent('TAB_VISIBLE');

          // Refresh authoritative session state from GET endpoint upon returning to exam tab
          try {
            const latestSession = await studentExamsAPI.getSession(sessionId);
            if (isFinalizedRef.current) return;

            const newCount = latestSession.tab_switch_count || 0;
            const maxAllowed = latestSession.max_tab_switches || 3;
            const prevCount = previousTabCountRef.current;

            setSession(latestSession);

            if (latestSession.status === 'AUTO_SUBMITTED' || latestSession.is_flagged || newCount > maxAllowed) {
              handleAutoSubmit(latestSession.flag_reason || 'TAB_SWITCH_LIMIT_EXCEEDED');
              return;
            }

            if (newCount > prevCount) {
              previousTabCountRef.current = newCount;
              setTabSwitchDialogData({
                count: newCount,
                max: maxAllowed,
                isFinalWarning: newCount === maxAllowed,
              });
              setShowTabSwitchDialog(true);
            }
          } catch (err) {
            console.warn('Failed to refresh session state on tab return:', err);
          }
        }
      }
    };

    const handleFullscreenChange = () => {
      if (isFinalizedRef.current) return;
      if (document.fullscreenElement) {
        setProctoringWarning(null);
        recordBrowserEvent('FULLSCREEN_ENTERED');
      } else {
        recordBrowserEvent(
          'FULLSCREEN_EXITED',
          'Fullscreen mode was exited. Please re-enter fullscreen for optimal exam environment.'
        );
      }
    };

    visibilityHandlerRef.current = handleVisibilityChange;
    fullscreenHandlerRef.current = handleFullscreenChange;

    document.addEventListener('visibilitychange', handleVisibilityChange);
    document.addEventListener('fullscreenchange', handleFullscreenChange);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [session?.status, recordBrowserEvent]);

  const handleReenterFullscreen = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } catch (err) {
      console.warn('Re-enter fullscreen failed:', err);
    }
  };


  // Log Behavioral Event (Stage 9.3)
  const logBehavioralEvent = useCallback(
    (eventType: ProctoringEventType, metadataJson?: Record<string, any>) => {
      if (isFinalizedRef.current || !session || session.status !== 'IN_PROGRESS') return;
      proctoringAPI
        .recordEvent(session.id, {
          event_type: eventType,
          metadata_json: metadataJson,
        })
        .catch((err) => {
          console.warn(`Failed to log behavioral event ${eventType}:`, err);
        });
    },
    [session]
  );

  // Monitor Question Viewing & Navigation
  useEffect(() => {
    if (!session || session.status !== 'IN_PROGRESS' || isFinalizedRef.current) return;
    const currentQ = session.questions[currentIndex];
    if (!currentQ) return;

    if (
      prevIndexRef.current !== null &&
      prevIndexRef.current !== currentIndex &&
      prevQuestionIdRef.current &&
      prevQuestionIdRef.current !== currentQ.id
    ) {
      logBehavioralEvent('QUESTION_NAVIGATION', {
        from_question_id: prevQuestionIdRef.current,
        to_question_id: currentQ.id,
        from_index: prevIndexRef.current,
        to_index: currentIndex,
      });
    }

    if (lastLoggedViewQuestionIdRef.current !== currentQ.id) {
      logBehavioralEvent('QUESTION_VIEWED', {
        question_id: currentQ.id,
        index: currentIndex,
      });
      lastLoggedViewQuestionIdRef.current = currentQ.id;
    }

    prevIndexRef.current = currentIndex;
    prevQuestionIdRef.current = currentQ.id;
  }, [currentIndex, session, logBehavioralEvent]);

  // Save Answer Function
  const saveAnswerToServer = useCallback(
    async (qId: string, selectedOptIds: string[], textAns: string) => {
      if (!session || session.status !== 'IN_PROGRESS') return;
      setSaveStatus('saving');
      try {
        await studentExamsAPI.saveAnswer(session.id, qId, {
          selected_option_ids: selectedOptIds || [],
          text_answer: textAns || '',
        });
        setSaveStatus('saved');
      } catch (err: unknown) {
        setSaveStatus('error');
      }
    },
    [session]
  );

  // Option Change Handler (MCQ & Multi-Select)
  const handleOptionChange = (questionId: string, optionId: string, isMulti: boolean) => {
    if (!session || session.status !== 'IN_PROGRESS') return;

    const current = answersMap[questionId] || { selected_option_ids: [], text_answer: '' };
    const wasAnswered =
      (current.selected_option_ids && current.selected_option_ids.length > 0) ||
      (current.text_answer && current.text_answer.trim().length > 0);

    let updatedSelected: string[] = [];

    if (isMulti) {
      if (current.selected_option_ids.includes(optionId)) {
        updatedSelected = current.selected_option_ids.filter((id) => id !== optionId);
      } else {
        updatedSelected = [...current.selected_option_ids, optionId];
      }
    } else {
      updatedSelected = [optionId];
    }

    const updated = { ...current, selected_option_ids: updatedSelected };
    setAnswersMap((prev) => ({ ...prev, [questionId]: updated }));

    const isNowAnswered = updatedSelected.length > 0 || (current.text_answer && current.text_answer.trim().length > 0);

    if (!wasAnswered && isNowAnswered) {
      logBehavioralEvent('ANSWER_CREATED', { question_id: questionId });
    } else if (wasAnswered && isNowAnswered) {
      logBehavioralEvent('ANSWER_CHANGED', { question_id: questionId });
    } else if (wasAnswered && !isNowAnswered) {
      logBehavioralEvent('ANSWER_CLEARED', { question_id: questionId });
    }

    // Instant save for options
    saveAnswerToServer(questionId, updatedSelected, current.text_answer || '');
  };

  // Text Answer Change Handler (Short & Long Answer with Debounce)
  const handleTextChange = (questionId: string, text: string) => {
    if (!session || session.status !== 'IN_PROGRESS') return;

    const current = answersMap[questionId] || { selected_option_ids: [], text_answer: '' };
    const wasAnswered =
      (current.selected_option_ids && current.selected_option_ids.length > 0) ||
      (current.text_answer && current.text_answer.trim().length > 0);

    const updated = { ...current, text_answer: text };
    setAnswersMap((prev) => ({ ...prev, [questionId]: updated }));

    const isNowAnswered =
      (current.selected_option_ids && current.selected_option_ids.length > 0) || text.trim().length > 0;

    if (!wasAnswered && isNowAnswered) {
      logBehavioralEvent('ANSWER_CREATED', { question_id: questionId });
    }

    setSaveStatus('saving');

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    const currentOptIds = current.selected_option_ids || [];
    debounceTimerRef.current = setTimeout(() => {
      if (wasAnswered && isNowAnswered) {
        logBehavioralEvent('ANSWER_CHANGED', { question_id: questionId });
      }
      saveAnswerToServer(questionId, currentOptIds, text);
    }, 800);
  };

  // Clear Answer Handler (MCQ, Multi-Select, Short/Long Answer)
  const handleClearAnswer = (questionId: string) => {
    if (!session || session.status !== 'IN_PROGRESS') return;

    const current = answersMap[questionId] || { selected_option_ids: [], text_answer: '' };
    const wasAnswered =
      (current.selected_option_ids && current.selected_option_ids.length > 0) ||
      (current.text_answer && current.text_answer.trim().length > 0);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    const cleared = { selected_option_ids: [], text_answer: '' };
    setAnswersMap((prev) => ({ ...prev, [questionId]: cleared }));

    if (wasAnswered) {
      logBehavioralEvent('ANSWER_CLEARED', { question_id: questionId });
    }

    saveAnswerToServer(questionId, [], '');
  };

  // Toggle Mark for Review
  const handleToggleReview = async (questionId: string) => {
    if (!session || session.status !== 'IN_PROGRESS') return;

    const isMarked = markedSet.has(questionId);
    const updatedSet = new Set(markedSet);
    if (isMarked) {
      updatedSet.delete(questionId);
    } else {
      updatedSet.add(questionId);
    }
    setMarkedSet(updatedSet);

    try {
      await studentExamsAPI.toggleReview(session.id, questionId, !isMarked);
    } catch (err: unknown) {
      // Revert if request fails
      setMarkedSet(markedSet);
    }
  };

  // Submit Session Handler
  const handleSubmitExam = async () => {
    if (!session) return;
    setSubmitting(true);
    setError(null);
    try {
      await studentExamsAPI.submitSession(session.id);
      cleanupProctoring();
      setShowSubmitModal(false);
      setShowReviewModal(false);
      setNoticeMessage('Exam submitted successfully.');
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit exam.');
      setShowSubmitModal(false);
    } finally {
      setSubmitting(false);
    }
  };

  const formatTimer = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="text-center font-mono text-xs text-slate-400 space-y-2">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p>Loading exam environment...</p>
        </div>
      </div>
    );
  }

  if (showSetupModal) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <ProctoringSetup
          open={true}
          examTitle={session?.exam_title || 'Identity Verification Required'}
          sessionId={sessionId}
          onProceed={() => {
            setShowSetupModal(false);
            fetchSession();
          }}
          onCancel={() => {
            router.push('/my-exams');
          }}
        />
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 text-xs space-y-4">
          <div className="flex items-center gap-3 text-red-400">
            <AlertTriangle className="w-6 h-6" />
            <h3 className="font-bold text-white text-sm">Exam Session Notice</h3>
          </div>
          <p className="text-slate-300">{error || 'Session failed to load.'}</p>
          <button
            onClick={() => router.push('/my-exams')}
            className="w-full py-2 bg-slate-800 text-white font-semibold rounded-xl hover:bg-slate-700"
          >
            Back to My Exams
          </button>
        </div>
      </div>
    );
  }

  const isCompleted = session.status !== 'IN_PROGRESS' && session.status !== 'CREATED';
  const currentQuestion = session.questions[currentIndex];
  const totalQuestions = session.questions.length;
  const currentAns = currentQuestion ? answersMap[currentQuestion.id] : null;

  const isAnswered = (qId: string) => {
    const a = answersMap[qId];
    if (!a) return false;
    return (
      (a.selected_option_ids && a.selected_option_ids.length > 0) ||
      (a.text_answer && a.text_answer.trim().length > 0) ||
      Boolean(a.answer_image_url)
    );
  };

  // Question Statistics
  let answeredCount = 0;
  let unansweredCount = 0;
  let markedCount = 0;
  let answeredAndMarkedCount = 0;

  session.questions.forEach((q) => {
    const ans = isAnswered(q.id);
    const mrk = markedSet.has(q.id);
    if (ans && mrk) answeredAndMarkedCount++;
    else if (mrk) markedCount++;
    else if (ans) answeredCount++;
    else unansweredCount++;
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 flex flex-col font-sans">
      {/* Notice Banner */}
      {noticeMessage && (
        <div className="bg-indigo-600 text-white px-4 py-2.5 text-xs font-semibold text-center flex items-center justify-center gap-2 z-50">
          <CheckCircle2 className="w-4 h-4" />
          <span>{noticeMessage} Redirecting to dashboard...</span>
        </div>
      )}

      {/* Neutral Proctoring Warning Banner */}
      {proctoringWarning && (
        <div className="bg-amber-950/90 border-b border-amber-800 text-amber-200 px-6 py-2.5 text-xs flex items-center justify-between z-50 shadow-lg backdrop-blur-md">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 animate-pulse" />
            <span>{proctoringWarning}</span>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleReenterFullscreen}
              className="px-2.5 py-1 bg-amber-900 hover:bg-amber-800 border border-amber-700 text-amber-100 rounded text-[11px] font-semibold transition"
            >
              Re-enter Fullscreen
            </button>
            <button
              onClick={() => setProctoringWarning(null)}
              className="text-amber-400 hover:text-amber-200 p-1"
              title="Dismiss notice"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}


      {/* Exam Header Bar */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-3 sticky top-0 z-40 flex items-center justify-between shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600/20 border border-indigo-500/30 rounded-xl">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-white">{session.exam_title}</h1>
            <p className="text-[10px] text-slate-400 font-mono">Subject: {session.exam_subject}</p>
          </div>
        </div>

        {/* Center: Live Timer & Tab Switch Counter */}
        {!isCompleted ? (
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 px-4 py-1.5 rounded-full">
              <Clock className={`w-4 h-4 ${remainingSeconds < 300 ? 'text-red-400 animate-pulse' : 'text-amber-400'}`} />
              <span className={`font-mono font-bold text-xs ${remainingSeconds < 300 ? 'text-red-400' : 'text-amber-300'}`}>
                Time Remaining: {formatTimer(remainingSeconds)}
              </span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-full text-xs font-mono text-slate-300">
              <span className="text-slate-400">Tab Switches:</span>
              <span className={`font-bold ${session.tab_switch_count > session.max_tab_switches ? 'text-red-400' : session.tab_switch_count > 0 ? 'text-amber-300' : 'text-emerald-400'}`}>
                {session.tab_switch_count || 0} / {session.max_tab_switches || 3}
              </span>
            </div>
          </div>
        ) : (
          <div className="px-3.5 py-1 bg-slate-950 border border-slate-800 text-slate-400 text-xs font-semibold rounded-full flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Session Completed
          </div>
        )}

        {/* Right Actions */}
        <div className="flex items-center gap-4">
          {/* Save status badge */}
          {!isCompleted && (
            <div className="text-[11px] font-mono flex items-center gap-1.5 text-slate-400">
              {saveStatus === 'saving' && (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                  <span className="text-amber-300">Saving...</span>
                </>
              )}
              {saveStatus === 'saved' && (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-slate-400">Saved</span>
                </>
              )}
              {saveStatus === 'error' && (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                  <span className="text-red-400">Unable to save. Please retry.</span>
                </>
              )}
            </div>
          )}

          {!isCompleted ? (
            <button
              onClick={() => setShowReviewModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-1.5"
            >
              <Eye className="w-3.5 h-3.5" /> Review & Submit
            </button>
          ) : (
            <button
              onClick={() => router.push('/dashboard')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs rounded-xl transition"
            >
              Back to Dashboard
            </button>
          )}
        </div>
      </header>

      {/* Main Examination Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Question Area */}
        <main className="flex-1 p-6 overflow-y-auto space-y-6 max-w-4xl mx-auto w-full">
          {isCompleted && (
            <div className="p-4 bg-indigo-950/60 border border-indigo-800 rounded-2xl text-xs text-indigo-300 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>This exam session is <strong>{session.status}</strong>. Answers are locked.</span>
              </div>
            </div>
          )}

          {currentQuestion ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm space-y-6 shadow-xl">
              {/* Question Header */}
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 bg-indigo-950 text-indigo-300 border border-indigo-800/60 font-mono font-bold text-xs rounded-lg">
                    Question {currentIndex + 1} of {totalQuestions}
                  </span>
                  <span className="px-2.5 py-1 bg-slate-950 text-slate-400 border border-slate-800 font-mono text-[10px] uppercase rounded-lg">
                    {currentQuestion.question_type}
                  </span>
                  {markedSet.has(currentQuestion.id) && (
                    <span className="px-2.5 py-1 bg-amber-950/80 text-amber-300 border border-amber-800/80 font-mono font-semibold text-[10px] rounded-lg flex items-center gap-1">
                      <Bookmark className="w-3 h-3 text-amber-400 fill-amber-400" /> Marked for Review
                    </span>
                  )}
                </div>

                <span className="font-mono text-xs font-bold text-indigo-400">
                  {currentQuestion.marks} pts
                </span>
              </div>

              {/* Question Text */}
              <div className="text-sm font-medium text-white leading-relaxed whitespace-pre-wrap">
                {currentQuestion.question_text}
              </div>

              {/* Input Workspace depending on Question Type */}
              <div className="pt-2">
                {/* MCQ */}
                {currentQuestion.question_type === 'MCQ' && (
                  <div className="space-y-3">
                    {currentQuestion.options.map((opt) => {
                      const isChecked = currentAns?.selected_option_ids?.includes(opt.id);
                      return (
                        <label
                          key={opt.id}
                          className={`flex items-start gap-3 p-3.5 rounded-xl border text-xs cursor-pointer transition ${
                            isChecked
                              ? 'bg-indigo-950/60 border-indigo-500 text-white'
                              : 'bg-slate-950/60 border-slate-800 hover:bg-slate-900 text-slate-300'
                          } ${isCompleted ? 'pointer-events-none opacity-80' : ''}`}
                        >
                          <input
                            type="radio"
                            name={`q_${currentQuestion.id}`}
                            disabled={isCompleted}
                            checked={isChecked || false}
                            onChange={() => handleOptionChange(currentQuestion.id, opt.id, false)}
                            className="mt-0.5 text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700"
                          />
                          <span>{opt.option_text}</span>
                        </label>
                      );
                    })}
                  </div>
                )}

                {/* MULTI_SELECT */}
                {currentQuestion.question_type === 'MULTI_SELECT' && (
                  <div className="space-y-3">
                    <p className="text-[11px] text-slate-400 italic mb-2">Select all options that apply:</p>
                    {currentQuestion.options.map((opt) => {
                      const isChecked = currentAns?.selected_option_ids?.includes(opt.id);
                      return (
                        <label
                          key={opt.id}
                          className={`flex items-start gap-3 p-3.5 rounded-xl border text-xs cursor-pointer transition ${
                            isChecked
                              ? 'bg-indigo-950/60 border-indigo-500 text-white'
                              : 'bg-slate-950/60 border-slate-800 hover:bg-slate-900 text-slate-300'
                          } ${isCompleted ? 'pointer-events-none opacity-80' : ''}`}
                        >
                          <input
                            type="checkbox"
                            disabled={isCompleted}
                            checked={isChecked || false}
                            onChange={() => handleOptionChange(currentQuestion.id, opt.id, true)}
                            className="mt-0.5 text-indigo-600 focus:ring-indigo-500 bg-slate-950 border-slate-700 rounded"
                          />
                          <span>{opt.option_text}</span>
                        </label>
                      );
                    })}
                  </div>
                )}

                {/* SHORT_ANSWER */}
                {currentQuestion.question_type === 'SHORT_ANSWER' && (
                  <div className="space-y-2">
                    <label className="block text-xs font-semibold text-slate-400">Your Answer:</label>
                    <input
                      type="text"
                      disabled={isCompleted}
                      placeholder="Type your answer here..."
                      value={currentAns?.text_answer || ''}
                      onChange={(e) => handleTextChange(currentQuestion.id, e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-70"
                    />
                  </div>
                )}

                {/* LONG_ANSWER */}
                {currentQuestion.question_type === 'LONG_ANSWER' && (
                  <div className="space-y-2">
                    <label className="block text-xs font-semibold text-slate-400">Your Detailed Answer:</label>
                    <textarea
                      rows={6}
                      disabled={isCompleted}
                      placeholder="Type your explanation or response..."
                      value={currentAns?.text_answer || ''}
                      onChange={(e) => handleTextChange(currentQuestion.id, e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 disabled:opacity-70"
                    />
                  </div>
                )}

                {/* HANDWRITTEN */}
                {currentQuestion.question_type === 'HANDWRITTEN' && (
                  <HandwrittenAnswerSection
                    key={currentQuestion.id}
                    sessionId={session.id}
                    questionId={currentQuestion.id}
                    marks={currentQuestion.marks}
                    isCompleted={isCompleted}
                    currentAnswerImageUrl={currentAns?.answer_image_url}
                    currentOcrStatus={currentAns?.ocr_status}
                    currentOcrConfidence={currentAns?.ocr_confidence}
                    currentExtractedText={currentAns?.text_answer}
                    onCaptureActiveChange={setIsHandwrittenCaptureActive}
                    onAnswerSaved={(data) => {
                      const current = answersMap[currentQuestion.id] || { selected_option_ids: [], text_answer: '' };
                      setAnswersMap((prev) => ({
                        ...prev,
                        [currentQuestion.id]: {
                          ...current,
                          answer_image_url: data.answer_image_url,
                          ocr_status: data.ocr_status,
                          ocr_confidence: data.ocr_confidence,
                          text_answer: data.extracted_text,
                        },
                      }));
                      logBehavioralEvent('ANSWER_CREATED', { question_id: currentQuestion.id });
                    }}
                    onAnswerCleared={() => {
                      handleClearAnswer(currentQuestion.id);
                    }}
                  />
                )}
              </div>

              {/* Prev / Mark for Review / Next Footer Controls */}
              <div className="flex justify-between items-center pt-4 border-t border-slate-800">
                <button
                  type="button"
                  disabled={currentIndex === 0}
                  onClick={() => setCurrentIndex((prev) => prev - 1)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5 disabled:opacity-40"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Previous
                </button>

                {!isCompleted && (
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleToggleReview(currentQuestion.id)}
                      className={`px-4 py-2 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 border ${
                        markedSet.has(currentQuestion.id)
                          ? 'bg-amber-950/80 border-amber-500 text-amber-300 hover:bg-amber-900'
                          : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-white hover:bg-slate-700'
                      }`}
                    >
                      <Bookmark className={`w-3.5 h-3.5 ${markedSet.has(currentQuestion.id) ? 'fill-amber-300 text-amber-300' : ''}`} />
                      {markedSet.has(currentQuestion.id) ? 'Marked for Review' : 'Mark for Review'}
                    </button>

                    {isAnswered(currentQuestion.id) && (
                      <button
                        type="button"
                        onClick={() => handleClearAnswer(currentQuestion.id)}
                        className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl border border-slate-700 transition flex items-center gap-1.5"
                      >
                        <RotateCcw className="w-3.5 h-3.5 text-slate-400" /> Clear Answer
                      </button>
                    )}
                  </div>
                )}

                {currentIndex < totalQuestions - 1 ? (
                  <button
                    type="button"
                    onClick={() => setCurrentIndex((prev) => prev + 1)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
                  >
                    Next <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowReviewModal(true)}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition flex items-center gap-1.5 shadow-lg shadow-indigo-600/25"
                  >
                    <Eye className="w-3.5 h-3.5" /> Review & Submit
                  </button>
                )}
              </div>
            </div>
          ) : null}
        </main>

        {/* Right Sidebar Question Navigation Grid */}
        <aside className="w-72 bg-slate-900/90 border-l border-slate-800 p-5 overflow-y-auto hidden lg:flex flex-col justify-between">
          <div className="space-y-4">
            <h3 className="font-bold text-xs text-white uppercase tracking-wider font-mono">
              Question Navigator
            </h3>

            {/* Grid of Buttons */}
            <div className="grid grid-cols-4 gap-2">
              {session.questions.map((q, idx) => {
                const answered = isAnswered(q.id);
                const marked = markedSet.has(q.id);
                const isCurrent = idx === currentIndex;

                let btnStyle = 'bg-slate-950 text-slate-400 border-slate-800 hover:bg-slate-800';

                if (answered && marked) {
                  btnStyle = 'bg-purple-950/80 text-purple-300 border-purple-800 hover:bg-purple-900';
                } else if (marked) {
                  btnStyle = 'bg-amber-950/80 text-amber-300 border-amber-800 hover:bg-amber-900';
                } else if (answered) {
                  btnStyle = 'bg-emerald-950/80 text-emerald-300 border-emerald-800 hover:bg-emerald-900';
                }

                if (isCurrent) {
                  btnStyle += ' ring-2 ring-indigo-500 border-indigo-400 font-bold';
                }

                return (
                  <button
                    key={q.id}
                    onClick={() => setCurrentIndex(idx)}
                    className={`h-10 text-xs font-mono rounded-xl border flex items-center justify-center transition relative ${btnStyle}`}
                  >
                    {idx + 1}
                    {marked && (
                      <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-amber-400" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Legend */}
          <div className="space-y-2 pt-6 border-t border-slate-800 text-[11px] text-slate-400">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-emerald-950 border border-emerald-800" />
              <span>🟢 Answered ({answeredCount})</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-slate-950 border border-slate-800" />
              <span>⚪ Unanswered ({unansweredCount})</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-amber-950 border border-amber-800" />
              <span>🟡 Marked for Review ({markedCount})</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-purple-950 border border-purple-800" />
              <span>🟣 Answered & Marked ({answeredAndMarkedCount})</span>
            </div>
            <div className="flex items-center gap-2 pt-1 border-t border-slate-800/60">
              <span className="w-3 h-3 rounded bg-slate-950 border border-indigo-500 ring-1 ring-indigo-500" />
              <span>🔵 Current Question</span>
            </div>
          </div>
        </aside>
      </div>

      {/* Review & Submit Modal Screen */}
      {showReviewModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full p-6 space-y-6 shadow-2xl my-8">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h2 className="font-bold text-base text-white">Exam Overview & Review</h2>
                <p className="text-xs text-slate-400">{session.exam_title} — {session.exam_subject}</p>
              </div>
              <button
                onClick={() => setShowReviewModal(false)}
                className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Summary Grid Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="bg-slate-950 border border-slate-800 p-3 rounded-2xl">
                <p className="text-[10px] font-mono text-slate-400 uppercase">Total</p>
                <p className="text-lg font-bold text-white mt-0.5">{totalQuestions}</p>
              </div>
              <div className="bg-emerald-950/40 border border-emerald-800/60 p-3 rounded-2xl">
                <p className="text-[10px] font-mono text-emerald-400 uppercase">Answered</p>
                <p className="text-lg font-bold text-emerald-300 mt-0.5">{answeredCount}</p>
              </div>
              <div className="bg-slate-950 border border-slate-800 p-3 rounded-2xl">
                <p className="text-[10px] font-mono text-slate-400 uppercase">Unanswered</p>
                <p className="text-lg font-bold text-slate-300 mt-0.5">{unansweredCount}</p>
              </div>
              <div className="bg-purple-950/40 border border-purple-800/60 p-3 rounded-2xl">
                <p className="text-[10px] font-mono text-purple-400 uppercase">Reviewing</p>
                <p className="text-lg font-bold text-purple-300 mt-0.5">{markedCount + answeredAndMarkedCount}</p>
              </div>
            </div>

            {/* Unanswered Warning Banner */}
            {unansweredCount > 0 && (
              <div className="p-3.5 bg-amber-950/50 border border-amber-800/80 rounded-2xl text-xs text-amber-300 flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0" />
                <span>You have <strong>{unansweredCount} unanswered questions</strong>. You can return to answer them or submit now.</span>
              </div>
            )}

            {/* Question List Summary */}
            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
              <p className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono mb-2">Question Breakdown</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {session.questions.map((q, idx) => {
                  const answered = isAnswered(q.id);
                  const marked = markedSet.has(q.id);

                  let statusText = '⚪ Unanswered';
                  let statusBadge = 'bg-slate-950 text-slate-400 border-slate-800';

                  if (answered && marked) {
                    statusText = '🟣 Answered & Marked';
                    statusBadge = 'bg-purple-950 text-purple-300 border-purple-800';
                  } else if (marked) {
                    statusText = '🟡 Marked for Review';
                    statusBadge = 'bg-amber-950 text-amber-300 border-amber-800';
                  } else if (answered) {
                    statusText = '🟢 Answered';
                    statusBadge = 'bg-emerald-950 text-emerald-300 border-emerald-800';
                  }

                  return (
                    <button
                      key={q.id}
                      onClick={() => {
                        setCurrentIndex(idx);
                        setShowReviewModal(false);
                      }}
                      className="flex items-center justify-between p-3 bg-slate-950 border border-slate-800 hover:border-indigo-500 rounded-xl text-left transition group"
                    >
                      <span className="text-xs font-semibold text-slate-200 group-hover:text-indigo-400 font-mono">
                        Q{idx + 1} ({q.question_type})
                      </span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded-lg border ${statusBadge}`}>
                        {statusText}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Action Footer */}
            <div className="flex items-center justify-between pt-4 border-t border-slate-800">
              <button
                onClick={() => setShowReviewModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-semibold text-xs rounded-xl transition"
              >
                Return to Exam
              </button>
              <button
                onClick={() => {
                  setShowReviewModal(false);
                  setShowSubmitModal(true);
                }}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-emerald-600/25 flex items-center gap-1.5"
              >
                <Send className="w-3.5 h-3.5" /> Submit Exam
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Custom Tab Switch Warning Dialog Modal */}
      {showTabSwitchDialog && tabSwitchDialogData && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center space-x-3 text-amber-400">
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-base text-white">Tab Switch Detected</h3>
                <p className="text-xs text-slate-400">Observable Proctoring Event</p>
              </div>
            </div>

            <div className="space-y-2 text-xs text-slate-300 bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80 leading-relaxed">
              <p>
                You left the exam window. Tab switch <strong>{tabSwitchDialogData.count} of {tabSwitchDialogData.max}</strong> has been recorded.
              </p>
              {tabSwitchDialogData.isFinalWarning && (
                <p className="text-amber-400 font-semibold pt-1 border-t border-slate-800/60">
                  One more tab switch will automatically submit your exam.
                </p>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowTabSwitchDialog(false)}
                className="w-full sm:w-auto px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl shadow-lg shadow-indigo-600/25 transition"
              >
                Continue Exam
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Submit Exam Confirmation Dialog */}
      <ConfirmDialog
        open={showSubmitModal}
        title="Submit Exam?"
        description={
          unansweredCount > 0
            ? `You have ${unansweredCount} unanswered questions. Once submitted, you cannot change your answers.`
            : 'Once submitted, you cannot change your answers.'
        }
        confirmLabel="Submit Exam"
        cancelLabel="Cancel"
        variant="default"
        loading={submitting}
        onConfirm={handleSubmitExam}
        onCancel={() => setShowSubmitModal(false)}
      />

      {/* Live Proctoring Monitor */}
      {!isCompleted && (
        <ProctoringCamera
          sessionId={sessionId}
          tabSwitchCount={session.tab_switch_count}
          maxTabSwitches={session.max_tab_switches}
          isHandwrittenCaptureActive={isHandwrittenCaptureActive}
          onEventLogged={handleProctoringEventLogged}
          onAutoSubmit={handleAutoSubmit}
          onStreamReady={handleProctoringStreamReady}
        />
      )}
    </div>
  );
}
