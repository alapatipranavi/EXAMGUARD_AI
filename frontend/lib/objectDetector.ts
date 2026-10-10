'use client';

import { initMediaPipeConsoleFilter } from './mediaPipeLogFilter';

initMediaPipeConsoleFilter();

export interface ObjectDetectionItem {
  categoryName: string;
  score: number;
}

export interface ObjectDetectionResult {
  supported: boolean;
  detectedObjects: ObjectDetectionItem[];
  statusText: string;
  error?: string;
}

export interface ProhibitedClassSupportInfo {
  categoryKey: string;
  displayName: string;
  isSupported: boolean;
  modelClassLabel?: string;
  unsupportedReason?: string;
  confidenceThreshold: number;
}

/**
 * Explicit Prohibited Object Taxonomy.
 * Clearly documents supported vs unsupported classes in the underlying COCO vision model.
 */
export const PROHIBITED_OBJECT_TAXONOMY: ProhibitedClassSupportInfo[] = [
  {
    categoryKey: 'cell phone',
    displayName: 'Mobile Phone',
    isSupported: true,
    modelClassLabel: 'cell phone',
    confidenceThreshold: 0.50,
  },
  {
    categoryKey: 'laptop',
    displayName: 'Laptop / Computer',
    isSupported: true,
    modelClassLabel: 'laptop',
    confidenceThreshold: 0.55,
  },
  {
    categoryKey: 'book',
    displayName: 'Book / Notebook / Notes',
    isSupported: true,
    modelClassLabel: 'book',
    confidenceThreshold: 0.50,
  },
  {
    categoryKey: 'additional_person',
    displayName: 'Additional Person',
    isSupported: true,
    modelClassLabel: 'person',
    confidenceThreshold: 0.55,
  },
  {
    categoryKey: 'smartwatch',
    displayName: 'Smartwatch / Wearable',
    isSupported: false,
    unsupportedReason: 'Class "smartwatch" is not present in standard COCO 80-class vision model',
    confidenceThreshold: 0.0,
  },
  {
    categoryKey: 'headphones',
    displayName: 'Headphones / Earbuds',
    isSupported: false,
    unsupportedReason: 'Class "headphones" is not present in standard COCO 80-class vision model',
    confidenceThreshold: 0.0,
  },
  {
    categoryKey: 'tablet',
    displayName: 'Tablet Device',
    isSupported: false,
    unsupportedReason: 'Class "tablet" is not present in standard COCO 80-class vision model',
    confidenceThreshold: 0.0,
  },
];

export const OBJECT_DETECTION_CONFIDENCE_THRESHOLD = 0.50;

export class GenuineObjectDetector {
  private detectorInstance: any = null;
  private initPromise: Promise<boolean> | null = null;
  private initFailed: boolean = false;
  private initErrorMsg: string | null = null;
  private activeStateMap: Record<string, boolean> = {};

  public async init(): Promise<boolean> {
    if (typeof window === 'undefined') return false;
    if (this.detectorInstance) return true;
    if (this.initFailed) return false;
    if (this.initPromise) return this.initPromise;

    this.initPromise = (async () => {
      try {
        let visionModule: any = null;
        try {
          const importDynamic = new Function('url', 'return import(url)');
          visionModule = await importDynamic(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs'
          );
        } catch (dynamicErr) {
          console.warn('Dynamic import of MediaPipe ObjectDetector module failed:', dynamicErr);
        }

        if (visionModule && visionModule.FilesetResolver && visionModule.ObjectDetector) {
          const filesetResolver = await visionModule.FilesetResolver.forVisionTasks(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
          );
          this.detectorInstance = await visionModule.ObjectDetector.createFromOptions(filesetResolver, {
            baseOptions: {
              modelAssetPath:
                'https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite',
            },
            scoreThreshold: 0.45,
            runningMode: 'VIDEO',
          });
          return true;
        }

        throw new Error('MediaPipe ObjectDetector module unavailable.');
      } catch (err: any) {
        const msg = err && typeof err === 'object' && err.message ? err.message : String(err);
        console.warn('ObjectDetector initialization error:', msg);
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

  public getTaxonomy(): ProhibitedClassSupportInfo[] {
    return PROHIBITED_OBJECT_TAXONOMY;
  }

  public async detect(
    videoElement: HTMLVideoElement | null,
    timestampMs: number = Date.now()
  ): Promise<ObjectDetectionResult> {
    if (!videoElement || videoElement.readyState < 2) {
      return {
        supported: true,
        detectedObjects: [],
        statusText: 'Waiting for video feed...',
      };
    }

    const initialized = await this.init();
    if (!initialized || !this.detectorInstance) {
      return {
        supported: false,
        detectedObjects: [],
        statusText: 'Object detection unavailable.',
        error: this.initErrorMsg || 'INITIALIZATION_FAILED',
      };
    }

    try {
      const results = this.detectorInstance.detectForVideo(videoElement, timestampMs);
      const items: ObjectDetectionItem[] = [];

      if (results && results.detections) {
        for (const det of results.detections) {
          if (det.categories && det.categories.length > 0) {
            const topCategory = det.categories[0];
            const catName = topCategory.categoryName.toLowerCase();
            let threshold = OBJECT_DETECTION_CONFIDENCE_THRESHOLD;

            if (catName === 'cell phone' || catName.includes('phone')) {
              threshold = 0.50;
            } else if (catName === 'laptop') {
              threshold = 0.55;
            } else if (catName === 'book') {
              threshold = 0.50;
            } else if (catName === 'person') {
              threshold = 0.55;
            }

            if (topCategory.score >= threshold) {
              items.push({
                categoryName: catName,
                score: topCategory.score,
              });
            }
          }
        }
      }

      return {
        supported: true,
        detectedObjects: items,
        statusText: items.length > 0 ? `Detected: ${items.map((i) => i.categoryName).join(', ')}` : 'Environment Clear',
      };
    } catch (err: any) {
      console.warn('Object detection inference error:', err);
      return {
        supported: true,
        detectedObjects: [],
        statusText: 'Inference error',
        error: String(err),
      };
    }
  }

  /**
   * Anti-Spam State Transition Helper.
   * Returns true ONLY when an object transitions from absent -> present.
   */
  public evaluateStateTransition(targetCategory: string, isCurrentlyPresent: boolean): boolean {
    const wasPresent = !!this.activeStateMap[targetCategory];

    if (isCurrentlyPresent && !wasPresent) {
      this.activeStateMap[targetCategory] = true;
      return true; // Transition triggered -> report event once
    } else if (!isCurrentlyPresent && wasPresent) {
      this.activeStateMap[targetCategory] = false;
      return false; // Cleared
    }

    return false;
  }

  public resetState(): void {
    this.activeStateMap = {};
  }
}

export const objectDetector = new GenuineObjectDetector();
