import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { parseAmendmentMarkup, truncateForDisplay } from "./bill-text";
import { isStale } from "./format";
import { billsHref, parseBillFilters, parseBillNumber, parseBillSlug } from "./search-params";
import { STATUS_LABELS, billStepIndex, statusExplanation } from "./status";

describe("bill number search", () => {
  it.each([
    ["HB 101", { billType: "HB", number: 101 }],
    ["hb101", { billType: "HB", number: 101 }],
    ["H.B. 2", { billType: "HB", number: 2 }],
    ["SJR 1", { billType: "SJR", number: 1 }],
  ])("parses %s", (input, expected) => {
    expect(parseBillNumber(input)).toEqual(expected);
  });

  it("treats other text as keywords", () => {
    expect(parseBillNumber("school finance")).toBeNull();
    expect(parseBillNumber("HB")).toBeNull();
  });

  it("parses URL slugs", () => {
    expect(parseBillSlug("HB2")).toEqual({ billType: "HB", number: 2 });
    expect(parseBillSlug("hjr-1")).toEqual({ billType: "HJR", number: 1 });
    expect(parseBillSlug("XX9")).toBeNull();
  });
});

describe("filters", () => {
  it("accepts valid values and drops invalid ones", () => {
    const f = parseBillFilters({ q: " HB 2 ", session: "89R", chamber: "senate", status: "signed", sort: "number", page: "3" });
    expect(f).toMatchObject({ q: "HB 2", session: "89R", chamber: "senate", status: "signed", sort: "number", page: 3 });
    expect(f.billNumber).toEqual({ billType: "HB", number: 2 });

    const bad = parseBillFilters({ session: "'; drop table bills", chamber: "both", status: "law", sort: "x", page: "-1" });
    expect(bad).toMatchObject({ session: null, chamber: null, status: null, sort: "recent", page: 1 });
  });

  it("builds clean URLs", () => {
    expect(billsHref({ q: "tax", session: null, page: 1 })).toBe("/bills?q=tax");
    expect(billsHref({ q: "", page: 2 })).toBe("/bills?page=2");
    expect(billsHref({})).toBe("/bills");
  });
});

describe("amendment markup", () => {
  it("splits added and removed text", () => {
    expect(parseAmendmentMarkup("A person [-may-]{+shall+} file.")).toEqual([
      { kind: "text", text: "A person " },
      { kind: "del", text: "may" },
      { kind: "add", text: "shall" },
      { kind: "text", text: " file." },
    ]);
  });

  it("never splits a marker when truncating", () => {
    const text = "line one\n{+added text that\ncontinues here+}\nmore";
    const { text: shown, truncated } = truncateForDisplay(text, 30);
    expect(truncated).toBe(true);
    expect(parseAmendmentMarkup(shown).some((s) => s.kind === "add")).toBe(true);
    expect(shown).not.toMatch(/\{\+[^+]*$/);
  });
});

describe("status", () => {
  it("has the same statuses as the ingestion pipeline and database", () => {
    const python = readFileSync(resolve(__dirname, "../../../ingestion/civictexas_ingest/status.py"), "utf8");
    const pyKeys = [...python.matchAll(/^\s+"([a-z_]+)": "[^"]+",$/gm)].map((m) => m[1]);
    expect(new Set(Object.keys(STATUS_LABELS))).toEqual(new Set(pyKeys));

    const sql = readFileSync(resolve(__dirname, "../../../supabase/migrations/20261126000001_initial_schema.sql"), "utf8");
    const check = sql.slice(sql.indexOf("status in ("), sql.indexOf("'unknown'))") + 9);
    const sqlKeys = [...check.matchAll(/'([a-z_]+)'/g)].map((m) => m[1]);
    expect(new Set(sqlKeys)).toEqual(new Set(Object.keys(STATUS_LABELS)));
  });

  it("never calls unenacted legislation law", () => {
    for (const status of Object.keys(STATUS_LABELS)) {
      const text = statusExplanation(status, "HB");
      if (!["signed", "became_law_without_signature"].includes(status)) {
        expect(text).not.toMatch(/\b(is|became) (now )?law\b/i);
      }
    }
    expect(statusExplanation("amendments_pending", "HB")).toMatch(/not law/);
    expect(statusExplanation("sent_to_governor", "SB")).toMatch(/not law yet/);
  });

  it("maps statuses to progress steps", () => {
    expect(billStepIndex("filed")).toBe(1);
    expect(billStepIndex("amendments_pending")).toBe(2);
    expect(billStepIndex("signed")).toBe(4);
    expect(billStepIndex("not_passed_session_ended")).toBe(0);
  });
});

describe("freshness", () => {
  it("flags data older than the threshold", () => {
    const now = new Date("2026-11-26T12:00:00Z");
    expect(isStale(new Date("2026-11-26T00:00:00Z"), now, 48)).toBe(false);
    expect(isStale(new Date("2026-11-20T00:00:00Z"), now, 48)).toBe(true);
    expect(isStale(null, now, 48)).toBe(true);
  });
});
