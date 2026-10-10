'use client';

import { initMediaPipeConsoleFilter } from './mediaPipeLogFilter';

initMediaPipeConsoleFilter();

export const DESCRIPTOR_VERSION = 2;

export interface FaceEmbeddingResult {
  success: boolean;
  faceCount: number;
  embedding?: number[];
  descriptorVersion?: number;
  alignmentStatus?: 'NO_FACE' | 'MULTIPLE_FACES' | 'NOT_ALIGNED' | 'ALIGNED';
  error?: string;
}

export const FACE_ALIGNMENT_CONFIG = {
  CENTER_TOLERANCE_X: 0.18,
  CENTER_TOLERANCE_Y: 0.18,
  MIN_FACE_HEIGHT: 0.20,
  MAX_FACE_HEIGHT: 0.75,
};

export class GenuineFaceIdentityEngine {
  private landmarkerInstance: any = null;
  private initPromise: Promise<boolean> | null = null;
  private initFailed: boolean = false;
  private initErrorMsg: string | null = null;

  public async init(): Promise<boolean> {
    if (typeof window === 'undefined') return false;
    if (this.landmarkerInstance) return true;
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
          console.warn('Dynamic import of MediaPipe Tasks Vision for Identity Engine failed:', dynamicErr);
        }

        if (visionModule && visionModule.FilesetResolver && visionModule.FaceLandmarker) {
          const filesetResolver = await visionModule.FilesetResolver.forVisionTasks(
            'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
          );
          this.landmarkerInstance = await visionModule.FaceLandmarker.createFromOptions(filesetResolver, {
            baseOptions: {
              modelAssetPath:
                'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
            },
            runningMode: 'VIDEO',
            numFaces: 3,
            minFaceDetectionConfidence: 0.5,
            minFacePresenceConfidence: 0.5,
            minTrackingConfidence: 0.5,
          });
          return true;
        }

