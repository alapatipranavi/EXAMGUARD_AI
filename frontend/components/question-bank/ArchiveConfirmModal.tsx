'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface ArchiveConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  questionText?: string;
  loading?: boolean;
}

export default function ArchiveConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  questionText,
  loading = false,
}: ArchiveConfirmModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl max-w-md w-full p-6 space-y-4">
        <div className="flex items-center gap-3 text-amber-400">
          <AlertTriangle className="w-6 h-6 flex-shrink-0" />
          <h3 className="text-lg font-extrabold text-white">Archive Question</h3>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          Are you sure you want to archive this question? It will be marked as inactive and removed from active paper generation pools.
        </p>

        {questionText && (
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs italic text-slate-400 max-h-24 overflow-y-auto">
            &ldquo;{questionText}&rdquo;
          </div>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-xs font-semibold text-slate-300 bg-slate-800 rounded-xl hover:bg-slate-700 transition"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-xs font-semibold text-white bg-red-600 rounded-xl hover:bg-red-500 disabled:opacity-50 transition shadow-md shadow-red-600/20"
          >
            {loading ? 'Archiving...' : 'Archive Question'}
          </button>
        </div>
      </div>
    </div>
  );
}
