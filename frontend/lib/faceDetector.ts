'use client';

import { initMediaPipeConsoleFilter } from './mediaPipeLogFilter';

initMediaPipeConsoleFilter();

export interface FaceDetectionResult {
  supported: boolean;
  faceCount: number;
  statusText: string;
  error?: string;
}

export class GenuineFaceDetector {
  private detectorInstance: any = null;
  private initPromise: Promise<boolean> | null = null;
  private isNativeDetector: boolean = false;
  private initFailed: boolean = false;
  private initErrorMsg: string | null = null;

  public async init(): Promise<boolean> {
    if (typeof window === 'undefined') return false;
    if (this.detectorInstance) return true;
    if (this.initFailed) return false;
    if (this.initPromise) return this.initPromise;

    this.initPromise = (async () => {
      try {
        // 1. Check for native FaceDetector API (Shape Detection API in Chrome/Edge Android or flags)
        if ('FaceDetector' in window) {
          try {
            const NativeDetector = (window as any).FaceDetector;
            this.detectorInstance = new NativeDetector({ maxDetectedFaces: 5, fastMode: true });
            this.isNativeDetector = true;
            return true;
          } catch (e) {
            console.warn('Native FaceDetector initialization failed, falling back to MediaPipe:', e);
          }
        }

        // 2. Load MediaPipe Tasks Vision dynamically on client side without top-level module imports
        let visionModule: any = null;
        try {
          const importDynamic = new Function('url', 'return import(url)');
          visionModule = await importDynamic(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs'
          );
        } catch (dynamicErr) {
          console.warn('Dynamic import of MediaPipe module failed:', dynamicErr);
        }

        if (visionModule && visionModule.FilesetResolver && visionModule.FaceDetector) {
          const filesetResolver = await visionModule.FilesetResolver.forVisionTasks(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
          );
          this.detectorInstance = await visionModule.FaceDetector.createFromOptions(filesetResolver, {
            baseOptions: {
              modelAssetPath:
                'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite',
            },
            runningMode: 'VIDEO',
            minDetectionConfidence: 0.5,
          });
          this.isNativeDetector = false;
          return true;
        }

        throw new Error('Face detector module could not be initialized.');
      } catch (err: any) {
        const msg = err && typeof err === 'object' && err.message ? err.message : String(err);
        console.warn('FaceDetector initialization error:', msg);
        this.initFailed = true;
        this.initErrorMsg = msg;
        return false;
      }
    })();

    return this.initPromise;
  }

  public checkSupport(): boolean {
    if (typeof window === 'undefined') return false;
    return !this.initFailed;
  }

  public async detect(
    videoElement: HTMLVideoElement | null,
    timestampMs: number = Date.now()
  ): Promise<FaceDetectionResult> {
    if (!videoElement || videoElement.readyState < 2) {
      return {
        supported: true,
        faceCount: 0,
        statusText: 'Waiting for video feed...',
      };
    }

    const initialized = await this.init();
    if (!initialized || !this.detectorInstance) {
      return {
        supported: false,
        faceCount: 0,
        statusText: 'Face detection could not be initialized. Please check your browser and camera permissions.',
        error: this.initErrorMsg || 'INITIALIZATION_FAILED',
      };
    }

    try {
      let faceCount = 0;

      if (this.isNativeDetector) {
        const faces = await this.detectorInstance.detect(videoElement);
        faceCount = faces ? faces.length : 0;
      } else {
        const result = this.detectorInstance.detectForVideo(videoElement, timestampMs);
        faceCount = result && result.detections ? result.detections.length : 0;
      }

      let statusText = 'Face Detected';
      if (faceCount === 0) {
        statusText = 'Face Not Detected';
      } else if (faceCount > 1) {
        statusText = 'Multiple Faces';
      }

      return {
        supported: true,
        faceCount,
        statusText,
      };
    } catch (err: any) {
      const msg = err && typeof err === 'object' && err.message ? err.message : String(err);
      console.warn('Face detection pass error:', msg);
      return {
        supported: true,
        faceCount: 0,
        statusText: 'Checking face presence...',
        error: msg || 'DETECTION_ERROR',
      };
    }
  }

  public reset(): void {
    if (this.detectorInstance && typeof this.detectorInstance.close === 'function') {
      try {
        this.detectorInstance.close();
      } catch (e) {}
    }
    this.detectorInstance = null;
    this.initPromise = null;
    this.initFailed = false;
    this.initErrorMsg = null;
  }
}

export const faceDetector = new GenuineFaceDetector();
