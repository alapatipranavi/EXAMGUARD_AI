'use client';

let isFilterInstalled = false;

/**
 * Filter harmless MediaPipe Tasks Vision / TensorFlow Lite WASM informational
 * delegate messages that Emscripten outputs to stderr (which defaults to console.error).
 *
 * In Next.js development mode, any call to console.error is captured by the Next.js
 * development overlay, falsely displaying harmless TFLite initialization logs
 * as runtime application errors.
 *
 * Genuine application errors, JavaScript exceptions, and warnings remain completely
 * untouched and pass directly to the original console.error.
 */
export function initMediaPipeConsoleFilter(): void {
  if (typeof window === 'undefined') return;
  if (isFilterInstalled) return;

  const originalConsoleError = console.error;

  const isTFLiteInfoMessage = (arg: any): boolean => {
    if (typeof arg !== 'string') {
      if (arg && typeof arg === 'object' && typeof arg.message === 'string') {
        arg = arg.message;
      } else {
        return false;
      }
    }

    // Check for MediaPipe / TFLite informational delegate messages
    return (
      arg.includes('Created TensorFlow Lite XNNPACK delegate') ||
      arg.includes('TensorFlow Lite XNNPACK delegate') ||
      (arg.startsWith('INFO:') && arg.includes('TensorFlow Lite')) ||
      (arg.startsWith('INFO:') && arg.includes('delegate')) ||
      (arg.includes('Replacing') && arg.includes('delegate (XNNPACK)')) ||
      arg.includes('xnnpack_delegate.cc')
    );
  };

  console.error = function (...args: any[]) {
    // If the message is a harmless TFLite / MediaPipe WASM INFO log
    const hasTFLiteInfo = args.some((arg) => isTFLiteInfoMessage(arg));
    if (hasTFLiteInfo) {
      // Re-route to console.info so developers can still inspect it in DevTools without triggering Next.js error overlay
      if (typeof console.info === 'function') {
        console.info(...args);
      }
      return;
    }

    // Pass through all genuine application errors, exceptions, and stack traces
    originalConsoleError.apply(console, args);
  };

  isFilterInstalled = true;
}

// Auto-initialize immediately when loaded in browser
if (typeof window !== 'undefined') {
  initMediaPipeConsoleFilter();
}
