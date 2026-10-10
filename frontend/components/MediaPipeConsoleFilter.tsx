'use client';

import { useEffect } from 'react';
import { initMediaPipeConsoleFilter } from '@/lib/mediaPipeLogFilter';

export function MediaPipeConsoleFilter() {
  useEffect(() => {
    initMediaPipeConsoleFilter();
  }, []);

  return null;
}
