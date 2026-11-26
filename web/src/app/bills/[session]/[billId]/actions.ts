"use server";

import { asPublic } from "@/lib/db";

export type ReportState = { ok: boolean; message: string } | null;

const REASONS = ["inaccurate", "misleading", "missing_information", "biased", "other"] as const;
const TARGETS = ["ai_summary", "bill_data"] as const;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Anyone can report a problem without an account. Stored with RLS as `anon`. */
export async function submitReport(_prev: ReportState, form: FormData): Promise<ReportState> {
  const targetType = String(form.get("target_type") ?? "");
  const targetId = String(form.get("target_id") ?? "");
  const reason = String(form.get("reason") ?? "");
  const details = String(form.get("details") ?? "").trim().slice(0, 2000);
  if (String(form.get("website") ?? "")) return { ok: true, message: "Thank you. Your report was received." }; // spam trap

  if (!(TARGETS as readonly string[]).includes(targetType) || !UUID.test(targetId)) {
    return { ok: false, message: "This report could not be linked to a record. Please reload the page and try again." };
  }
  if (!(REASONS as readonly string[]).includes(reason)) {
    return { ok: false, message: "Please choose what kind of problem you found." };
  }
  if (details.length < 10) {
    return { ok: false, message: "Please describe the problem in a sentence or two so we can check it." };
  }
  try {
    await asPublic(
      (tx) => tx`
        insert into content_reports (target_type, target_id, reason, details)
        values (${targetType}, ${targetId}, ${reason}, ${details})`,
    );
    return { ok: true, message: "Thank you. Your report was received and will be reviewed." };
  } catch {
    return { ok: false, message: "Your report could not be saved. Please try again later." };
  }
}
