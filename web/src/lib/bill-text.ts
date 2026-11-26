// Turns stored plain text with amendment markers into display segments.
// Markers (set by ingestion/civictexas_ingest/text.py):
//   {+added text+}   [-removed text-]

export type Segment = { kind: "text" | "add" | "del"; text: string };

export function parseAmendmentMarkup(input: string): Segment[] {
  const segments: Segment[] = [];
  const pattern = /\{\+([\s\S]*?)\+\}|\[-([\s\S]*?)-\]/g;
  let last = 0;
  for (const match of input.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > last) segments.push({ kind: "text", text: input.slice(last, index) });
    if (match[1] !== undefined) segments.push({ kind: "add", text: match[1] });
    else segments.push({ kind: "del", text: match[2] });
    last = index + match[0].length;
  }
  if (last < input.length) segments.push({ kind: "text", text: input.slice(last) });
  return segments;
}

export const MAX_RENDERED_CHARS = 60_000;

export function truncateForDisplay(text: string, max = MAX_RENDERED_CHARS): { text: string; truncated: boolean } {
  if (text.length <= max) return { text, truncated: false };
  // Cut at a line break so a marker is never split mid-line.
  const cut = text.lastIndexOf("\n", max);
  let shown = text.slice(0, cut > 0 ? cut : max);
  // Close any marker left open by the cut.
  const opensAdd = (shown.match(/\{\+/g) ?? []).length - (shown.match(/\+\}/g) ?? []).length;
  const opensDel = (shown.match(/\[-/g) ?? []).length - (shown.match(/-\]/g) ?? []).length;
  if (opensAdd > 0) shown += "+}";
  if (opensDel > 0) shown += "-]";
  return { text: shown, truncated: true };
}
