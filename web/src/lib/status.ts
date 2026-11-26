// Legislative status labels. Keys must match ingestion/civictexas_ingest/status.py
// (a test checks this).

export const STATUS_LABELS = {
  filed: "Filed",
  in_committee: "In committee",
  reported_from_committee: "Reported from committee",
  passed_origin_chamber: "Passed chamber of origin",
  in_committee_second_chamber: "In committee (second chamber)",
  reported_from_committee_second_chamber: "Reported from committee (second chamber)",
  amendments_pending: "Passed both chambers in different versions",
  passed_both_chambers: "Passed both chambers",
  sent_to_governor: "Sent to the Governor",
  signed: "Signed by the Governor",
  vetoed: "Vetoed by the Governor",
  became_law_without_signature: "Became law without signature",
  adopted: "Adopted",
  filed_with_secretary_of_state: "Filed with the Secretary of State",
  not_passed_session_ended: "Did not pass (session ended)",
  unknown: "Unknown",
} as const;

export type BillStatus = keyof typeof STATUS_LABELS;

export function statusLabel(status: string): string {
  return STATUS_LABELS[status as BillStatus] ?? STATUS_LABELS.unknown;
}

/** Plain-language note shown next to the status so it is never misread. */
export function statusExplanation(status: string, billType: string): string {
  const isResolution = /R$/.test(billType) && billType !== "HJR" && billType !== "SJR";
  switch (status) {
    case "signed":
    case "became_law_without_signature":
      return "This bill completed the legislative process. Check the effective date in the bill's history or text.";
    case "filed_with_secretary_of_state":
      return "This proposed constitutional amendment passed the Legislature. It takes effect only if approved by voters.";
    case "vetoed":
      return "The Governor vetoed this bill. It did not become law.";
    case "not_passed_session_ended":
      return "The session ended before this measure completed the legislative process. It did not become law.";
    case "sent_to_governor":
      return "Passed by the Legislature and awaiting the Governor's action. It is not law yet.";
    case "passed_both_chambers":
      return isResolution
        ? "Adopted by both chambers."
        : "Passed by the Legislature. It is not law until it completes the remaining steps.";
    case "amendments_pending":
      return "Each chamber passed a different version. Both must agree on the same text before it can proceed. It is not law.";
    case "adopted":
      return "Adopted by the chamber. Simple resolutions do not become law.";
    case "unknown":
      return "We could not determine the status from the official history. Check the official record.";
    default:
      return "This is proposed legislation. It is not law.";
  }
}

export type StatusTone = "neutral" | "progress" | "enacted" | "stopped";

export function statusTone(status: string): StatusTone {
  if (["signed", "became_law_without_signature", "filed_with_secretary_of_state", "adopted"].includes(status))
    return "enacted";
  if (["vetoed", "not_passed_session_ended"].includes(status)) return "stopped";
  if (["filed", "unknown"].includes(status)) return "neutral";
  return "progress";
}

/** Steps for the progress indicator (bills only). */
export const BILL_STEPS = [
  { key: "filed", label: "Filed" },
  { key: "origin", label: "Chamber of origin" },
  { key: "second", label: "Second chamber" },
  { key: "governor", label: "Governor" },
] as const;

export function billStepIndex(status: string): number {
  switch (status) {
    case "filed":
    case "in_committee":
    case "reported_from_committee":
      return 1;
    case "passed_origin_chamber":
    case "in_committee_second_chamber":
    case "reported_from_committee_second_chamber":
    case "amendments_pending":
      return 2;
    case "passed_both_chambers":
    case "sent_to_governor":
      return 3;
    case "signed":
    case "became_law_without_signature":
    case "vetoed":
      return 4;
    default:
      return 0;
  }
}
