import type { FeatureHealth, FeatureStatus } from '../../api/health';

export const STATUS_LABELS: Record<FeatureStatus, string> = {
  healthy: 'Healthy', issues: 'Issue', unavailable: 'Unavailable', unknown: 'Unknown',
};

/** 只彙整實際回報；請求失敗時不得以全零或示意結果取代。 */
export function summarizeFeatures(features: FeatureHealth[]) {
  return features.reduce((counts, feature) => {
    counts[feature.status] += 1;
    return counts;
  }, { healthy: 0, issues: 0, unavailable: 0, unknown: 0 });
}
