// Dates are shown in Texas (Central) time, where the Legislature records them.
const TZ = "America/Chicago";

export function formatDate(value: Date | string | null | undefined): string {
  if (!value) return "Unknown";
  const date = typeof value === "string" ? new Date(`${value}T12:00:00Z`) : value;
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeZone: "UTC" }).format(date);
}

export function formatDateTime(value: Date | string | null | undefined): string {
  if (!value) return "Unknown";
  const date = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: TZ,
    timeZoneName: "short",
  }).format(date);
}

export function staleAfterHours(): number {
  const value = Number(process.env.NEXT_PUBLIC_STALE_AFTER_HOURS);
  return Number.isFinite(value) && value > 0 ? value : 48;
}

export function isStale(lastSynced: Date | string | null | undefined, now = new Date(), hours = staleAfterHours()) {
  if (!lastSynced) return true;
  const synced = typeof lastSynced === "string" ? new Date(lastSynced) : lastSynced;
  return now.getTime() - synced.getTime() > hours * 3600 * 1000;
}

export function relativeAge(value: Date | string, now = new Date()): string {
  const date = typeof value === "string" ? new Date(value) : value;
  const minutes = Math.round((now.getTime() - date.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} days ago`;
}
