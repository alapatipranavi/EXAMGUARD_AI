'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { CameraOff, Mic, MicOff, ShieldCheck, Video, Users, AlertTriangle } from 'lucide-react';
import { proctoringAPI, identityAPI, ProctoringEventType } from '@/lib/api';
import { faceDetector } from '@/lib/faceDetector';
import { objectDetector } from '@/lib/objectDetector';
import { faceIdentityEngine } from '@/lib/faceIdentity';

interface ProctoringCameraProps {
  sessionId: string;
  tabSwitchCount?: number;
  maxTabSwitches?: number;
  isHandwrittenCaptureActive?: boolean;
  onEventLogged?: (eventType: ProctoringEventType, message: string) => void;
  onStatusChange?: (status: { cameraActive: boolean; faceStatus: 'FACE_DETECTED' | 'FACE_NOT_DETECTED' | 'MULTIPLE_FACES_DETECTED' | 'CHECKING' }) => void;
  onAutoSubmit?: (reason: string) => void;
  onStreamReady?: (stream: MediaStream | null) => void;
}

export function ProctoringCamera({
  sessionId,
  tabSwitchCount = 0,
  maxTabSwitches = 3,
  isHandwrittenCaptureActive = false,
  onEventLogged,
  onStatusChange,
  onAutoSubmit,
  onStreamReady,
}: ProctoringCameraProps) {
  const [cameraActive, setCameraActive] = useState<boolean>(false);
  const [micActive, setMicActive] = useState<boolean>(false);
  const [objectDetectorActive, setObjectDetectorActive] = useState<boolean>(false);
  const [faceStatus, setFaceStatus] = useState<'FACE_DETECTED' | 'FACE_NOT_DETECTED' | 'MULTIPLE_FACES_DETECTED' | 'CHECKING'>('CHECKING');
  const [identityStatus, setIdentityStatus] = useState<'VERIFIED' | 'TEMPORARILY_UNVERIFIED' | 'CONFIRMED_IDENTITY_MISMATCH' | 'CHECKING'>('CHECKING');
  const [isMinimized, setIsMinimized] = useState<boolean>(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const assignedStreamRef = useRef<MediaStream | null>(null);
  const lastEventTimeRef = useRef<Record<string, number>>({});
  const lastFaceCountRef = useRef<number | null>(null);
  const lastIdentityCheckTimeRef = useRef<number>(0);
  const isHandwrittenCaptureActiveRef = useRef(isHandwrittenCaptureActive);
  const identityStatusRef = useRef<'VERIFIED' | 'TEMPORARILY_UNVERIFIED' | 'CONFIRMED_IDENTITY_MISMATCH' | 'CHECKING'>('CHECKING');
  const consecutiveMatchRef = useRef<number>(0);
  const consecutiveMismatchRef = useRef<number>(0);
  const isVerifyingIdentityRef = useRef<boolean>(false);

  const onEventLoggedRef = useRef(onEventLogged);
  const onStatusChangeRef = useRef(onStatusChange);
  const onAutoSubmitRef = useRef(onAutoSubmit);
  const onStreamReadyRef = useRef(onStreamReady);

  useEffect(() => {
    isHandwrittenCaptureActiveRef.current = isHandwrittenCaptureActive;
    if (isHandwrittenCaptureActive && faceStatus === 'FACE_NOT_DETECTED') {
      setFaceStatus('FACE_DETECTED');
    }
  }, [isHandwrittenCaptureActive, faceStatus]);

  useEffect(() => {
    onEventLoggedRef.current = onEventLogged;
    onStatusChangeRef.current = onStatusChange;
    onAutoSubmitRef.current = onAutoSubmit;
    onStreamReadyRef.current = onStreamReady;
  }, [onEventLogged, onStatusChange, onAutoSubmit, onStreamReady]);

  const isInitializingRef = useRef(false);
  const isIntentionalCleanupRef = useRef(false);
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const stopAllTracks = useCallback(() => {
    isIntentionalCleanupRef.current = true;
    if (checkIntervalRef.current) {
      clearInterval(checkIntervalRef.current);
      checkIntervalRef.current = null;
    }

    if (videoRef.current) {
      try {
        videoRef.current.pause();
        videoRef.current.onloadedmetadata = null;
        videoRef.current.srcObject = null;
      } catch (e) {
        console.warn('Error clearing video element:', e);
      }
    }

    if (streamRef.current) {
      try {
        const videoTracks = streamRef.current.getVideoTracks();
        videoTracks.forEach((track) => {
          try {
            track.enabled = false;
            track.stop();
          } catch (e) {
            console.warn('Error stopping video track:', e);
          }
        });

        const audioTracks = streamRef.current.getAudioTracks();
        audioTracks.forEach((track) => {
          try {
            track.enabled = false;
            track.stop();
          } catch (e) {
            console.warn('Error stopping audio track:', e);
          }
        });

        const allTracks = streamRef.current.getTracks();
        allTracks.forEach((track) => {
          try {
            track.enabled = false;
            track.stop();
          } catch (e) {
            console.warn('Error stopping track:', e);
          }
        });
      } catch (e) {
        console.warn('Error stopping stream tracks:', e);
      }
      streamRef.current = null;
    }

    assignedStreamRef.current = null;
    setCameraActive(false);
    setMicActive(false);
  }, []);

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

  const recordProctoringEvent = useCallback(
    async (eventType: ProctoringEventType, warningMessage?: string, metadata?: Record<string, any>) => {
      const isTabHidden = eventType === 'TAB_HIDDEN';
      const now = Date.now();
      const lastTime = lastEventTimeRef.current[eventType] || 0;

      // 30-second deduplication for non-TAB_HIDDEN events
      if (!isTabHidden && now - lastTime < 30000) {
        return;
      }

      lastEventTimeRef.current[eventType] = now;

      try {
        const res = await proctoringAPI.recordEvent(sessionId, {
          event_type: eventType,
          metadata_json: metadata,
        });

        if (res.auto_submitted && onAutoSubmitRef.current) {
          onAutoSubmitRef.current(res.flag_reason || 'TAB_SWITCH_LIMIT_EXCEEDED');
        }

        if (warningMessage && onEventLoggedRef.current) {
          onEventLoggedRef.current(eventType, warningMessage);
        }
      } catch (err) {
        console.warn(`Failed to record proctoring event [${eventType}]:`, err);
      }
    },
    [sessionId]
  );

  useEffect(() => {
    if (isInitializingRef.current || streamRef.current) return;
    isInitializingRef.current = true;

    const initMedia = async () => {
      try {
        if (typeof window === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          setCameraActive(false);
          setMicActive(false);
          return;
        }

        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 320 }, height: { ideal: 240 }, frameRate: { ideal: 15 } },
          audio: true,
        });

        streamRef.current = stream;
        setCameraActive(true);
        setMicActive(true);

        if (onStreamReadyRef.current) {
          onStreamReadyRef.current(stream);
        }

        if (videoRef.current) {
          attachStreamToVideo(videoRef.current, stream);
        }

        recordProctoringEvent('CAMERA_READY');
        recordProctoringEvent('MICROPHONE_READY');

        // Monitor video track disconnected state
        const videoTrack = stream.getVideoTracks()[0];
        if (videoTrack) {
          videoTrack.onended = () => {
            if (isIntentionalCleanupRef.current) return;
            setCameraActive(false);
            recordProctoringEvent('CAMERA_DISCONNECTED', 'Camera stream was disconnected. Please check your camera.');
          };
        }

        // Monitor microphone track disconnected state
        const audioTrack = stream.getAudioTracks()[0];
        if (audioTrack) {
          audioTrack.onended = () => {
            if (isIntentionalCleanupRef.current) return;
            setMicActive(false);
            recordProctoringEvent('MICROPHONE_DISCONNECTED', 'Microphone stream was disconnected. Please check your microphone.');
          };
        }

        const isSupported = faceDetector.checkSupport();
        const objSupported = objectDetector.checkSupport();

        if (objSupported) {
          objectDetector.init().then((success) => {
            if (success) {
              setObjectDetectorActive(true);
              recordProctoringEvent('OBJECT_DETECTION_STARTED');
            } else {
              setObjectDetectorActive(false);
              recordProctoringEvent('OBJECT_DETECTION_UNAVAILABLE', undefined, { reason: 'ObjectDetector init failed' });
            }
          }).catch((err) => {
            setObjectDetectorActive(false);
            recordProctoringEvent('OBJECT_DETECTION_UNAVAILABLE', undefined, { reason: String(err) });
          });
        } else {
          setObjectDetectorActive(false);
          recordProctoringEvent('OBJECT_DETECTION_UNAVAILABLE', undefined, { reason: 'ObjectDetector unsupported' });
        }

        checkIntervalRef.current = setInterval(async () => {
          if (!videoRef.current || videoRef.current.readyState < 2) return;

          try {
            // Face presence detection
            if (isSupported) {
              const res = await faceDetector.detect(videoRef.current, Date.now());
              const currentCount = res.faceCount;
              const prevCount = lastFaceCountRef.current;

              // Only act / log on state transition or initial detection
              if (currentCount !== prevCount) {
                lastFaceCountRef.current = currentCount;

                if (currentCount === 0) {
                  const isCapturing = isHandwrittenCaptureActiveRef.current;
                  setFaceStatus(isCapturing ? 'FACE_DETECTED' : 'FACE_NOT_DETECTED');
                  if (onStatusChangeRef.current) {
                    onStatusChangeRef.current({ cameraActive: true, faceStatus: isCapturing ? 'FACE_DETECTED' : 'FACE_NOT_DETECTED' });
                  }
                  const warningMsg = isCapturing
                    ? undefined
                    : 'Face not detected. Please remain visible to the camera.';
                  recordProctoringEvent('FACE_NOT_DETECTED', warningMsg);
                } else if (currentCount === 1) {
                  setFaceStatus('FACE_DETECTED');
                  if (onStatusChangeRef.current) onStatusChangeRef.current({ cameraActive: true, faceStatus: 'FACE_DETECTED' });
                  if (prevCount !== null) {
                    recordProctoringEvent('FACE_DETECTED');
                  }
                } else if (currentCount > 1) {
                  setFaceStatus('MULTIPLE_FACES_DETECTED');
                  if (onStatusChangeRef.current) onStatusChangeRef.current({ cameraActive: true, faceStatus: 'MULTIPLE_FACES_DETECTED' });
                  recordProctoringEvent('MULTIPLE_FACES_DETECTED', 'Multiple faces detected in camera view.');
                }
              }

              // Stage 14.1 Continuous Identity Verification with Multi-Frame Confirmation
              // Suppress identity verification checks during intentional handwritten answer sheet capture
              const isCapturing = isHandwrittenCaptureActiveRef.current;
              const checkIntervalMs = identityStatusRef.current === 'TEMPORARILY_UNVERIFIED' ? 5000 : 15000;
              if (
                !isCapturing &&
                currentCount === 1 &&
                Date.now() - lastIdentityCheckTimeRef.current >= checkIntervalMs &&
                !isVerifyingIdentityRef.current
              ) {
                lastIdentityCheckTimeRef.current = Date.now();
                isVerifyingIdentityRef.current = true;
                try {
                  const idRes = await faceIdentityEngine.extractFaceEmbedding(videoRef.current, Date.now());
                  if (idRes.success && idRes.embedding) {
                    const vRes = await identityAPI.verifySessionIdentity(sessionId, { face_embedding: idRes.embedding });
                    if (vRes.verified && (vRes.similarity ?? 0) >= 0.80) {
                      consecutiveMatchRef.current += 1;
                      consecutiveMismatchRef.current = 0;
                      // If temporarily unverified, require 2 consecutive matching observations before restoring VERIFIED
                      if (identityStatusRef.current === 'TEMPORARILY_UNVERIFIED') {
                        if (consecutiveMatchRef.current >= 2) {
                          identityStatusRef.current = 'VERIFIED';
                          setIdentityStatus('VERIFIED');
                          if (onEventLoggedRef.current) {
                            onEventLoggedRef.current('IDENTITY_VERIFICATION_RESTORED', 'Student identity restored.');
                          }
                        }
                      } else {
                        identityStatusRef.current = 'VERIFIED';
                        setIdentityStatus('VERIFIED');
                      }
                    } else if (vRes.status === 'CONFIRMED_IDENTITY_MISMATCH') {
                      identityStatusRef.current = 'CONFIRMED_IDENTITY_MISMATCH';
                      setIdentityStatus('CONFIRMED_IDENTITY_MISMATCH');
                      if (onEventLoggedRef.current) {
                        onEventLoggedRef.current('IDENTITY_MISMATCH_CONFIRMED', vRes.message);
                      }
                    } else {
                      consecutiveMismatchRef.current += 1;
                      consecutiveMatchRef.current = 0;
                      // Do not transition to TEMPORARILY_UNVERIFIED on a single noisy frame; require 2 consecutive mismatches
                      if (identityStatusRef.current === 'VERIFIED') {
                        if (consecutiveMismatchRef.current >= 2) {
                          identityStatusRef.current = 'TEMPORARILY_UNVERIFIED';
                          setIdentityStatus('TEMPORARILY_UNVERIFIED');
                          if (onEventLoggedRef.current) {
                            onEventLoggedRef.current('IDENTITY_MISMATCH_STARTED', vRes.message);
                          }
                        }
                      } else {
                        identityStatusRef.current = 'TEMPORARILY_UNVERIFIED';
                        setIdentityStatus('TEMPORARILY_UNVERIFIED');
                      }
                    }
                  }
                } catch (idErr) {
                  // Non-blocking catch
                } finally {
                  isVerifyingIdentityRef.current = false;
                }
              }
            } else {
              setFaceStatus('FACE_NOT_DETECTED');
              if (onStatusChangeRef.current) onStatusChangeRef.current({ cameraActive: true, faceStatus: 'FACE_NOT_DETECTED' });
            }

            // Object & Environment Detection Loop (Stage 9.2)
            if (objectDetector.checkSupport()) {
              const objRes = await objectDetector.detect(videoRef.current, Date.now());
              if (objRes.supported && objRes.detectedObjects.length > 0) {
                // Check Mobile Phone
                const phoneItem = objRes.detectedObjects.find(
                  (i) => i.categoryName === 'cell phone' || i.categoryName.includes('phone')
                );
                if (phoneItem && objectDetector.evaluateStateTransition('cell phone', true)) {
                  recordProctoringEvent(
                    'PHONE_DETECTED',
                    'Potential mobile phone detected. Please keep your examination environment clear.',
                    { object: 'cell phone', confidence: phoneItem.score }
                  );
                } else if (!phoneItem) {
                  objectDetector.evaluateStateTransition('cell phone', false);
                }

                // Check Additional Laptop / Display Device
                const laptopItem = objRes.detectedObjects.find(
                  (i) => i.categoryName === 'laptop' || i.categoryName.includes('laptop')
                );
                if (laptopItem && objectDetector.evaluateStateTransition('laptop', true)) {
                  recordProctoringEvent(
                    'LAPTOP_DETECTED',
                    'Prohibited object detected: Additional device. Please remove it from camera view.',
                    { object: 'laptop', confidence: laptopItem.score }
                  );
                } else if (!laptopItem) {
                  objectDetector.evaluateStateTransition('laptop', false);
                }

                // Check Book / Notes
                const bookItem = objRes.detectedObjects.find(
                  (i) => i.categoryName === 'book' || i.categoryName.includes('book')
                );
                if (bookItem && objectDetector.evaluateStateTransition('book', true)) {
                  const isCapturing = isHandwrittenCaptureActiveRef.current;
                  const warningMsg = isCapturing
                    ? undefined
                    : 'Prohibited object detected: Book / Notes. Please remove it from camera view.';
                  recordProctoringEvent(
                    'BOOK_DETECTED',
                    warningMsg,
                    { object: 'book', confidence: bookItem.score }
                  );
                } else if (!bookItem) {
                  objectDetector.evaluateStateTransition('book', false);
                }

                // Check Additional Person Presence
                const personItems = objRes.detectedObjects.filter((i) => i.categoryName === 'person');
                if (personItems.length >= 2 && objectDetector.evaluateStateTransition('additional_person', true)) {
                  recordProctoringEvent(
                    'ADDITIONAL_PERSON_DETECTED',
                    'Potential additional person detected in room environment.',
                    { object: 'person', count: personItems.length }
                  );
                } else if (personItems.length < 2) {
                  objectDetector.evaluateStateTransition('additional_person', false);
                }
              } else if (objRes.supported) {
                objectDetector.evaluateStateTransition('cell phone', false);
                objectDetector.evaluateStateTransition('laptop', false);
                objectDetector.evaluateStateTransition('additional_person', false);
              }
            }
          } catch (err) {
            console.warn('Proctoring detection loop error:', err);
          }
        }, 3000);
      } catch (err: any) {
        console.warn('Camera/mic initialization failed:', err);
        setCameraActive(false);
        setMicActive(false);
        recordProctoringEvent('CAMERA_PERMISSION_DENIED', 'Camera access was denied or unavailable.');
      }
    };

    initMedia();

    return () => {
      stopAllTracks();
      if (onStreamReadyRef.current) {
        onStreamReadyRef.current(null);
      }
      isInitializingRef.current = false;
    };
  }, [sessionId, recordProctoringEvent, attachStreamToVideo, stopAllTracks]);

  return (
    <div className="fixed bottom-4 right-4 z-40">
      <div className="bg-slate-900/95 border border-slate-800 rounded-xl shadow-2xl overflow-hidden backdrop-blur-md transition-all duration-200 min-w-[220px]">
        {/* Header Bar */}
        <div className="px-3 py-2 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between space-x-3">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  cameraActive && micActive && faceStatus === 'FACE_DETECTED'
                    ? 'bg-emerald-400'
                    : faceStatus === 'MULTIPLE_FACES_DETECTED' || faceStatus === 'FACE_NOT_DETECTED'
                    ? 'bg-amber-400'
                    : 'bg-rose-400'
                }`}
              />
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  cameraActive && micActive && faceStatus === 'FACE_DETECTED'
                    ? 'bg-emerald-500'
                    : faceStatus === 'MULTIPLE_FACES_DETECTED' || faceStatus === 'FACE_NOT_DETECTED'
                    ? 'bg-amber-500'
                    : 'bg-rose-500'
                }`}
              />
            </span>
            <span className="text-xs font-semibold text-slate-200">
              {faceStatus === 'FACE_DETECTED'
                ? 'Proctoring Active'
                : faceStatus === 'MULTIPLE_FACES_DETECTED'
                ? 'Multiple Faces'
                : faceStatus === 'FACE_NOT_DETECTED'
                ? 'Face Not Detected'
                : 'Connecting...'}
            </span>
          </div>

          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="text-xs text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded hover:bg-slate-800 transition-colors"
          >
            {isMinimized ? 'Expand' : 'Hide'}
          </button>
        </div>

        {/* Compact Proctoring Status Bar */}
        <div className="px-3 py-1.5 bg-slate-900/80 border-b border-slate-800/80 flex items-center justify-between text-[11px]">
          <div className="flex items-center space-x-3 text-slate-400">
            <span className="flex items-center space-x-1" title={cameraActive ? 'Camera Connected' : 'Camera Disconnected'}>
              {cameraActive ? <Video className="w-3.5 h-3.5 text-emerald-400" /> : <CameraOff className="w-3.5 h-3.5 text-rose-400" />}
              <span className={cameraActive ? 'text-emerald-400' : 'text-rose-400'}>{cameraActive ? 'Cam' : 'No Cam'}</span>
            </span>

            <span className="flex items-center space-x-1" title={micActive ? 'Microphone Connected' : 'Microphone Disconnected'}>
              {micActive ? <Mic className="w-3.5 h-3.5 text-emerald-400" /> : <MicOff className="w-3.5 h-3.5 text-rose-400" />}
              <span className={micActive ? 'text-emerald-400' : 'text-rose-400'}>{micActive ? 'Mic' : 'No Mic'}</span>
            </span>

            <span className="flex items-center space-x-1" title={objectDetectorActive ? 'Object Monitoring Active' : 'Object Monitoring Inactive'}>
              <ShieldCheck className={`w-3.5 h-3.5 ${objectDetectorActive ? 'text-emerald-400' : 'text-slate-500'}`} />
              <span className={objectDetectorActive ? 'text-emerald-400' : 'text-slate-500'}>{objectDetectorActive ? 'Objects' : 'Obj Off'}</span>
            </span>
          </div>

          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
            Tabs: {tabSwitchCount}/{maxTabSwitches}
          </span>
        </div>

        {/* Persistent Video Frame */}
        {!isMinimized && (
          <div className="relative w-full h-32 bg-slate-950 flex items-center justify-center overflow-hidden">
            <video
              ref={setVideoRef}
              autoPlay
              playsInline
              muted
              className={`w-full h-full object-cover transform -scale-x-100 ${cameraActive ? 'block' : 'hidden'}`}
            />
            {!cameraActive && (
              <div className="flex flex-col items-center space-y-1 text-slate-500">
                <CameraOff className="w-6 h-6 stroke-1 text-rose-400" />
                <span className="text-[10px] text-rose-300 font-medium">Camera Offline</span>
              </div>
            )}

            <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-slate-950/70 text-[9px] text-slate-400 border border-slate-800 flex items-center space-x-1">
              <ShieldCheck className="w-2.5 h-2.5 text-blue-400" />
              <span>AI Guard</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
