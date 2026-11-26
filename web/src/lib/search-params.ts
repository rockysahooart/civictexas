// Parsing and validation for /bills query parameters. Pure functions, no I/O.
import { STATUS_LABELS } from "./status";

export const BILL_TYPES = ["HB", "SB", "HJR", "SJR", "HCR", "SCR", "HR", "SR"] as const;
export const SORTS = ["recent", "number"] as const;
export const PAGE_SIZE = 25;

export type BillFilters = {
  q: string;
  billNumber: { billType: string; number: number } | null;
  session: string | null;
  chamber: "house" | "senate" | null;
  status: string | null;
  topic: string | null;
  sort: (typeof SORTS)[number];
  page: number;
};

type Raw = Record<string, string | string[] | undefined>;

function one(raw: Raw, key: string): string {
  const value = raw[key];
  return (Array.isArray(value) ? value[0] : value ?? "").trim();
}

/** Recognizes "HB 101", "hb101", "H.B. 101", "SJR 1". */
export function parseBillNumber(text: string): { billType: string; number: number } | null {
  const compact = text.toUpperCase().replace(/\./g, "").replace(/\s+/g, "");
  const match = compact.match(/^(HB|SB|HJR|SJR|HCR|SCR|HR|SR)(\d{1,5})$/);
  if (!match) return null;
  return { billType: match[1], number: Number(match[2]) };
}

export function parseBillFilters(raw: Raw): BillFilters {
  const q = one(raw, "q").slice(0, 200);
  const session = one(raw, "session");
  const chamber = one(raw, "chamber");
  const status = one(raw, "status");
  const topic = one(raw, "topic").slice(0, 200);
  const sort = one(raw, "sort");
  const page = Number.parseInt(one(raw, "page"), 10);
  return {
    q,
    billNumber: parseBillNumber(q),
    session: /^\d{2,3}(R|\d)$/.test(session) ? session : null,
    chamber: chamber === "house" || chamber === "senate" ? chamber : null,
    status: status in STATUS_LABELS ? status : null,
    topic: topic || null,
    sort: (SORTS as readonly string[]).includes(sort) ? (sort as BillFilters["sort"]) : "recent",
    page: Number.isFinite(page) && page > 0 && page < 10_000 ? page : 1,
  };
}

/** Build a /bills URL, dropping empty values. */
export function billsHref(filters: Partial<Record<string, string | number | null>>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== null && value !== undefined && value !== "" && !(key === "page" && value === 1)) {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `/bills?${query}` : "/bills";
}

/** "HB101" / "hb-101" in a URL path segment -> parts. */
export function parseBillSlug(slug: string): { billType: string; number: number } | null {
  return parseBillNumber(decodeURIComponent(slug).replace(/-/g, ""));
}

export function billSlug(billType: string, number: number): string {
  return `${billType}${number}`;
}
