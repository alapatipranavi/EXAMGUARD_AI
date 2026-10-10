'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import AppShell from '@/components/layout/AppShell';
import PageHeader from '@/components/layout/PageHeader';
import {
  User as UserIcon,
  ShieldCheck,
  Camera,
  CheckCircle2,
  AlertTriangle,
  X,
  RotateCcw,
  Loader2,
  Info,
  Save,
  Building2,
  GraduationCap,
  Edit3,
  Lock,
  Calendar,
  BadgeCheck,
} from 'lucide-react';
import { authAPI, identityAPI, dashboardAPI, userAPI, User, StudentAcademicProfile, IdentityStatusResponse } from '@/lib/api';
import { faceIdentityEngine } from '@/lib/faceIdentity';

export default function ProfilePage() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [academicProfile, setAcademicProfile] = useState<StudentAcademicProfile | null>(null);
  const [identityStatus, setIdentityStatus] = useState<IdentityStatusResponse | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit Name Modal State
  const [showEditModal, setShowEditModal] = useState(false);
  const [editFirstName, setEditFirstName] = useState('');
  const [editLastName, setEditLastName] = useState('');
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState<string | null>(null);

  // Face Registration Modal State
  const [showRegModal, setShowRegModal] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const [regStatus, setRegStatus] = useState<
    'idle' | 'initializing' | 'NO_FACE' | 'MULTIPLE_FACES' | 'NOT_ALIGNED' | 'ALIGNED' | 'CAPTURED' | 'saving' | 'success' | 'failed'
  >('idle');
  const [regMessage, setRegMessage] = useState<string>('No face detected. Please position your face inside the camera frame.');
  const [regError, setRegError] = useState<string | null>(null);
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(null);
  const [savedFacePreview, setSavedFacePreview] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const assignedStreamRef = useRef<MediaStream | null>(null);
  const scanIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const capturedEmbeddingRef = useRef<number[] | null>(null);
  const consecutiveAlignedRef = useRef<number>(0);

  const fetchUser = async () => {
    setLoadingUser(true);
    setError(null);
    try {
      const user = await userAPI.getProfile();
      setCurrentUser(user);
      if (user.role === 'STUDENT') {
        try {
          const dashData = await dashboardAPI.getStudentDashboard();
          setAcademicProfile(dashData.academic_profile);
        } catch (e) {
          console.warn('Failed to load student academic profile on profile page:', e);
        }
        try {
          const idData = await identityAPI.getStatus();
          setIdentityStatus(idData);
        } catch (e) {
          console.warn('Failed to load identity status on profile page:', e);
        }
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load user profile.');
    } finally {
      setLoadingUser(false);
    }
  };

  const handleOpenEditModal = () => {
    if (currentUser) {
      setEditFirstName(currentUser.first_name);
      setEditLastName(currentUser.last_name || '');
      setEditError(null);
      setEditSuccess(null);
      setShowEditModal(true);
    }
  };

  const handleCloseEditModal = () => {
    setShowEditModal(false);
    setEditError(null);
    setEditSuccess(null);
  };

  const handleSaveProfileName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editFirstName.trim()) {
      setEditError('First name is required.');
      return;
    }
    setEditLoading(true);
    setEditError(null);
    try {
      const updated = await userAPI.updateProfile({
        first_name: editFirstName.trim(),
        last_name: editLastName.trim(),
      });
      setCurrentUser(updated);
      setEditSuccess('Profile name updated successfully.');
      setTimeout(() => {
        setShowEditModal(false);
        setEditSuccess(null);
      }, 1200);
    } catch (err: any) {
      setEditError(err?.message || 'Failed to update profile name.');
    } finally {
      setEditLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  useEffect(() => {
    if (currentUser?.id && currentUser?.is_face_registered) {
      try {
        const saved = localStorage.getItem(`examguard_face_preview_${currentUser.id}`);
        if (saved) {
          setSavedFacePreview(saved);
        }
      } catch (e) {}
    }
  }, [currentUser]);

  const stopCameraStream = useCallback(() => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
    }
    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => track.stop());
      } catch (e) {
        console.warn('Error stopping profile camera tracks:', e);
      }
      streamRef.current = null;
    }
    if (videoRef.current) {
      try {
        videoRef.current.onloadedmetadata = null;
        videoRef.current.srcObject = null;
      } catch (e) {}
    }
    assignedStreamRef.current = null;
  }, []);

  const attachStreamToVideo = useCallback((video: HTMLVideoElement | null, stream: MediaStream | null) => {
    if (!video || !stream) return;
    if (video.srcObject === stream && assignedStreamRef.current === stream) return;
    try {
      video.srcObject = stream;
      assignedStreamRef.current = stream;
      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          if (err?.name === 'AbortError' || err?.name === 'NotAllowedError') return;
          console.warn('Profile video play error:', err);
        });
      }
    } catch (err) {
      console.warn('Profile attachStreamToVideo error:', err);
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

  const startFaceRegistrationCamera = useCallback(async () => {
    stopCameraStream();
    setRegStatus('initializing');
    setRegMessage('Initializing camera & identity model...');
    setRegError(null);
    setCapturedDataUrl(null);
    capturedEmbeddingRef.current = null;
    consecutiveAlignedRef.current = 0;

    try {
      if (typeof window === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera access is not supported by your browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 15 } },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        attachStreamToVideo(videoRef.current, stream);
      }

      await faceIdentityEngine.init();

      setRegStatus('NO_FACE');
      setRegMessage('No face detected. Please position your face inside the camera frame.');

      scanIntervalRef.current = setInterval(async () => {
        if (!videoRef.current || videoRef.current.readyState < 2) return;

        const res = await faceIdentityEngine.extractFaceEmbedding(videoRef.current, Date.now(), { requireStrictAlignment: true });
        const alignStatus = res.alignmentStatus || 'NO_FACE';

        if (alignStatus === 'NO_FACE') {
          consecutiveAlignedRef.current = 0;
          setRegStatus('NO_FACE');
          setRegMessage('No face detected. Please position your face inside the camera frame.');
          capturedEmbeddingRef.current = null;
        } else if (alignStatus === 'MULTIPLE_FACES') {
          consecutiveAlignedRef.current = 0;
          setRegStatus('MULTIPLE_FACES');
          setRegMessage('Multiple faces detected. Only one person should be visible.');
          capturedEmbeddingRef.current = null;
        } else if (alignStatus === 'NOT_ALIGNED') {
          consecutiveAlignedRef.current = 0;
          setRegStatus('NOT_ALIGNED');
          setRegMessage('Face not aligned. Please position your face inside the circle.');
          capturedEmbeddingRef.current = null;
        } else if (alignStatus === 'ALIGNED' && res.embedding) {
          consecutiveAlignedRef.current += 1;
          if (consecutiveAlignedRef.current >= 2) {
            setRegStatus('ALIGNED');
            setRegMessage('Face aligned. Ready to capture.');
            capturedEmbeddingRef.current = res.embedding;
          }
        }
      }, 500);
    } catch (err: any) {
      console.warn('Face registration camera error:', err);
      setRegStatus('failed');
      setRegError(err?.message || 'Camera permission denied or camera unavailable.');
    }
  }, [stopCameraStream, attachStreamToVideo]);

  const handleOpenRegistrationModal = () => {
    setShowRegModal(true);
    setConsentGiven(false);
    setRegStatus('idle');
    setRegError(null);
    setCapturedDataUrl(null);
    setRegMessage('No face detected. Please position your face inside the camera frame.');
  };

  const handleCloseRegistrationModal = () => {
    stopCameraStream();
    setShowRegModal(false);
  };

  const handleCaptureFace = () => {
    if (regStatus !== 'ALIGNED' || !capturedEmbeddingRef.current) {
      setRegError('Please align your face inside the circular guide before capturing.');
      return;
    }

    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
      scanIntervalRef.current = null;
    }

    // Capture static video frame to canvas dataURL
    if (videoRef.current) {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = videoRef.current.videoWidth || 640;
        canvas.height = videoRef.current.videoHeight || 480;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.translate(canvas.width, 0);
          ctx.scale(-1, 1);
          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
          const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
          setCapturedDataUrl(dataUrl);
        }
      } catch (err) {
        console.warn('Error capturing canvas snapshot:', err);
      }
    }

    setRegStatus('CAPTURED');
    setRegMessage('Face captured successfully.');
  };

  const handleRetakeFace = () => {
    setCapturedDataUrl(null);
    capturedEmbeddingRef.current = null;
    startFaceRegistrationCamera();
  };

  const handleSaveProfile = async () => {
    if (!capturedEmbeddingRef.current) {
      setRegError('No valid face capture available. Please capture a valid face alignment.');
      return;
    }
    if (!consentGiven) {
      setRegError('Please check the consent box before saving your face profile.');
      return;
    }

    setRegStatus('saving');
    setRegError(null);

    try {
      await identityAPI.registerFace({
        face_embedding: capturedEmbeddingRef.current,
        consent_given: true,
        descriptor_version: 2,
      });

      if (currentUser?.id && capturedDataUrl) {
        try {
          localStorage.setItem(`examguard_face_preview_${currentUser.id}`, capturedDataUrl);
          setSavedFacePreview(capturedDataUrl);
        } catch (e) {}
      }

      setRegStatus('success');
      setRegMessage('Face identity registered successfully.');
      await fetchUser();
      setTimeout(() => {
        handleCloseRegistrationModal();
      }, 1200);
    } catch (err: any) {
      setRegStatus('CAPTURED');
      setRegError(err?.message || 'Failed to save face registration reference.');
    }
  };

  if (loadingUser) {
    return (
      <AppShell title="User Profile">
        <div className="p-12 text-center font-mono text-xs text-slate-500">Loading user profile...</div>
      </AppShell>
    );
  }

  if (error || !currentUser) {
    return (
      <AppShell title="User Profile">
        <div className="p-6 bg-red-950/60 border border-red-800 text-red-300 rounded-2xl text-xs">
          {error || 'User profile unavailable.'}
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell title="User Profile">
      <div className="max-w-4xl mx-auto space-y-6 pb-16">
        <PageHeader
          title="Account Profile"
          subtitle="Manage your personal profile, identity credentials, and institutional scope."
        />

        {/* User Profile Summary Card */}
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-2xl shrink-0">
              {currentUser.first_name[0] || 'U'}
              {currentUser.last_name ? currentUser.last_name[0] : ''}
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-white tracking-tight">
                  {currentUser.first_name} {currentUser.last_name}
                </h2>
                <button
                  onClick={handleOpenEditModal}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition flex items-center gap-1.5"
                  title="Edit First and Last Name"
                >
                  <Edit3 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Edit Name</span>
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                <span className="flex items-center gap-1.5 font-mono text-slate-300">
                  <Lock className="w-3.5 h-3.5 text-slate-500" />
                  {currentUser.email}
                  <span className="text-[10px] text-slate-500 font-mono">(read-only)</span>
                </span>
                <span className="text-slate-600">•</span>
                <span className="flex items-center gap-1.5 text-slate-400">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  Joined {currentUser.created_at ? new Date(currentUser.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }) : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <span
              className={`px-3 py-1.5 rounded-xl border font-mono text-xs font-bold uppercase ${
                currentUser.role === 'ADMIN'
                  ? 'bg-purple-950/60 border-purple-800 text-purple-300'
                  : currentUser.role === 'EXAMINER'
                  ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
                  : 'bg-indigo-950/60 border-indigo-800 text-indigo-300'
              }`}
            >
              {currentUser.role}
            </span>
            <span className="px-3 py-1.5 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-400 text-xs font-semibold flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Active
            </span>
          </div>
        </div>

        {/* Academic Profile & Institution Card */}
        <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4 shadow-xl">
          <div className="flex items-center gap-3 border-b border-slate-800 pb-3">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <Building2 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">Academic & Institutional Scope</h3>
              <p className="text-xs text-slate-400">Institutional scope determines exam targeting and administrative jurisdiction.</p>
            </div>
          </div>

          {currentUser.role === 'STUDENT' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">College</span>
                <p className="font-semibold text-slate-200">
                  {currentUser.college_name || academicProfile?.college_name ? (
                    <>
                      {currentUser.college_name || academicProfile?.college_name}{' '}
                      {(currentUser.college_code || academicProfile?.college_code) && (
                        <span className="text-slate-400 font-mono text-[10px]">
                          ({currentUser.college_code || academicProfile?.college_code})
                        </span>
                      )}
                    </>
                  ) : (
                    'Not assigned'
                  )}
                </p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Department</span>
                <p className="font-semibold text-slate-200">
                  {currentUser.department_name || academicProfile?.department_name ? (
                    <>
                      {currentUser.department_name || academicProfile?.department_name}{' '}
                      {(currentUser.department_code || academicProfile?.department_code) && (
                        <span className="text-slate-400 font-mono text-[10px]">
                          ({currentUser.department_code || academicProfile?.department_code})
                        </span>
                      )}
                    </>
                  ) : (
                    'Not assigned'
                  )}
                </p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Year of Study</span>
                <p className="font-semibold text-slate-200">
                  {currentUser.year_of_study || academicProfile?.year_of_study ? (
                    `${currentUser.year_of_study || academicProfile?.year_of_study}${
                      (currentUser.year_of_study || academicProfile?.year_of_study) === 1
                        ? 'st'
                        : (currentUser.year_of_study || academicProfile?.year_of_study) === 2
                        ? 'nd'
                        : (currentUser.year_of_study || academicProfile?.year_of_study) === 3
                        ? 'rd'
                        : 'th'
                    } Year`
                  ) : (
                    'Not assigned'
                  )}
                </p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Section</span>
                <p className="font-semibold text-slate-200">
                  {currentUser.section_name || academicProfile?.section_name ? (
                    <>
                      {currentUser.section_name || academicProfile?.section_name}{' '}
                      {(currentUser.section_code || academicProfile?.section_code) && (
                        <span className="text-slate-400 font-mono text-[10px]">
                          ({currentUser.section_code || academicProfile?.section_code})
                        </span>
                      )}
                    </>
                  ) : (
                    'Not assigned'
                  )}
                </p>
              </div>
            </div>
          )}

          {currentUser.role === 'EXAMINER' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Assigned College</span>
                <p className="font-semibold text-slate-200">
                  {currentUser.college_name ? (
                    <>
                      {currentUser.college_name}{' '}
                      {currentUser.college_code && (
                        <span className="text-slate-400 font-mono text-[10px]">({currentUser.college_code})</span>
                      )}
                    </>
                  ) : (
                    'Not assigned'
                  )}
                </p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1">
                <span className="text-[10px] font-mono text-slate-500 uppercase">Examiner Scope</span>
                <p className="text-slate-300 leading-relaxed text-[11px]">
                  Examination creation and candidate monitoring are strictly targeted to students within this institution.
                </p>
              </div>
            </div>
          )}

          {currentUser.role === 'ADMIN' && (
            <div className="p-4 bg-slate-950 border border-slate-800/80 rounded-xl space-y-1 text-xs">
              <span className="text-[10px] font-mono text-slate-500 uppercase">Administrative Jurisdiction</span>
              <p className="font-semibold text-slate-200">
                System-Wide Administrator
              </p>
              <p className="text-slate-400 text-[11px] leading-relaxed mt-1">
                Unrestricted administrative jurisdiction over all colleges, departments, examiners, students, and exam sessions across ExamGuard AI.
              </p>
            </div>
          )}
        </div>

        {/* IDENTITY VERIFICATION SECTION (STUDENT ONLY) */}
        {currentUser.role === 'STUDENT' && (
          <div className="p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight">Identity Verification</h3>
                  <p className="text-xs text-slate-400">
                    Your face identity is used for exam identity verification.
                  </p>
                </div>
              </div>

              {identityStatus?.requires_re_enrollment ? (
                <span className="px-3 py-1 rounded-md text-[10px] font-mono font-bold uppercase bg-amber-950 text-amber-400 border border-amber-500/30 flex items-center gap-1.5 animate-pulse">
                  <AlertTriangle className="w-3.5 h-3.5" /> UPDATE REQUIRED (v1)
                </span>
              ) : currentUser.is_face_registered ? (
                <span className="px-3 py-1 rounded-md text-[10px] font-mono font-bold uppercase bg-emerald-950 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> REGISTERED (v2)
                </span>
              ) : (
                <span className="px-3 py-1 rounded-md text-[10px] font-mono font-bold uppercase bg-slate-800 text-slate-400 border border-slate-700">
                  NOT REGISTERED
                </span>
              )}
            </div>

            {/* Template Version Migration Warning Banner */}
            {identityStatus?.requires_re_enrollment && (
              <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-800/60 text-amber-200 text-xs flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <span className="font-bold text-white text-xs">Biometric Template Calibration Update Required</span>
                  <p className="text-amber-200/90 leading-relaxed text-[11px]">
                    Your stored face template was registered with an earlier calibration system (v1). Exam proctoring security requires re-registering your face reference with the zero-centered biometric standard (v2) to prevent verification mismatches.
                  </p>
                </div>
              </div>
            )}

            {/* Profile Display: IF REGISTERED */}
            {currentUser.is_face_registered ? (
              <div className="space-y-6">
                <div className="flex flex-col sm:flex-row items-center gap-6 p-4 bg-slate-950 border border-slate-800/80 rounded-xl">
                  {/* Registered Face Preview Thumbnail */}
                  <div className="relative w-32 h-32 rounded-xl border-2 border-indigo-500/30 bg-slate-900 overflow-hidden shrink-0 flex items-center justify-center">
                    {savedFacePreview ? (
                      <img
                        src={savedFacePreview}
                        alt="Registered Face Reference"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center text-slate-500 text-center p-2">
                        <UserIcon className="w-10 h-10 text-indigo-400 mb-1" />
                        <span className="text-[9px] font-mono">Face Reference Active</span>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2 text-center sm:text-left flex-1">
                    <p className="text-xs font-bold text-white">
                      Face identity registered for proctored examinations.
                    </p>
                    <p className="text-xs text-slate-400 font-mono">
                      Registered on:{' '}
                      <span className="text-slate-200">
                        {currentUser.face_registered_at
                          ? new Date(currentUser.face_registered_at).toLocaleDateString()
                          : '29/09/2026'}
                      </span>
                    </p>
                    <p className="text-[11px] text-slate-400 leading-relaxed max-w-md">
                      Your registered identity reference is used for exam identity verification.
                    </p>
                    <div className="pt-2 flex flex-wrap gap-2">
                      <button
                        onClick={handleOpenRegistrationModal}
                        className={`px-4 py-2 font-semibold text-xs rounded-xl transition shadow-lg flex items-center gap-2 ${
                          identityStatus?.requires_re_enrollment
                            ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/25 animate-pulse'
                            : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                        }`}
                      >
                        <RotateCcw className="w-4 h-4" />
                        {identityStatus?.requires_re_enrollment ? 'Update Face Reference (Required)' : 'Re-register Face Reference'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* Profile Display: IF NOT REGISTERED */
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/50 text-indigo-200 text-xs flex items-start gap-3">
                  <Info className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="font-bold text-white">Identity Registration Required</span>
                    <p className="text-slate-300 leading-relaxed">
                      Face identity is not registered. Please register your face before attempting a proctored examination.
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2">
                  <div>
                    <p className="text-xs text-slate-300 font-semibold">Face identity is not registered.</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Required prior to initiating proctored examinations.</p>
                  </div>

                  <button
                    onClick={handleOpenRegistrationModal}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2"
                  >
                    <Camera className="w-4 h-4" /> Register Face
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* FACE REGISTRATION MODAL */}
        {showRegModal && (
          <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 space-y-6 shadow-2xl relative max-h-[92vh] overflow-y-auto">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-2.5">
                  <Camera className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-base font-bold text-white">Face Registration</h3>
                </div>
                <button
                  onClick={handleCloseRegistrationModal}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Instructions Banner */}
              <p className="text-xs text-slate-300 leading-relaxed">
                Your face will be used only to verify your identity during proctored examinations.
              </p>

              {/* Camera Preview & Alignment Container */}
              <div className="space-y-4">
                <div className="relative aspect-video bg-slate-950 border border-slate-800 rounded-xl overflow-hidden flex items-center justify-center">
                  {/* Live Video Feed or Captured Preview */}
                  {regStatus === 'CAPTURED' && capturedDataUrl ? (
                    <img
                      src={capturedDataUrl}
                      alt="Captured Face Snapshot"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <video
                      ref={setVideoRef}
                      autoPlay
                      playsInline
                      muted
                      className="w-full h-full object-cover transform -scale-x-100"
                    />
                  )}

                  {/* Development Testing Status Overlay Badge */}
                  {regStatus !== 'CAPTURED' && regStatus !== 'idle' && regStatus !== 'initializing' && (
                    <div className="absolute top-3 left-3 bg-slate-950/80 border border-slate-800/80 rounded-lg px-2.5 py-1 text-[10px] font-mono text-slate-300 space-y-0.5 pointer-events-none z-10">
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-400">Face Detected:</span>
                        <span className={regStatus !== 'NO_FACE' ? 'text-emerald-400 font-bold' : 'text-slate-400 font-bold'}>
                          {regStatus !== 'NO_FACE' ? 'YES' : 'NO'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-400">Alignment:</span>
                        <span className={regStatus === 'ALIGNED' ? 'text-emerald-400 font-bold' : regStatus === 'NOT_ALIGNED' ? 'text-amber-400 font-bold' : regStatus === 'MULTIPLE_FACES' ? 'text-rose-400 font-bold' : 'text-slate-400 font-bold'}>
                          {regStatus === 'ALIGNED' ? 'ALIGNED' : regStatus === 'NOT_ALIGNED' ? 'NOT ALIGNED' : regStatus === 'MULTIPLE_FACES' ? 'MULTIPLE FACES' : 'NONE'}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Circular Alignment Guide Overlay (Visible during live camera mode) */}
                  {regStatus !== 'CAPTURED' && regStatus !== 'idle' && regStatus !== 'initializing' && (
                    <div
                      className={`absolute inset-0 border-2 border-dashed rounded-full w-48 h-48 mx-auto my-auto pointer-events-none flex flex-col items-center justify-center transition-all duration-300 ${
                        regStatus === 'ALIGNED'
                          ? 'border-emerald-500 bg-emerald-500/10 shadow-[0_0_25px_rgba(16,185,129,0.3)]'
                          : 'border-amber-500/60 bg-amber-500/5'
                      }`}
                    >
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold transition ${
                          regStatus === 'ALIGNED'
                            ? 'text-emerald-300 bg-emerald-950/90 border border-emerald-500/40'
                            : 'text-amber-300 bg-amber-950/90 border border-amber-500/40'
                        }`}
                      >
                        {regStatus === 'ALIGNED' ? 'Face Aligned' : 'Align Face Here'}
                      </span>
                    </div>
                  )}

                  {/* State Overlay for Idle & Initializing */}
                  {regStatus === 'idle' && (
                    <div className="absolute inset-0 bg-slate-950/90 flex flex-col items-center justify-center p-6 text-center space-y-3">
                      <Camera className="w-10 h-10 text-indigo-400 animate-bounce" />
                      <p className="text-xs text-slate-300">
                        Click <strong>Enable Camera</strong> to begin identity registration.
                      </p>
                      <button
                        onClick={startFaceRegistrationCamera}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg transition"
                      >
                        Enable Camera
                      </button>
                    </div>
                  )}

                  {regStatus === 'initializing' && (
                    <div className="absolute inset-0 bg-slate-950/80 flex flex-col items-center justify-center text-xs text-slate-400 space-y-2">
                      <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                      <span>Initializing camera and face identity model...</span>
                    </div>
                  )}
                </div>

                {/* Real-time Status Message */}
                {regStatus !== 'idle' && (
                  <div
                    className={`p-3 rounded-xl border text-xs font-mono flex items-center gap-2 transition ${
                      regStatus === 'ALIGNED' || regStatus === 'CAPTURED' || regStatus === 'success'
                        ? 'bg-emerald-950/60 border-emerald-800 text-emerald-300'
                        : regStatus === 'NOT_ALIGNED' || regStatus === 'MULTIPLE_FACES'
                        ? 'bg-amber-950/60 border-amber-800 text-amber-300'
                        : 'bg-slate-950 border-slate-800 text-slate-300'
                    }`}
                  >
                    {regStatus === 'ALIGNED' || regStatus === 'CAPTURED' || regStatus === 'success' ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : regStatus === 'NOT_ALIGNED' || regStatus === 'MULTIPLE_FACES' ? (
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                    ) : (
                      <Info className="w-4 h-4 text-indigo-400 shrink-0" />
                    )}
                    <span>{regMessage}</span>
                  </div>
                )}

                {regError && (
                  <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{regError}</span>
                  </div>
                )}

                {/* Explicit Consent Checkbox */}
                <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-2">
                  <label className="flex items-start gap-2.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={consentGiven}
                      onChange={(e) => setConsentGiven(e.target.checked)}
                      className="mt-0.5 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-slate-300 leading-relaxed text-[11px]">
                      I consent to using my face for examination identity verification.
                    </span>
                  </label>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4">
                <button
                  onClick={handleCloseRegistrationModal}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl transition"
                >
                  Cancel
                </button>

                {regStatus === 'CAPTURED' ? (
                  <>
                    <button
                      onClick={handleRetakeFace}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition flex items-center gap-1.5"
                    >
                      <RotateCcw className="w-3.5 h-3.5" /> Retake
                    </button>
                    <button
                      onClick={handleSaveProfile}
                      disabled={!consentGiven}
                      className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-emerald-600/25 flex items-center gap-2 disabled:opacity-50"
                    >
                      <Save className="w-4 h-4" /> Save Profile
                    </button>
                  </>
                ) : (
                  <button
                    onClick={handleCaptureFace}
                    disabled={regStatus !== 'ALIGNED' || !consentGiven}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50"
                  >
                    <Camera className="w-4 h-4" /> Capture
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* EDIT NAME MODAL */}
        {showEditModal && (
          <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-5 shadow-2xl relative">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <Edit3 className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-base font-bold text-white">Edit Profile Name</h3>
                </div>
                <button
                  onClick={handleCloseEditModal}
                  className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {editError && (
                <div className="p-3 bg-rose-950/80 border border-rose-800 text-rose-300 text-xs rounded-xl flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{editError}</span>
                </div>
              )}

              {editSuccess && (
                <div className="p-3 bg-emerald-950/80 border border-emerald-800 text-emerald-300 text-xs rounded-xl flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{editSuccess}</span>
                </div>
              )}

              <form onSubmit={handleSaveProfileName} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    First Name <span className="text-rose-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={editFirstName}
                    onChange={(e) => setEditFirstName(e.target.value)}
                    required
                    maxLength={100}
                    placeholder="Enter first name"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-indigo-500 transition"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300">
                    Last Name
                  </label>
                  <input
                    type="text"
                    value={editLastName}
                    onChange={(e) => setEditLastName(e.target.value)}
                    maxLength={100}
                    placeholder="Enter last name"
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs focus:outline-none focus:border-indigo-500 transition"
                  />
                </div>

                <div className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-xl text-[11px] text-slate-400 leading-relaxed flex items-start gap-2">
                  <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                  <span>Email, user role, and institutional scope are managed by administrators and cannot be altered directly.</span>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={handleCloseEditModal}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl transition"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={editLoading || !editFirstName.trim()}
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2 disabled:opacity-50"
                  >
                    {editLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" /> Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4" /> Save Changes
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
