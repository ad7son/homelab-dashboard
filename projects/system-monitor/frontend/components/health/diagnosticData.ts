/** 直接以原始本文排版，不依賴快照後來才新增的欄位，舊快照也能完整顯示。 */
export function formatDiagnosticResponse(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
