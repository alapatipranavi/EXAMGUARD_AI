'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Camera,
  CameraOff,
  Mic,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Loader2,
  X,
  UserCheck,
  Maximize,
  BookOpen,
  ArrowRight,
  ArrowLeft,
  Smartphone,
  Watch,
  Headphones,
  Laptop,
  Users,
  FileText,
  AlertTriangle,
  RotateCcw,
} from 'lucide-react';
import { faceDetector } from '@/lib/faceDetector';
import { objectDetector, PROHIBITED_OBJECT_TAXONOMY } from '@/lib/objectDetector';
import { faceIdentityEngine } from '@/lib/faceIdentity';
import { identityAPI } from '@/lib/api';

interface ProctoringSetupProps {
  open: boolean;
  examTitle: string;
  examInstructions?: string | null;
  sessionId?: string;
  onProceed: () => void;
  onCancel: () => void;
}

export function ProctoringSetup({
  open,
  examTitle,
  examInstructions,
  sessionId,
  onProceed,
  onCancel,
}: ProctoringSetupProps) {
  const [step, setStep] = useState<'rules' | 'check'>('rules');
  const [agreedToRules, setAgreedToRules] = useState<boolean>(false);

  const [cameraStatus, setCameraStatus] = useState<'idle' | 'checking' | 'ready' | 'denied' | 'error'>('idle');
  const [micStatus, setMicStatus] = useState<'idle' | 'checking' | 'ready' | 'denied' | 'error'>('idle');
  const [faceStatus, setFaceStatus] = useState<'idle' | 'checking' | 'ready' | 'failed' | 'unavailable'>('idle');
  const [identityStatus, setIdentityStatus] = useState<'idle' | 'checking' | 'ready' | 'failed' | 'unregistered'>('idle');
  const [singlePersonStatus, setSinglePersonStatus] = useState<'idle' | 'checking' | 'ready' | 'failed'>('idle');
  const [objectStatus, setObjectStatus] = useState<'idle' | 'checking' | 'ready' | 'prohibited_detected' | 'unavailable'>('idle');
  const [prohibitedAlert, setProhibitedAlert] = useState<string | null>(null);

  const [faceMessage, setFaceMessage] = useState<string>('Checking...');
  const [identityMessage, setIdentityMessage] = useState<string>('Checking student identity...');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [debugSimilarity, setDebugSimilarity] = useState<number | null>(null);
  const [debugMatchCount, setDebugMatchCount] = useState<number>(0);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const assignedStreamRef = useRef<MediaStream | null>(null);
  const detectionIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const consecutiveFacesRef = useRef<number>(0);
  const matchCountRef = useRef<number>(0);
  const mismatchCountRef = useRef<number>(0);
  const isVerifyingRef = useRef<boolean>(false);
  const lastIdentityCheckTimeRef = useRef<number>(0);
  const identityStatusRef = useRef<'idle' | 'checking' | 'ready' | 'failed' | 'unregistered'>('idle');

  const stopDetectionLoop = useCallback(() => {
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current);
      detectionIntervalRef.current = null;
    }
  }, []);

  const stopMediaStream = useCallback(() => {
    stopDetectionLoop();
    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => track.stop());
      } catch (err) {
        console.warn('Error stopping stream tracks:', err);
      }
      streamRef.current = null;
    }
    if (videoRef.current) {
      try {
        videoRef.current.onloadedmetadata = null;
        videoRef.current.srcObject = null;
      } catch (err) {
        console.warn('Error resetting video srcObject:', err);
      }
    }
    assignedStreamRef.current = null;
  }, [stopDetectionLoop]);

  const attachStreamToVideo = useCallback((video: HTMLVideoElement | null, stream: MediaStream | null) => {
    if (!video || !stream) return;
    if (video.srcObject === stream && assignedStreamRef.current === stream) {
      if (video.paused) {
        const playPromise = video.play();
        if (playPromise !== undefined) {
          playPromise.catch((err) => {
            if (err?.name === 'AbortError' || err?.name === 'NotAllowedError') return;
            console.warn('Video play error:', err);
          });
        }
      }
      return;
    }

    try {
      video.srcObject = stream;
      assignedStreamRef.current = stream;

      const playVideo = () => {
        const playPromise = video.play();
        if (playPromise !== undefined) {
          playPromise.catch((err) => {
            if (err?.name === 'AbortError' || err?.name === 'NotAllowedError') return;
            console.warn('Video play promise error:', err);
          });
        }
      };

      if (video.readyState >= 1) {
        playVideo();
      } else {
        video.onloadedmetadata = () => {
          playVideo();
        };
      }
    } catch (err) {
      console.warn('Failed to assign srcObject to video:', err);
    }
  }, []);

  const setVideoRef = useCallback(
    (node: HTMLVideoElement | null) => {
      videoRef.current = node;
      if (node && streamRef.current) {
        attachStreamToVideo(node, streamRef.current);
      }
    },
    [attachStreamToVideo]
  );

  const runDetectionLoop = useCallback(() => {
    stopDetectionLoop();
    consecutiveFacesRef.current = 0;
    matchCountRef.current = 0;
    mismatchCountRef.current = 0;
    isVerifyingRef.current = false;
    identityStatusRef.current = 'idle';
    setIdentityStatus('idle');
    setDebugSimilarity(null);
    setDebugMatchCount(0);

    setFaceStatus('checking');
    setSinglePersonStatus('checking');
    setObjectStatus('checking');
    setFaceMessage('Initializing AI detectors...');
    setProhibitedAlert(null);

    objectDetector.resetState();

    detectionIntervalRef.current = setInterval(async () => {
      if (!videoRef.current || videoRef.current.readyState < 2) return;

      try {
        // 1. Real Face Detection
        const faceRes = await faceDetector.detect(videoRef.current, Date.now());

        if (!faceRes.supported || faceRes.error === 'INITIALIZATION_FAILED') {
          setFaceStatus('unavailable');
          setFaceMessage('Face detection unavailable on your browser.');
        } else if (faceRes.faceCount === 1) {
          consecutiveFacesRef.current += 1;
          if (consecutiveFacesRef.current >= 2) {
            setFaceStatus('ready');
            setSinglePersonStatus('ready');
            setFaceMessage('Face Present (1 Face)');

            // Perform Stage 14.1 Identity Verification with Multi-Frame Consensus
            const now = Date.now();
            const shouldVerify = sessionId && !isVerifyingRef.current && (
              identityStatusRef.current !== 'ready' ||
              (now - lastIdentityCheckTimeRef.current >= 3000)
            );
            if (shouldVerify) {
              lastIdentityCheckTimeRef.current = now;
              isVerifyingRef.current = true;
              try {
                const idRes = await faceIdentityEngine.extractFaceEmbedding(videoRef.current, Date.now());
                if (idRes.success && idRes.embedding) {
                  const verifyRes = await identityAPI.verifySessionIdentity(sessionId, { face_embedding: idRes.embedding });
                  const simVal = typeof verifyRes.similarity === 'number' ? verifyRes.similarity : null;
                  setDebugSimilarity(simVal);

                  const liveNorm = Math.sqrt(idRes.embedding.reduce((s, x) => s + x * x, 0));
                  console.warn('[FRONTEND_IDENTITY_DIAGNOSTIC]', {
                    sessionId,
                    embeddingValid: Array.isArray(idRes.embedding) && idRes.embedding.length > 0,
                    embeddingLength: idRes.embedding.length,
                    embeddingNorm: Number(liveNorm.toFixed(4)),
                    similarity: simVal,
                    threshold: 0.80,
                    currentState: identityStatusRef.current,
                    matchCount: matchCountRef.current,
                    verifiedByAPI: verifyRes.verified,
                    exactCondition: verifyRes.verified && (simVal ?? 0) >= 0.80 && (matchCountRef.current + 1 >= 2)
                      ? 'MULTI_FRAME_CONSENSUS_REACHED'
                      : verifyRes.verified && (simVal ?? 0) >= 0.80
                      ? 'FIRST_FRAME_MATCHED'
                      : 'FRAME_MISMATCH_REJECTED',
                  });

                  if (verifyRes.verified && (simVal ?? 0) >= 0.80) {
                    matchCountRef.current += 1;
                    mismatchCountRef.current = 0;
                    setDebugMatchCount(matchCountRef.current);
                    if (matchCountRef.current >= 2) {
                      identityStatusRef.current = 'ready';
                      setIdentityStatus('ready');
                      setIdentityMessage('Student Identity Verified');
                    } else {
                      identityStatusRef.current = 'checking';
                      setIdentityStatus('checking');
                      setIdentityMessage('Verifying identity... (1/2 matched). Please remain still.');
                    }
                  } else {
                    // Critical Security Guard: ANY mismatch frame IMMEDIATELY revokes ready state and resets match count
                    matchCountRef.current = 0;
                    setDebugMatchCount(0);
                    mismatchCountRef.current += 1;
                    identityStatusRef.current = 'failed';
                    setIdentityStatus('failed');
                    setIdentityMessage(verifyRes.message || 'Identity verification failed. Detected face does not match registered student.');
                  }
                } else {
                  // Face features temporarily not aligned or clear - cannot confirm identity
                  matchCountRef.current = 0;
                  setDebugMatchCount(0);
                  if (identityStatusRef.current === 'ready') {
                    identityStatusRef.current = 'failed';
                    setIdentityStatus('failed');
                  }
                  setIdentityMessage('Aligning face for identity verification...');
                }
              } catch (err: any) {
                matchCountRef.current = 0;
                setDebugMatchCount(0);
                identityStatusRef.current = 'failed';
                const detail = err?.response?.data?.detail;
                const detailMsg = typeof detail === 'string' ? detail : (detail?.message || err?.message || '');
                const isVersionMismatch = detailMsg.includes('TEMPLATE_VERSION_MISMATCH') || detailMsg.includes('earlier descriptor version') || detail?.code === 'TEMPLATE_VERSION_MISMATCH';
                const isUnregistered = detailMsg.includes('not registered') || (err?.response?.status === 400 && detailMsg.includes('registered'));

                if (isVersionMismatch || isUnregistered) {
                  identityStatusRef.current = 'unregistered';
                  setIdentityStatus('unregistered');
                  if (isVersionMismatch) {
                    setIdentityMessage('Biometric template update required. Please re-register your face in Profile.');
                    setErrorMessage('Biometric template update required. Your face reference was registered with an earlier system version. Please re-register your face in Profile settings.');
                  } else {
                    setIdentityMessage('Face reference not registered. Please complete face registration in Profile.');
                    setErrorMessage('Face reference not registered. Please register your face in Profile settings.');
                  }
                } else if (err?.response?.status >= 500 || err?.name === 'TypeError' || err?.message?.includes('fetch') || err?.message?.includes('Network') || err?.message?.includes('CORS')) {
                  setIdentityStatus('failed');
                  setIdentityMessage('Identity verification could not be completed due to a server error. Please retry.');
                } else {
                  setIdentityStatus('failed');
                  setIdentityMessage(detailMsg || 'Identity verification failed.');
                }
              } finally {
                isVerifyingRef.current = false;
              }
            }
          } else {
            setFaceStatus('checking');
            setFaceMessage('Verifying face presence...');
          }
        } else if (faceRes.faceCount === 0) {
          consecutiveFacesRef.current = 0;
          matchCountRef.current = 0;
          mismatchCountRef.current = 0;
          setDebugMatchCount(0);
          setFaceStatus('failed');
          setSinglePersonStatus('failed');
          setFaceMessage('Face Not Detected. Please align yourself in frame.');
          if (identityStatusRef.current !== 'unregistered') {
            identityStatusRef.current = 'failed';
            setIdentityStatus('failed');
            setIdentityMessage('Face Not Detected');
          }
        } else {
          consecutiveFacesRef.current = 0;
          matchCountRef.current = 0;
          mismatchCountRef.current = 0;
          setDebugMatchCount(0);
          setFaceStatus('failed');
          setSinglePersonStatus('failed');
          setFaceMessage('Multiple Faces Detected. Please ensure you are alone.');
          if (identityStatusRef.current !== 'unregistered') {
            identityStatusRef.current = 'failed';
            setIdentityStatus('failed');
            setIdentityMessage('Multiple Faces Detected');
          }
        }

        // 2. Real Object Detection
        if (objectDetector.checkSupport()) {
          const objRes = await objectDetector.detect(videoRef.current, Date.now());

          if (!objRes.supported) {
            setObjectStatus('unavailable');
          } else if (objRes.detectedObjects.length > 0) {
            const detectedItems = objRes.detectedObjects;

            const phone = detectedItems.find((i) => i.categoryName === 'cell phone' || i.categoryName.includes('phone'));
            const laptop = detectedItems.find((i) => i.categoryName === 'laptop');
            const book = detectedItems.find((i) => i.categoryName === 'book');
            const personCount = detectedItems.filter((i) => i.categoryName === 'person').length;

            if (phone) {
              setObjectStatus('prohibited_detected');
              setProhibitedAlert('Prohibited object detected: Mobile Phone. Please remove it from camera view before starting.');
            } else if (laptop) {
              setObjectStatus('prohibited_detected');
              setProhibitedAlert('Prohibited object detected: Additional Laptop / Device. Please remove it from camera view before starting.');
            } else if (book) {
              setObjectStatus('prohibited_detected');
              setProhibitedAlert('Prohibited object detected: Book / Notebook / Notes. Please remove it from camera view before starting.');
            } else if (personCount >= 2) {
              setObjectStatus('prohibited_detected');
              setSinglePersonStatus('failed');
              setProhibitedAlert('Additional person detected in environment. Please ensure you are alone before starting.');
            } else {
              setObjectStatus('ready');
              setProhibitedAlert(null);
            }
          } else {
            setObjectStatus('ready');
            setProhibitedAlert(null);
          }
        } else {
          setObjectStatus('unavailable');
        }
      } catch (err: any) {
        console.warn('Error during pre-exam detection pass:', err);
      }
    }, 1000);
  }, [sessionId, stopDetectionLoop]);

  const startDeviceCheck = useCallback(async () => {
    stopMediaStream();
    setCameraStatus('checking');
    setMicStatus('checking');
    setFaceStatus('idle');
    setIdentityStatus('idle');
    identityStatusRef.current = 'idle';
    matchCountRef.current = 0;
    mismatchCountRef.current = 0;
    setDebugMatchCount(0);
    setDebugSimilarity(null);
    isVerifyingRef.current = false;
    lastIdentityCheckTimeRef.current = 0;
    consecutiveFacesRef.current = 0;
    setIdentityMessage('Checking student identity...');
    setSinglePersonStatus('idle');
    setObjectStatus('idle');
    setFaceMessage('Checking...');
    setErrorMessage(null);
    setProhibitedAlert(null);

    try {
      // Check identity registration status
      try {
        const idStatus = await identityAPI.getStatus();
        if (idStatus.requires_re_enrollment) {
          identityStatusRef.current = 'unregistered';
          setIdentityStatus('unregistered');
          setIdentityMessage('Biometric template update required. Please re-register your face in Profile.');
          setErrorMessage('Biometric template update required. Your face reference was registered with an earlier system version. Please re-register your face in Profile settings before starting the exam.');
        } else if (!idStatus.is_face_registered) {
          identityStatusRef.current = 'unregistered';
          setIdentityStatus('unregistered');
          setIdentityMessage('Face identity is not registered. Please register your face from Profile.');
          setErrorMessage('Face identity is not registered. Please complete face registration in Profile before starting the exam.');
        }
      } catch (idErr) {
        console.warn('Failed to check identity registration status:', idErr);
      }

      if (typeof window === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera/Microphone access is not supported by your browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true,
      });

      streamRef.current = stream;

      const hasVideo = stream.getVideoTracks().length > 0 && stream.getVideoTracks()[0].enabled;
      const hasAudio = stream.getAudioTracks().length > 0 && stream.getAudioTracks()[0].enabled;

      if (hasVideo) {
        setCameraStatus('ready');
        if (videoRef.current) {
          attachStreamToVideo(videoRef.current, stream);
        }
        runDetectionLoop();
      } else {
        setCameraStatus('denied');
        setFaceStatus('failed');
        setFaceMessage('Camera stream unavailable.');
      }

      if (hasAudio) {
        setMicStatus('ready');
      } else {
        setMicStatus('denied');
      }
    } catch (err: any) {
      console.warn('Device check getUserMedia error:', err);
      setCameraStatus('denied');
      setMicStatus('denied');
      setFaceStatus('failed');
      setObjectStatus('unavailable');

      let userMsg = 'Camera and microphone access could not be initialized.';
      if (err instanceof Error || (err && typeof err === 'object' && err.name)) {
        const errName = (err as any).name || '';
        if (errName === 'NotAllowedError' || errName === 'PermissionDeniedError') {
          userMsg = 'Camera and microphone permissions were denied. Please allow browser access in your browser settings to continue.';
        } else if (errName === 'NotFoundError' || errName === 'DevicesNotFoundError') {
          userMsg = 'No camera or microphone hardware found on your device.';
        } else if (errName === 'NotReadableError' || errName === 'TrackStartError') {
          userMsg = 'Camera or microphone is already in use by another application.';
        } else if (err.message) {
          userMsg = err.message;
        }
      }
      setErrorMessage(userMsg);
    }
  }, [stopMediaStream, attachStreamToVideo, runDetectionLoop]);

  useEffect(() => {
    if (open) {
      setStep('rules');
      setAgreedToRules(false);
      setCameraStatus('idle');
      setMicStatus('idle');
      setFaceStatus('idle');
      setIdentityStatus('idle');
      identityStatusRef.current = 'idle';
      matchCountRef.current = 0;
      mismatchCountRef.current = 0;
      setDebugMatchCount(0);
      setDebugSimilarity(null);
      isVerifyingRef.current = false;
      lastIdentityCheckTimeRef.current = 0;
      consecutiveFacesRef.current = 0;
    } else {
      stopMediaStream();
      setIdentityStatus('idle');
      identityStatusRef.current = 'idle';
      matchCountRef.current = 0;
      mismatchCountRef.current = 0;
      setDebugMatchCount(0);
      setDebugSimilarity(null);
      isVerifyingRef.current = false;
      lastIdentityCheckTimeRef.current = 0;
    }
    return () => {
      stopMediaStream();
    };
  }, [open, stopMediaStream]);

  if (!open) return null;

  const handleProceedToExam = async () => {
    // Stage 14.1 Security Hardening: Mandatory Pre-Start Final Identity Re-verification Guard
    if (!sessionId || !videoRef.current) {
      identityStatusRef.current = 'failed';
      setIdentityStatus('failed');
      setErrorMessage('Cannot start exam: active session or camera feed is missing.');
      return;
    }

    try {
      setIdentityStatus('checking');
      setIdentityMessage('Final identity check before entering exam...');
      const idRes = await faceIdentityEngine.extractFaceEmbedding(videoRef.current, Date.now());
      if (idRes.success && idRes.embedding) {
        const verifyRes = await identityAPI.verifySessionIdentity(sessionId, { face_embedding: idRes.embedding });
        const simVal = typeof verifyRes.similarity === 'number' ? verifyRes.similarity : null;
        setDebugSimilarity(simVal);

        if (!verifyRes.verified || verifyRes.status !== 'VERIFIED' || (simVal ?? 0) < 0.80) {
          identityStatusRef.current = 'failed';
          matchCountRef.current = 0;
          setDebugMatchCount(0);
          setIdentityStatus('failed');
          setIdentityMessage(verifyRes.message || 'Final identity check failed. Detected face does not match registered student.');
          return;
        }
      } else {
        identityStatusRef.current = 'failed';
        matchCountRef.current = 0;
        setDebugMatchCount(0);
        setIdentityStatus('failed');
        setIdentityMessage('Could not extract clear face features for final identity check.');
        return;
      }
    } catch (err: any) {
      identityStatusRef.current = 'failed';
      matchCountRef.current = 0;
      setDebugMatchCount(0);
      setIdentityStatus('failed');
      const detail = err?.response?.data?.detail || err?.message || '';
      if (err?.response?.status >= 500 || err?.name === 'TypeError' || err?.message?.includes('fetch') || err?.message?.includes('Network') || err?.message?.includes('CORS')) {
        setIdentityMessage('Final identity verification could not be completed due to a server error. Please retry.');
      } else {
        setIdentityMessage(detail || 'Final identity verification failed.');
      }
      return;
    }

    try {
      if (typeof document !== 'undefined' && document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen().catch(() => {});
      }
    } catch (err) {
      console.warn('Fullscreen request failed:', err);
    }

    stopMediaStream();
    onProceed();
  };

  const isCheckReady =
    cameraStatus === 'ready' &&
    micStatus === 'ready' &&
    faceStatus === 'ready' &&
    identityStatus === 'ready' &&
    singlePersonStatus === 'ready' &&
    objectStatus !== 'prohibited_detected';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header Bar */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                {step === 'rules' ? 'Before You Begin' : 'Environment & System Check'}
              </h2>
              <p className="text-xs text-slate-400 font-medium">{examTitle}</p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Step Tabs Indicator */}
            <div className="hidden sm:flex items-center space-x-2 text-xs font-mono">
              <span className={`px-2.5 py-1 rounded-lg ${step === 'rules' ? 'bg-indigo-600 text-white font-bold' : 'bg-slate-800 text-slate-400'}`}>
                1. Rules
              </span>
              <span className="text-slate-600">→</span>
              <span className={`px-2.5 py-1 rounded-lg ${step === 'check' ? 'bg-indigo-600 text-white font-bold' : 'bg-slate-800 text-slate-400'}`}>
                2. Check
              </span>
            </div>

            <button
              onClick={() => {
                stopMediaStream();
                onCancel();
              }}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors"
              title="Close setup"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* STEP 1: EXAM INSTRUCTIONS & PROCTORING RULES */}
        {step === 'rules' && (
          <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
            {/* Exam Specific Instructions */}
            <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
              <div className="flex items-center space-x-2 text-indigo-400 font-bold">
                <FileText className="w-4 h-4" />
                <span>Examination Specific Instructions</span>
              </div>
              <div className="text-slate-300 leading-relaxed pt-1">
                {examInstructions ? (
                  <p className="whitespace-pre-wrap">{examInstructions}</p>
                ) : (
                  <p className="text-slate-400 italic">
                    Standard examination timing and submission policies apply. Ensure a clean workspace before proceeding.
                  </p>
                )}
              </div>
            </div>

            {/* Mandatory Proctoring Rules Section */}
            <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="font-bold text-white text-xs uppercase tracking-wider font-mono flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" /> Mandatory Proctoring Rules
                </h3>
                <span className="text-[10px] text-slate-500 font-mono">ExamGuard AI Enforcement</span>
              </div>

              <ol className="list-decimal list-inside space-y-2 text-slate-300 leading-relaxed">
                <li>Keep your face clearly visible in the camera throughout the examination.</li>
                <li>Keep only the registered student in the camera frame.</li>
                <li>Do not use a mobile phone.</li>
                <li>Do not use a smartwatch or other smart wearable devices.</li>
                <li>Do not use tablets, laptops, secondary computers, or other electronic devices.</li>
                <li>Do not use headphones or earbuds unless explicitly permitted by the examiner.</li>
                <li>Do not use books, notes, papers, or unauthorized study material.</li>
                <li>Do not switch browser tabs or windows during active examination time.</li>
                <li>Do not exit full-screen mode unless necessary.</li>
                <li>Keep the camera and microphone connected during the exam session.</li>
                <li>Complete the examination independently according to the examiner&apos;s instructions.</li>
              </ol>

              <div className="p-3 rounded-lg bg-indigo-950/40 border border-indigo-800/60 text-indigo-300 text-[11px] leading-relaxed flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <span>
                  <strong>AI Assistance & Review Disclaimer:</strong> AI-assisted monitoring may detect prohibited objects and environment changes. The system does not automatically convict; final session review remains with the Examiner.
                </span>
              </div>
            </div>

            {/* Agreement Checkbox */}
            <label className="flex items-center space-x-3 p-4 rounded-xl bg-slate-800/50 border border-slate-700/60 cursor-pointer hover:bg-slate-800/80 transition">
              <input
                type="checkbox"
                checked={agreedToRules}
                onChange={(e) => setAgreedToRules(e.target.checked)}
                className="w-4 h-4 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-900"
              />
              <span className="text-xs font-semibold text-slate-200">
                I understand and agree to these exam rules and system proctoring requirements.
              </span>
            </label>
          </div>
        )}

        {/* STEP 2: ENVIRONMENT & DEVICE CHECK */}
        {step === 'check' && (
          <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs">
            {/* Live Camera Feed & Beside-Camera Diagnostic Monitor */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-stretch">
              {/* Live Camera Preview Box */}
              <div className="relative aspect-video w-full bg-slate-950 rounded-xl overflow-hidden border border-slate-800 flex flex-col items-center justify-center shadow-xl">
                {cameraStatus === 'ready' ? (
                  <video
                    ref={setVideoRef}
                    autoPlay
                    playsInline
                    muted
                    className="w-full h-full object-cover transform -scale-x-100"
                  />
                ) : cameraStatus === 'checking' ? (
                  <div className="flex flex-col items-center space-y-2 text-slate-400">
                    <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
                    <span className="text-xs font-mono">Accessing camera & microphone feed...</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-2 text-slate-500 p-6 text-center">
                    <CameraOff className="w-10 h-10 stroke-1 text-rose-400" />
                    <p className="text-xs text-rose-300">Camera stream unavailable. Please check permissions.</p>
                  </div>
                )}

                {/* Overlaid Live Status Indicator */}
                {cameraStatus === 'ready' && (
                  <div className="absolute bottom-2 left-2 right-2 px-3 py-1.5 rounded-lg bg-slate-950/80 backdrop-blur-md border border-slate-800 flex items-center justify-between text-[11px]">
                    <span className="flex items-center gap-1.5 font-medium text-slate-300">
                      <span className={`w-2 h-2 rounded-full ${objectStatus === 'prohibited_detected' ? 'bg-rose-400 animate-ping' : faceStatus === 'ready' ? 'bg-blue-400' : 'bg-amber-400'}`} />
                      {faceStatus === 'ready' ? 'Face Present (1 Face)' : faceMessage}
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">Camera Monitor</span>
                  </div>
                )}
              </div>

              {/* Beside-Camera Live Identity Verification Monitor Box */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-3 font-mono shadow-xl">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400" />
                    <span className="text-xs font-bold text-white tracking-wide">Live Identity Monitor</span>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">Stage 14.1 Guard</span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between py-1 border-b border-slate-900">
                    <span className="text-slate-400">Cosine Similarity:</span>
                    <span className={`font-bold ${debugSimilarity !== null ? (debugSimilarity >= 0.80 ? 'text-emerald-400' : 'text-rose-400') : 'text-slate-400'}`}>
                      {debugSimilarity !== null ? debugSimilarity.toFixed(4) : 'Awaiting frame...'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-900">
                    <span className="text-slate-400">Required Threshold:</span>
                    <span className="text-slate-200 font-bold">0.8000</span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-900">
                    <span className="text-slate-400">Consecutive Match:</span>
                    <span className={`font-bold ${debugMatchCount >= 2 ? 'text-emerald-400' : debugMatchCount === 1 ? 'text-amber-400' : 'text-slate-400'}`}>
                      {debugMatchCount} / 2 frames
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1 border-b border-slate-900">
                    <span className="text-slate-400">Frame Verdict:</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      debugSimilarity === null
                        ? 'bg-slate-900 text-slate-400'
                        : debugSimilarity >= 0.80
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                        : 'bg-rose-950 text-rose-400 border border-rose-800'
                    }`}>
                      {debugSimilarity === null ? 'ANALYZING' : debugSimilarity >= 0.80 ? 'MATCH' : 'MISMATCH'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between py-1">
                    <span className="text-slate-400">Identity State:</span>
                    <span className={`font-bold ${
                      identityStatus === 'ready'
                        ? 'text-emerald-400'
                        : identityStatus === 'failed'
                        ? 'text-rose-400'
                        : identityStatus === 'unregistered'
                        ? 'text-amber-400'
                        : 'text-indigo-400'
                    }`}>
                      {identityStatus === 'ready'
                        ? 'VERIFIED'
                        : identityStatus === 'failed'
                        ? 'VERIFICATION_FAILED'
                        : identityStatus === 'unregistered'
                        ? 'NOT_REGISTERED'
                        : 'CHECKING'}
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 leading-tight">
                  {identityStatus === 'ready' ? (
                    <span className="text-emerald-400 font-medium flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0" /> Live face matched registered template for 2 consecutive frames.
                    </span>
                  ) : identityStatus === 'unregistered' ? (
                    <div className="space-y-2">
                      <span className="text-amber-400 font-medium flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> Biometric template update required.
                      </span>
                      <a
                        href="/profile"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-white font-semibold text-[10px] rounded-lg transition"
                      >
                        <RotateCcw className="w-3 h-3" /> Update Face in Profile &rarr;
                      </a>
                    </div>
                  ) : identityStatus === 'failed' ? (
                    <span className="text-rose-400 font-medium flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> Live face does not match registered template. Exam access locked.
                    </span>
                  ) : (
                    <span className="text-slate-400 flex items-center gap-1">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 shrink-0" /> Align face directly to camera. 2 consecutive matching frames required.
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Prohibited Alert Banner */}
            {prohibitedAlert && (
              <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-200 flex items-start gap-3 shadow-lg">
                <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold block text-white text-xs">Prohibited Environment Signal Detected</span>
                  <p className="text-xs text-rose-300 mt-0.5">{prohibitedAlert}</p>
                </div>
              </div>
            )}

            {/* Error Message Banner */}
            {errorMessage && (
              <div className="p-4 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-200 flex items-start gap-3 shadow-lg">
                <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
                <p className="text-xs">{errorMessage}</p>
              </div>
            )}

            {/* Environment & Device Checklist */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {/* Camera */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-2">
                <div className="flex items-center space-x-2">
                  <Camera className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold text-white">Camera</span>
                </div>
                <div>
                  {cameraStatus === 'ready' ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Ready
                    </span>
                  ) : cameraStatus === 'checking' ? (
                    <span className="inline-flex items-center text-[10px] text-indigo-400">
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Checking
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold text-rose-400 bg-rose-950 px-2 py-0.5 rounded border border-rose-800">
                      Denied
                    </span>
                  )}
                </div>
              </div>

              {/* Microphone */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-2">
                <div className="flex items-center space-x-2">
                  <Mic className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold text-white">Microphone</span>
                </div>
                <div>
                  {micStatus === 'ready' ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Ready
                    </span>
                  ) : micStatus === 'checking' ? (
                    <span className="inline-flex items-center text-[10px] text-indigo-400">
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Checking
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold text-rose-400 bg-rose-950 px-2 py-0.5 rounded border border-rose-800">
                      Denied
                    </span>
                  )}
                </div>
              </div>

              {/* Face Presence */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-2">
                <div className="flex items-center space-x-2">
                  <UserCheck className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold text-white">Face Presence</span>
                </div>
                <div>
                  {faceStatus === 'ready' ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Face Present
                    </span>
                  ) : faceStatus === 'checking' ? (
                    <span className="inline-flex items-center text-[10px] text-indigo-400">
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Verifying
                    </span>
                  ) : (
                    <span className="text-[10px] font-bold text-amber-400 bg-amber-950 px-2 py-0.5 rounded border border-amber-800">
                      Check Face
                    </span>
                  )}
                </div>
              </div>

              {/* Student Identity */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-2">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-white">Student Identity</span>
                </div>
                <div>
                  {identityStatus === 'ready' ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Verified Match
                    </span>
                  ) : identityStatus === 'checking' ? (
                    <span className="inline-flex items-center text-[10px] text-indigo-400">
                      <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Matching Face...
                    </span>
                  ) : identityStatus === 'unregistered' ? (
                    <div className="flex flex-col gap-1 items-start">
                      <span className="inline-flex items-center text-[10px] font-bold text-amber-400 bg-amber-950 px-2 py-0.5 rounded border border-amber-800">
                        Not Registered
                      </span>
                      <a href="/profile" className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold underline">
                        Register Face →
                      </a>
                    </div>
                  ) : identityStatus === 'failed' ? (
                    <div className="flex flex-col gap-1 items-start">
                      <span className="inline-flex items-center text-[10px] font-bold text-rose-400 bg-rose-950 px-2 py-0.5 rounded border border-rose-800">
                        <AlertTriangle className="w-3 h-3 mr-1" /> {identityMessage.includes('retry') ? 'Verification Failed' : 'Identity Mismatch'}
                      </span>
                      <button
                        onClick={startDeviceCheck}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold underline text-left"
                      >
                        Retry Verification →
                      </button>
                    </div>
                  ) : (
                    <span className="text-[10px] text-slate-400">Awaiting face...</span>
                  )}
                </div>
              </div>

              {/* Single Person */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-2">
                <div className="flex items-center space-x-2">
                  <Users className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold text-white">Single Person</span>
                </div>
                <div>
                  {singlePersonStatus === 'ready' ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Single Person
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-400">Checking...</span>
                  )}
                </div>
              </div>

              {/* Object Monitoring */}
              <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-2">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-slate-400" />
                  <span className="text-xs font-semibold text-white">Object Guard</span>
                </div>
                <div>
                  {objectStatus === 'ready' ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-800">
                      <CheckCircle2 className="w-3 h-3 mr-1" /> Environment Clear
                    </span>
                  ) : objectStatus === 'prohibited_detected' ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-rose-400 bg-rose-950 px-2 py-0.5 rounded border border-rose-800">
                      <AlertTriangle className="w-3 h-3 mr-1" /> Object Detected
                    </span>
                  ) : objectStatus === 'unavailable' ? (
                    <span className="text-[10px] font-bold text-amber-400 bg-amber-950 px-2 py-0.5 rounded border border-amber-800">
                      Unavailable
                    </span>
                  ) : (
                    <span className="text-[10px] text-slate-400">Scanning environment...</span>
                  )}
                </div>
              </div>
            </div>



            {/* Vision Model Capabilities & Supported Taxonomy */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
              <span className="text-[10px] font-mono font-bold text-slate-400 uppercase block">
                Object Guard Vision Model Capabilities
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center space-x-1.5 text-emerald-400">
                  <Smartphone className="w-3.5 h-3.5 shrink-0" />
                  <span>Phone: Monitored</span>
                </div>
                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center space-x-1.5 text-emerald-400">
                  <Laptop className="w-3.5 h-3.5 shrink-0" />
                  <span>Laptop: Monitored</span>
                </div>
                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center space-x-1.5 text-emerald-400">
                  <BookOpen className="w-3.5 h-3.5 shrink-0" />
                  <span>Book/Notes: Monitored</span>
                </div>
                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center space-x-1.5 text-amber-400" title="Smartwatch class is not present in standard COCO-80 vision model; handled via Examiner Visual Review">
                  <Watch className="w-3.5 h-3.5 shrink-0" />
                  <span>Watch: Examiner Review</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="p-5 border-t border-slate-800 flex items-center justify-between bg-slate-950/80">
          {step === 'rules' ? (
            <>
              <button
                onClick={() => {
                  stopMediaStream();
                  onCancel();
                }}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>

              <button
                onClick={() => {
                  setStep('check');
                  startDeviceCheck();
                }}
                disabled={!agreedToRules}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue to Environment Check <ArrowRight className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => {
                    stopMediaStream();
                    setStep('rules');
                  }}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition flex items-center gap-1.5"
                >
                  <ArrowLeft className="w-3.5 h-3.5" /> Back to Rules
                </button>

                <button
                  onClick={startDeviceCheck}
                  disabled={cameraStatus === 'checking'}
                  className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition disabled:opacity-50"
                >
                  Re-test Devices
                </button>
              </div>

              <button
                onClick={handleProceedToExam}
                disabled={!isCheckReady}
                className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-emerald-600/25 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Maximize className="w-4 h-4" /> Enter Fullscreen & Start Exam
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
