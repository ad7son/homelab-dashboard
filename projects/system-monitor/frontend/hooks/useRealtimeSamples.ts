import { useCallback, useState } from 'react';
import type { RealtimeSample } from '../types/realtime';
import type { Overview } from '../types/system';
import { mergeRealtimeSample } from '../utils/realtimeSamples';

export function useRealtimeSamples() {
  const [samples, setSamples] = useState<RealtimeSample[]>([]);
  const appendSample = useCallback((overview: Overview) => {
    setSamples((previous) => mergeRealtimeSample(previous, overview));
  }, []);
  return { samples, appendSample };
}
