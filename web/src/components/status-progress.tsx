import { BILL_STEPS, billStepIndex } from "@/lib/status";
import { cn } from "@/lib/utils";

/** Where a bill is in the process. Only shown for bills and joint/concurrent resolutions. */
export function StatusProgress({ status }: { status: string }) {
  const current = billStepIndex(status);
  const stopped = status === "vetoed" || status === "not_passed_session_ended";
  if (current === 0) return null;
  return (
    <ol className="mt-4 grid grid-cols-4 gap-1" aria-label="Legislative progress">
      {BILL_STEPS.map((step, index) => {
        const position = index + 1;
        const reached = position <= current;
        const isCurrent = position === current;
        return (
          <li key={step.key} className="min-w-0">
            <div
              className={cn(
                "h-1.5 rounded-full",
                reached ? (stopped && isCurrent ? "bg-ink-soft" : "bg-sienna") : "bg-rule",
              )}
              aria-hidden="true"
            />
            <p
              className={cn("mt-1.5 text-xs leading-tight", reached ? "text-foreground font-medium" : "text-ink-soft")}
            >
              {step.label}
              <span className="sr-only">{isCurrent ? " (current stage)" : reached ? " (reached)" : " (not reached)"}</span>
            </p>
          </li>
        );
      })}
    </ol>
  );
}
