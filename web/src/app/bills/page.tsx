import type { Metadata } from "next";
import Link from "next/link";
import { BillRow } from "@/components/bill-row";
import { DataUnavailable, ProofOfConceptNotice } from "@/components/notices";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getFreshness, getSessions, getTopics, searchBills } from "@/lib/bills";
import { DataUnavailableError } from "@/lib/db";
import { formatDateTime } from "@/lib/format";
import { PAGE_SIZE, billsHref, parseBillFilters } from "@/lib/search-params";
import { STATUS_LABELS } from "@/lib/status";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Bills" };

const selectClass =
  "h-10 w-full rounded border border-input bg-card px-2 text-sm text-foreground focus-visible:outline-3 focus-visible:outline-ring";

export default async function BillsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const filters = parseBillFilters(await searchParams);

  let data;
  try {
    const [sessions, topics, results, freshness] = await Promise.all([
      getSessions(),
      getTopics(filters.session),
      searchBills(filters),
      getFreshness(),
    ]);
    data = { sessions, topics, results, freshness };
  } catch (error) {
    if (error instanceof DataUnavailableError) {
      return (
        <div className="space-y-6">
          <h1 className="text-3xl sm:text-4xl">Bills</h1>
          <DataUnavailable />
        </div>
      );
    }
    throw error;
  }

  const { sessions, topics, results, freshness } = data;
  const totalPages = Math.max(1, Math.ceil(results.total / PAGE_SIZE));
  const base = {
    q: filters.q,
    session: filters.session,
    chamber: filters.chamber,
    status: filters.status,
    topic: filters.topic,
    sort: filters.sort === "recent" ? null : filters.sort,
  };
  const hasFilters = Boolean(filters.q || filters.session || filters.chamber || filters.status || filters.topic);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <h1 className="text-3xl sm:text-4xl">Bills</h1>
        <p className="max-w-2xl text-lg text-ink-soft">
          Search Texas legislation by bill number or keyword. Every record links back to the official source.
        </p>
        <ProofOfConceptNotice />
      </header>

      <form method="get" action="/bills" className="space-y-4 border-y border-foreground py-5" role="search">
        <div>
          <label htmlFor="q" className="mb-1 block text-sm font-semibold">
            Bill number or keyword
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              id="q"
              name="q"
              type="search"
              defaultValue={filters.q}
              placeholder="e.g. HB 2, SB 31, school finance"
              className="h-10 bg-card text-base"
            />
            <Button type="submit" className="h-10 px-5">
              Search
            </Button>
          </div>
        </div>
        <fieldset className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <legend className="sr-only">Filters</legend>
          <div>
            <label htmlFor="session" className="mb-1 block text-sm font-semibold">
              Session
            </label>
            <select id="session" name="session" defaultValue={filters.session ?? ""} className={selectClass}>
              <option value="">All sessions</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.bill_count})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="chamber" className="mb-1 block text-sm font-semibold">
              Chamber
            </label>
            <select id="chamber" name="chamber" defaultValue={filters.chamber ?? ""} className={selectClass}>
              <option value="">House and Senate</option>
              <option value="house">House</option>
              <option value="senate">Senate</option>
            </select>
          </div>
          <div>
            <label htmlFor="status" className="mb-1 block text-sm font-semibold">
              Status
            </label>
            <select id="status" name="status" defaultValue={filters.status ?? ""} className={selectClass}>
              <option value="">Any status</option>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="topic" className="mb-1 block text-sm font-semibold">
              Topic
            </label>
            <select id="topic" name="topic" defaultValue={filters.topic ?? ""} className={selectClass}>
              <option value="">Any topic</option>
              {topics.map((t) => (
                <option key={t} value={t}>
                  {t.replace(/\s*\([A-Z]\d+\)$/, "")}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="sort" className="mb-1 block text-sm font-semibold">
              Sort by
            </label>
            <select id="sort" name="sort" defaultValue={filters.sort} className={selectClass}>
              <option value="recent">Recently updated</option>
              <option value="number">Bill number</option>
            </select>
          </div>
        </fieldset>
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <Button type="submit" variant="outline" className="h-9">
            Apply filters
          </Button>
          {hasFilters && (
            <Link href="/bills" className="underline">
              Clear all
            </Link>
          )}
          <p className="text-ink-soft">Topics are the Texas Legislative Council&apos;s subject index.</p>
        </div>
      </form>

      <section aria-labelledby="results-heading" className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="results-heading" className="text-2xl" aria-live="polite">
            {results.total === 0 ? "No bills found" : `${results.total} bill${results.total === 1 ? "" : "s"}`}
          </h2>
          <p className="text-sm text-ink-soft">
            {freshness
              .filter((f) => f.last_successful_at)
              .map((f) => `${f.session_id} last synced ${formatDateTime(f.last_successful_at)}`)
              .join(" · ") || "Not synchronized yet"}
          </p>
        </div>

        {results.total === 0 ? (
          <div className="space-y-2 rounded border border-rule bg-card p-5">
            <p>
              {hasFilters
                ? "No bills in this sample match your search."
                : "No bills have been loaded yet. Run the ingestion job to load the sample."}
            </p>
            <p className="text-sm text-ink-soft">
              This proof of concept holds only a sample of bills. To look up any bill, use{" "}
              <a href="https://capitol.texas.gov/" className="text-sienna underline">
                Texas Legislature Online
              </a>
              .
            </p>
          </div>
        ) : (
          <ol className="list-none">
            {results.bills.map((bill) => (
              <BillRow key={bill.id} bill={bill} />
            ))}
          </ol>
        )}

        {totalPages > 1 && (
          <nav aria-label="Pagination" className="flex items-center justify-between pt-2 text-sm">
            {filters.page > 1 ? (
              <Link href={billsHref({ ...base, page: filters.page - 1 })} className="underline">
                Previous page
              </Link>
            ) : (
              <span />
            )}
            <span>
              Page {filters.page} of {totalPages}
            </span>
            {filters.page < totalPages ? (
              <Link href={billsHref({ ...base, page: filters.page + 1 })} className="underline">
                Next page
              </Link>
            ) : (
              <span />
            )}
          </nav>
        )}
      </section>
    </div>
  );
}
