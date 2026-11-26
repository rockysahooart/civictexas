import { parseAmendmentMarkup, truncateForDisplay } from "@/lib/bill-text";

export function BillTextLegend() {
  return (
    <p className="text-sm text-ink-soft">
      In Texas bills, <ins className="bill-add">underlined text</ins> is language that would be added to existing law,
      and <del className="bill-del">struck-through text</del> is language that would be removed. Screen readers announce
      these as inserted and deleted text.
    </p>
  );
}

export function BillText({ text, officialUrl }: { text: string; officialUrl: string | null }) {
  const { text: shown, truncated } = truncateForDisplay(text);
  const segments = parseAmendmentMarkup(shown);
  return (
    <div>
      <div className="max-h-[70vh] overflow-auto rounded border border-rule bg-card p-4 sm:p-6" tabIndex={0} aria-label="Bill text">
        <div className="font-mono text-[0.85rem] leading-relaxed whitespace-pre-wrap break-words">
          {segments.map((segment, i) =>
            segment.kind === "add" ? (
              <ins key={i} className="bill-add">
                {segment.text}
              </ins>
            ) : segment.kind === "del" ? (
              <del key={i} className="bill-del">
                {segment.text}
              </del>
            ) : (
              <span key={i}>{segment.text}</span>
            ),
          )}
        </div>
      </div>
      {truncated && (
        <p className="mt-2 text-sm">
          This version is long, so only the beginning is shown here.{" "}
          {officialUrl && (
            <a href={officialUrl} className="text-sienna underline">
              Read the full official text
            </a>
          )}
        </p>
      )}
    </div>
  );
}
