'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Camera,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  FileText,
  Sparkles,
  Eye,
  Trash2,
  X,
  Image as ImageIcon,
} from 'lucide-react';
import { studentExamsAPI, submitHandwrittenAnswer, HandwrittenAnswerProcessResponse } from '@/lib/api';

interface HandwrittenAnswerSectionProps {
  sessionId: string;
  questionId: string;
  marks: number;
  isCompleted: boolean;
  currentAnswerImageUrl?: string | null;
  currentOcrStatus?: string | null;
  currentOcrConfidence?: number | null;
  currentExtractedText?: string | null;
  onAnswerSaved: (data: {
    answer_image_url: string;
    ocr_status: string;
    ocr_confidence?: number | null;
    extracted_text: string;
  }) => void;
  onAnswerCleared: () => void;
  onCaptureActiveChange?: (isActive: boolean) => void;
}

export default function HandwrittenAnswerSection({
  sessionId,
  questionId,
  marks,
  isCompleted,
  currentAnswerImageUrl,
  currentOcrStatus,
  currentOcrConfidence,
  currentExtractedText,
  onAnswerSaved,
  onAnswerCleared,
  onCaptureActiveChange,
}: HandwrittenAnswerSectionProps) {
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isCaptureWorkflowActive, setIsCaptureWorkflowActive] = useState(false);
  const [capturedImageData, setCapturedImageData] = useState<string | null>(null);
  const [previewImageData, setPreviewImageData] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Status message after processing
  const [processResult, setProcessResult] = useState<HandwrittenAnswerProcessResponse | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Stop camera when unmounting or stopping capture
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  // Reset component temporary capture state whenever questionId changes
  useEffect(() => {
    stopCamera();
    setCapturedImageData(null);
    setPreviewImageData(null);
    setValidationError(null);
    setProcessResult(null);
    setSaving(false);
    setIsCaptureWorkflowActive(false);
  }, [questionId]);

  // Report active handwritten capture workflow state to parent (to suppress Face Not Detected warning)
  useEffect(() => {
    onCaptureActiveChange?.(isCaptureWorkflowActive);
    return () => {
      onCaptureActiveChange?.(false);
    };
  }, [isCaptureWorkflowActive, onCaptureActiveChange]);

  const handleStartCapture = async () => {
    setIsCaptureWorkflowActive(true);
    setValidationError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      setIsCameraActive(true);
      setPreviewImageData(null);
      setCapturedImageData(null);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (err: any) {
      setValidationError('Camera permission denied or unavailable. Please check camera settings.');
      setIsCaptureWorkflowActive(false);
    }
  };

  const handleCancelCapture = () => {
    stopCamera();
    setIsCaptureWorkflowActive(false);
  };

  // Re-attach stream to video element when videoRef becomes ready
  useEffect(() => {
    if (isCameraActive && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [isCameraActive]);

  const handleSnapPicture = () => {
    if (!videoRef.current) return;

    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/png');

    // Perform capture validation
    if (canvas.width < 100 || canvas.height < 100) {
      setValidationError('Captured resolution is too low. Please capture again.');
      return;
    }

    // Basic blank image detection (sample pixels)
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let sum = 0;
    let sumSq = 0;
    const totalPixels = imgData.length / 4;

    for (let i = 0; i < imgData.length; i += 16) {
      const gray = (imgData[i] + imgData[i + 1] + imgData[i + 2]) / 3;
      sum += gray;
      sumSq += gray * gray;
    }

    const sampleCount = totalPixels / 4;
    const mean = sum / sampleCount;
    const variance = sumSq / sampleCount - mean * mean;
    const stddev = Math.sqrt(Math.max(0, variance));

    if (stddev < 2.5) {
      setValidationError('Answer image is unclear or blank. Please capture the handwritten answer again.');
      return;
    }

    setValidationError(null);
    setCapturedImageData(dataUrl);
    setPreviewImageData(dataUrl);
    stopCamera();
  };

  const handleRetake = () => {
    setCapturedImageData(null);
    setPreviewImageData(null);
    setValidationError(null);
    handleStartCapture();
  };

  const handleConfirmAndSave = async () => {
    if (!capturedImageData) return;
    setSaving(true);
    setValidationError(null);
    try {
      const submitFn =
        typeof studentExamsAPI?.submitHandwrittenAnswer === 'function'
          ? studentExamsAPI.submitHandwrittenAnswer
          : submitHandwrittenAnswer;
      const res = await submitFn(sessionId, questionId, capturedImageData);
      setProcessResult(res);
      onAnswerSaved({
        answer_image_url: res.answer_image_url,
        ocr_status: res.ocr_status,
        ocr_confidence: res.ocr_confidence,
        extracted_text: res.extracted_text,
      });
      setPreviewImageData(null);
      setCapturedImageData(null);
      setIsCaptureWorkflowActive(false);
    } catch (err: any) {
      setValidationError(err?.message || 'Failed to process handwritten answer. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleClearSavedAnswer = () => {
    setProcessResult(null);
    setCapturedImageData(null);
    setPreviewImageData(null);
    setIsCaptureWorkflowActive(false);
    onAnswerCleared();
  };

  const getOcrBadge = (status?: string | null) => {
    switch (status) {
      case 'OCR_SUCCESS':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 flex items-center gap-1 inline-flex">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" /> OCR Completed
          </span>
        );
      case 'OCR_LOW_CONFIDENCE':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase bg-amber-950/80 text-amber-300 border border-amber-800/80 flex items-center gap-1 inline-flex">
            <AlertTriangle className="w-3 h-3 text-amber-400" /> OCR Low Confidence (Pending Review)
          </span>
        );
      case 'OCR_FAILED':
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase bg-rose-950/80 text-rose-300 border border-rose-800/80 flex items-center gap-1 inline-flex">
            <AlertTriangle className="w-3 h-3 text-rose-400" /> Pending Examiner Review
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase bg-slate-900 text-slate-400 border border-slate-800 flex items-center gap-1 inline-flex">
            <FileText className="w-3 h-3 text-slate-400" /> Pending Capture
          </span>
        );
    }
  };

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const displayImageUrl = currentAnswerImageUrl
    ? currentAnswerImageUrl.startsWith('data:') || currentAnswerImageUrl.startsWith('http')
      ? currentAnswerImageUrl
      : `${API_BASE_URL}${currentAnswerImageUrl}`
    : null;

  return (
    <div className="space-y-4">
      {/* Workflow Instructions Header */}
      <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-white font-mono uppercase tracking-wider flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-indigo-400" /> Handwritten Answer Sheet Scanner
          </span>
          {getOcrBadge(currentOcrStatus || processResult?.ocr_status)}
        </div>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          Show your handwritten paper to the camera, capture a clear picture, preview it, and click <strong>Confirm & Save</strong>.
        </p>
      </div>

      {/* Validation Error Banner */}
      {validationError && (
        <div className="p-3.5 bg-rose-950/80 border border-rose-800/80 rounded-xl text-xs text-rose-300 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Process Notification Banner */}
      {processResult && (
        <div className="p-3.5 bg-indigo-950/80 border border-indigo-800/80 rounded-xl text-xs text-indigo-200 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{processResult.message}</span>
        </div>
      )}

      {/* 1. Saved Answer Display State */}
      {displayImageUrl && !isCameraActive && !previewImageData && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300 font-mono">Current Saved Answer Sheet:</span>
            {!isCompleted && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleStartCapture}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition flex items-center gap-1.5"
                >
                  <RotateCcw className="w-3.5 h-3.5" /> Retake & Replace
                </button>
                <button
                  type="button"
                  onClick={handleClearSavedAnswer}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-rose-300 text-xs font-semibold rounded-lg border border-slate-700 transition flex items-center gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Clear
                </button>
              </div>
            )}
          </div>

          <div className="relative border border-slate-800 rounded-lg overflow-hidden bg-slate-950 max-h-80 flex items-center justify-center p-2">
            <img
              src={displayImageUrl}
              alt="Handwritten Answer Sheet"
              className="max-h-72 object-contain rounded"
            />
          </div>

          {(currentExtractedText || processResult?.extracted_text) && (
            <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-lg space-y-1">
              <span className="text-[10px] font-mono text-slate-500 uppercase block">OCR Extracted Text:</span>
              <p className="text-xs text-slate-300 italic font-mono whitespace-pre-wrap">
                {currentExtractedText || processResult?.extracted_text}
              </p>
            </div>
          )}
        </div>
      )}

      {/* 2. Active Camera Scanning Interface */}
      {isCameraActive && (
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-4 text-center">
          <div className="relative border-2 border-dashed border-indigo-500/60 rounded-xl overflow-hidden bg-black max-w-xl mx-auto min-h-[300px] flex items-center justify-center">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full max-h-[360px] object-cover"
            />
            <div className="absolute inset-0 border-2 border-indigo-400/40 pointer-events-none rounded-xl m-4 flex items-center justify-center">
              <span className="bg-slate-950/80 text-indigo-300 font-mono text-[10px] px-3 py-1 rounded-full border border-indigo-500/30">
                Align Handwritten Sheet Inside Border
              </span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleSnapPicture}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/25 transition flex items-center gap-2"
            >
              <Camera className="w-4 h-4" /> Capture Answer Sheet
            </button>
            <button
              type="button"
              onClick={handleCancelCapture}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* 3. Captured Preview & Confirmation Interface */}
      {previewImageData && (
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="text-xs font-bold text-white font-mono uppercase tracking-wider flex items-center gap-1.5">
              <Eye className="w-4 h-4 text-amber-400" /> Preview Captured Answer Sheet
            </span>
            <span className="text-[10px] text-slate-400 font-mono">Verify clarity before saving</span>
          </div>

          <div className="relative border border-slate-800 rounded-lg overflow-hidden bg-slate-950 max-h-80 flex items-center justify-center p-2">
            <img
              src={previewImageData}
              alt="Preview Capture"
              className="max-h-72 object-contain rounded"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
            <button
              type="button"
              disabled={saving}
              onClick={handleRetake}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Retake
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={handleConfirmAndSave}
              className="px-6 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-600/25 transition flex items-center gap-2 disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Processing OCR...
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" /> Confirm & Save
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* 4. Initial Ready State (No image, camera inactive) */}
      {!displayImageUrl && !isCameraActive && !previewImageData && (
        <div className="p-8 bg-slate-950 border border-slate-800 rounded-2xl text-center space-y-4">
          <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-2xl w-fit mx-auto text-indigo-400">
            <Camera className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h4 className="text-xs font-bold text-white">No Handwritten Answer Sheet Captured Yet</h4>
            <p className="text-[11px] text-slate-400 max-w-sm mx-auto leading-relaxed">
              Use your device camera to scan and record your paper response directly into ExamGuard.
            </p>
          </div>

          {!isCompleted && (
            <button
              type="button"
              onClick={handleStartCapture}
              className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/25 transition inline-flex items-center gap-2"
            >
              <Camera className="w-4 h-4" /> Scan / Capture Answer Sheet
            </button>
          )}
        </div>
      )}
    </div>
  );
}