        throw new Error('FaceLandmarker module could not be initialized.');
      } catch (err: any) {
        const msg = err && typeof err === 'object' && err.message ? err.message : String(err);
        console.warn('FaceLandmarker initialization error:', msg);
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

  public async extractFaceEmbedding(
    videoElement: HTMLVideoElement | null,
    timestampMs: number = Date.now(),
    options: { requireStrictAlignment?: boolean } = {}
  ): Promise<FaceEmbeddingResult> {
    if (!videoElement || videoElement.readyState < 2) {
      return {
        success: false,
        faceCount: 0,
        alignmentStatus: 'NO_FACE',
        error: 'Waiting for video feed...',
      };
    }

    const initialized = await this.init();
    if (!initialized || !this.landmarkerInstance) {
      return {
        success: false,
        faceCount: 0,
        alignmentStatus: 'NO_FACE',
        error: this.initErrorMsg || 'Identity verification engine initialization failed.',
      };
    }

    try {
      const result = this.landmarkerInstance.detectForVideo(videoElement, timestampMs);
      const faceLandmarksList = result && result.faceLandmarks ? result.faceLandmarks : [];
      const faceCount = faceLandmarksList.length;

      if (faceCount === 0) {
        return {
          success: false,
          faceCount: 0,
          alignmentStatus: 'NO_FACE',
          error: 'No face detected. Please position your face inside the camera frame.',
        };
      }

      if (faceCount > 1) {
        return {
          success: false,
          faceCount,
          alignmentStatus: 'MULTIPLE_FACES',
          error: 'Multiple faces detected. Only one person should be visible.',
        };
      }

      // Extract 478 3D landmarks for the single detected face
      const landmarks = faceLandmarksList[0];
      if (!landmarks || landmarks.length < 400) {
        return {
          success: false,
          faceCount: 1,
          alignmentStatus: 'NOT_ALIGNED',
          error: 'Face landmarks incomplete. Please ensure good lighting and clear camera alignment.',
        };
      }

      // Check alignment bounding box against center guide (0.5, 0.5)
      let minX = 1.0, maxX = 0.0, minY = 1.0, maxY = 0.0;
      for (const lm of landmarks) {
        if (lm.x < minX) minX = lm.x;
        if (lm.x > maxX) maxX = lm.x;
        if (lm.y < minY) minY = lm.y;
        if (lm.y > maxY) maxY = lm.y;
      }

      const xCenter = (minX + maxX) / 2;
      const yCenter = (minY + maxY) / 2;
      const faceHeight = maxY - minY;

      const requireStrict = options.requireStrictAlignment ?? false;

      if (requireStrict) {
        const isAligned =
          Math.abs(xCenter - 0.5) <= FACE_ALIGNMENT_CONFIG.CENTER_TOLERANCE_X &&
          Math.abs(yCenter - 0.5) <= FACE_ALIGNMENT_CONFIG.CENTER_TOLERANCE_Y &&
          faceHeight >= FACE_ALIGNMENT_CONFIG.MIN_FACE_HEIGHT &&
          faceHeight <= FACE_ALIGNMENT_CONFIG.MAX_FACE_HEIGHT;

        if (!isAligned) {
          return {
            success: false,
            faceCount: 1,
            alignmentStatus: 'NOT_ALIGNED',
            error: 'Face not aligned. Please position your face inside the circle.',
          };
        }
      } else {
        if (faceHeight < 0.10) {
          return {
            success: false,
            faceCount: 1,
            alignmentStatus: 'NOT_ALIGNED',
            error: 'Face is too far from camera. Please move closer.',
          };
        }
      }

      // Compute normalized 64-dimensional scale & rotation invariant facial landmark descriptor vector
      const embedding = this.computeLandmarkDescriptor(landmarks, videoElement);

      return {
        success: true,
        faceCount: 1,
        alignmentStatus: 'ALIGNED',
        embedding,
        descriptorVersion: DESCRIPTOR_VERSION,
      };
    } catch (err: any) {
      const msg = err && typeof err === 'object' && err.message ? err.message : String(err);
      console.warn('Face landmark extraction error:', msg);
      return {
        success: false,
        faceCount: 0,
        alignmentStatus: 'NO_FACE',
        error: msg || 'FACE_EMBEDDING_EXTRACTION_FAILED',
      };
    }
  }

  private computeLandmarkDescriptor(
    landmarks: Array<{ x: number; y: number; z: number }>,
    videoElement?: HTMLVideoElement | null
  ): number[] {
    const videoWidth = videoElement?.videoWidth || 640;
    const videoHeight = videoElement?.videoHeight || 480;
    const aspectCorrection = videoWidth > 0 ? videoHeight / videoWidth : 0.75;

    const leftOuter = landmarks[33] || { x: 0.35, y: 0.4, z: 0 };
    const leftInner = landmarks[133] || { x: 0.45, y: 0.4, z: 0 };
    const rightInner = landmarks[362] || { x: 0.55, y: 0.4, z: 0 };
    const rightOuter = landmarks[263] || { x: 0.65, y: 0.4, z: 0 };

    const leftEye = {
      x: (leftOuter.x + leftInner.x) / 2,
      y: ((leftOuter.y + leftInner.y) / 2) * aspectCorrection,
      z: ((leftOuter.z || 0) + (leftInner.z || 0)) / 2,
    };

    const rightEye = {
      x: (rightOuter.x + rightInner.x) / 2,
      y: ((rightOuter.y + rightInner.y) / 2) * aspectCorrection,
      z: ((rightOuter.z || 0) + (rightInner.z || 0)) / 2,
    };

    const eyeCenter = {
      x: (leftEye.x + rightEye.x) / 2,
      y: (leftEye.y + rightEye.y) / 2,
      z: (leftEye.z + rightEye.z) / 2,
    };

    const eyeDistance =
      Math.hypot(
        rightEye.x - leftEye.x,
        rightEye.y - leftEye.y,
        rightEye.z - leftEye.z
      ) || 0.1;

    // Roll angle in image plane (makes eye line horizontal regardless of head tilt)
    const dx = rightEye.x - leftEye.x;
    const dy = rightEye.y - leftEye.y;
    const rollAngle = Math.atan2(dy, dx);
    const cosR = Math.cos(-rollAngle);
    const sinR = Math.sin(-rollAngle);

    // Deterministic landmark index order (19 landmarks x 3 = 57 raw dimensions, zero-padded to 64)
    const CANONICAL_LANDMARK_INDICES: number[] = [
      0, 1, 4, 6, 10, 17, 33, 61, 70, 107, 133, 152, 234, 263, 291, 300, 336, 362, 454
    ];

    // Canonical Mean Relative Landmark Positions (strictly zero-centered at eyeCenter=(0,0,0) and eyeDistance=1.0)
    // Empirically calibrated across MediaPipe 3D face landmarks to eliminate shared common facial offset
    const CANONICAL_MEAN: Record<number, [number, number, number]> = {
      0:   [ 0.0488,  0.5397,  0.4908], // upper lip
      1:   [ 0.0144,  0.3420,  0.5576], // nose tip
      4:   [-0.0517, -0.1723,  0.4639], // nose bridge
      6:   [-0.0040, -0.3685,  0.2856], // between eyebrows
      10:  [ 0.0112, -0.6471,  0.0644], // forehead
      17:  [-0.0015,  0.6156,  0.3251], // lower lip
      33:  [-0.6755,  0.0059, -0.0282], // left eye outer
      61:  [-0.3714,  0.6515,  0.3635], // left mouth corner
      70:  [-0.7132, -0.1320, -0.0247], // left eyebrow outer
      107: [-0.2459, -0.3397,  0.3617], // left eyebrow inner
      133: [-0.3193, -0.0383, -0.0410], // left eye inner
      152: [-0.0120,  1.1965,  0.4894], // chin
      234: [-0.9739,  0.2686, -0.1134], // left jaw
      263: [ 0.6791, -0.0446,  0.0627], // right eye outer
      291: [ 0.3852,  0.7964,  0.2054], // right mouth corner
      300: [ 0.7269, -0.1567,  0.0666], // right eyebrow outer
      336: [ 0.2333, -0.2781,  0.3656], // right eyebrow inner
      362: [ 0.3198,  0.0771,  0.0065], // right eye inner
      454: [ 0.9781,  0.3092,  0.2560], // right jaw
    };

    const features: number[] = [];
    const rotatedPoints: Record<number, [number, number, number]> = {};

    // 1. Roll-rotated & mean-subtracted relative 3D landmark deviations
    for (const idx of CANONICAL_LANDMARK_INDICES) {
      const [mx, my, mz] = CANONICAL_MEAN[idx];
      const lm = landmarks[idx] || {
        x: eyeCenter.x + mx * eyeDistance,
        y: (eyeCenter.y + my * eyeDistance) / aspectCorrection,
        z: eyeCenter.z + mz * eyeDistance,
      };

      const tx = (lm.x - eyeCenter.x) / eyeDistance;
      const ty = ((lm.y * aspectCorrection) - eyeCenter.y) / eyeDistance;
      const tz = ((lm.z || 0) - eyeCenter.z) / eyeDistance;

      const rx = tx * cosR - ty * sinR;
      const ry = tx * sinR + ty * cosR;
      const rz = tz;

      rotatedPoints[idx] = [rx, ry, rz];

      features.push(rx - mx);
      features.push(ry - my);
      features.push(rz - mz);
    }

    // 2. Pad zero-mean landmark residual vector to exactly 64 floats
    while (features.length < 64) {
      features.push(0.0);
    }
    const descriptor = features.slice(0, 64);

    // L2 Normalize vector to unit length
    const norm = Math.sqrt(descriptor.reduce((sum, val) => sum + val * val, 0));
    if (norm > 0) {
      return descriptor.map((v) => v / norm);
    }

    return descriptor;
  }

  public compareEmbeddings(embeddingA: number[], embeddingB: number[]): { match: boolean; similarity: number } {
    if (!embeddingA || !embeddingB || embeddingA.length !== embeddingB.length) {
      return { match: false, similarity: 0.0 };
    }

    let dot = 0.0;
    let normA = 0.0;
    let normB = 0.0;

    for (let i = 0; i < embeddingA.length; i++) {
      dot += embeddingA[i] * embeddingB[i];
      normA += embeddingA[i] * embeddingA[i];
      normB += embeddingB[i] * embeddingB[i];
    }

    const similarity = normA > 0 && normB > 0 ? dot / (Math.sqrt(normA) * Math.sqrt(normB)) : 0.0;
    return {
      match: similarity >= 0.80,
      similarity: Math.max(-1.0, Math.min(1.0, similarity)),
    };
  }

  public reset(): void {
    if (this.landmarkerInstance && typeof this.landmarkerInstance.close === 'function') {
      try {
        this.landmarkerInstance.close();
      } catch (e) {}
    }
    this.landmarkerInstance = null;
    this.initPromise = null;
    this.initFailed = false;
    this.initErrorMsg = null;
  }
}

export const faceIdentityEngine = new GenuineFaceIdentityEngine();
