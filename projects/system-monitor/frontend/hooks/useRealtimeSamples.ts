import { useCallback, useState } from 'react';
import type { RealtimeSample } from '../utils/realtimeSamples';
import type { Overview } from '../api/overview';
import { mergeRealtimeSample } from '../utils/realtimeSamples';

export function useRealtimeSamples() {
  const [samples, setSamples] = useState<RealtimeSample[]>([]);
  const appendSample = useCallback((overview: Overview) => {
    setSamples((previous) => mergeRealtimeSample(previous, overview));
  }, []);
  return { samples, appendSample };
}
