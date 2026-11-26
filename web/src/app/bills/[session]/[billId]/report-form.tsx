"use client";

import { useActionState } from "react";
import { Button } from "@/components/ui/button";
import { submitReport, type ReportState } from "./actions";

export function ReportForm({ targetType, targetId }: { targetType: "ai_summary" | "bill_data"; targetId: string }) {
  const [state, action, pending] = useActionState<ReportState, FormData>(submitReport, null);
  const id = `report-${targetType}`;
  return (
    <details className="rounded border border-rule bg-card p-4">
      <summary className="cursor-pointer font-semibold">Report a problem with this information</summary>
      <form action={action} className="mt-4 space-y-3">
        <input type="hidden" name="target_type" value={targetType} />
        <input type="hidden" name="target_id" value={targetId} />
        <div className="hidden" aria-hidden="true">
          <label htmlFor={`${id}-website`}>Leave this empty</label>
          <input id={`${id}-website`} name="website" tabIndex={-1} autoComplete="off" />
        </div>
        <div>
          <label htmlFor={`${id}-reason`} className="mb-1 block text-sm font-semibold">
            What kind of problem?
          </label>
          <select
            id={`${id}-reason`}
            name="reason"
            required
            defaultValue=""
            className="h-10 w-full max-w-sm rounded border border-input bg-background px-2 text-sm"
          >
            <option value="" disabled>
              Choose one
            </option>
            <option value="inaccurate">Inaccurate</option>
            <option value="missing_information">Missing information</option>
            <option value="misleading">Misleading</option>
            <option value="biased">Not neutral</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div>
          <label htmlFor={`${id}-details`} className="mb-1 block text-sm font-semibold">
            Details
          </label>
          <textarea
            id={`${id}-details`}
            name="details"
            required
            minLength={10}
            maxLength={2000}
            rows={3}
            aria-describedby={`${id}-hint`}
            className="w-full rounded border border-input bg-background p-2 text-sm"
          />
          <p id={`${id}-hint`} className="mt-1 text-xs text-ink-soft">
            Please don&apos;t include personal information. No account needed.
          </p>
        </div>
        <Button type="submit" disabled={pending}>
          {pending ? "Sending…" : "Send report"}
        </Button>
        <p role="status" aria-live="polite" className={state?.ok ? "text-success font-medium" : "text-destructive font-medium"}>
          {state?.message}
        </p>
      </form>
    </details>
  );
}
