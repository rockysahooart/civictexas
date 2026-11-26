import Link from "next/link";
import { BillRow } from "@/components/bill-row";
import { DataUnavailable, ProofOfConceptNotice } from "@/components/notices";
import { getCounts, getFreshness, getRecentlyUpdated, getSessions } from "@/lib/bills";
import { DataUnavailableError } from "@/lib/db";
import { formatDateTime, isStale } from "@/lib/format";

export const dynamic = "force-dynamic";

async function loadOverview() {
  try {
    const [sessions, freshness, recent, counts] = await Promise.all([
      getSessions(),
      getFreshness(),
      getRecentlyUpdated(5),
      getCounts(),
    ]);
    return { sessions, freshness, recent, counts };
  } catch (error) {
    if (error instanceof DataUnavailableError) return null;
    throw error;
  }
}

export default async function Home() {
  const data = await loadOverview();

  return (
    <div className="space-y-12">
      <section className="space-y-5">
        <h1 className="max-w-3xl text-4xl sm:text-6xl">
          Know what&apos;s being passed. <span className="block text-sienna">Understand what it means.</span>
        </h1>
        <p className="max-w-2xl text-lg text-ink-soft sm:text-xl">
          Civic Texas brings official Texas legislative records into one readable place: bill status, history, sponsors
          and the full text of every version, each linked to its official source.
        </p>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/bills"
            className="inline-flex h-11 items-center rounded bg-foreground px-5 font-semibold text-background hover:bg-sienna"
          >
            Browse bills
          </Link>
          <Link href="/methodology" className="inline-flex h-11 items-center font-semibold underline">
            How we source data
          </Link>
        </div>
        <ProofOfConceptNotice />
      </section>

      {!data ? (
        <DataUnavailable />
      ) : (
        <>
          <section aria-labelledby="freshness-heading" className="space-y-4">
            <h2 id="freshness-heading" className="border-b border-foreground pb-2 text-2xl">
              Data freshness
            </h2>
            <p className="max-w-2xl text-ink-soft">
              Records are copied from the Texas Legislative Council&apos;s official bulk files on a schedule. This is
              when each session was last checked. It is not live.
            </p>
            <table className="w-full max-w-2xl border-collapse text-sm">
              <thead>
                <tr className="border-b border-rule text-left">
                  <th scope="col" className="py-2 pr-4">
                    Session
                  </th>
                  <th scope="col" className="py-2 pr-4">
                    Bills loaded
                  </th>
                  <th scope="col" className="py-2">
                    Last successful sync
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.sessions.map((s) => {
                  const f = data.freshness.find((x) => x.session_id === s.id);
                  const stale = isStale(f?.last_successful_at ?? null);
                  return (
                    <tr key={s.id} className="border-b border-rule/60">
                      <th scope="row" className="py-2 pr-4 text-left font-normal">
                        {s.name}
                      </th>
                      <td className="py-2 pr-4">{s.bill_count}</td>
                      <td className="py-2">
                        {f?.last_successful_at ? formatDateTime(f.last_successful_at) : "Not yet synchronized"}
                        {f?.last_successful_at && stale && <span className="ml-2 font-semibold text-warning-ink">(stale)</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="text-sm text-ink-soft">
              {data.counts.bills} bills, {data.counts.actions} official actions and {data.counts.documents} official
              documents stored.
            </p>
          </section>

          <section aria-labelledby="recent-heading" className="space-y-4">
            <h2 id="recent-heading" className="border-b border-foreground pb-2 text-2xl">
              Most recent activity
            </h2>
            {data.recent.length === 0 ? (
              <p>No bills have been loaded yet.</p>
            ) : (
              <ol className="list-none">
                {data.recent.map((bill) => (
                  <BillRow key={bill.id} bill={bill} />
                ))}
              </ol>
            )}
          </section>
        </>
      )}

      <section aria-labelledby="principles-heading" className="space-y-4">
        <h2 id="principles-heading" className="border-b border-foreground pb-2 text-2xl">
          How this site works
        </h2>
        <dl className="grid gap-6 sm:grid-cols-3">
          <div>
            <dt className="font-serif text-lg font-semibold">Official records first</dt>
            <dd className="mt-1 text-ink-soft">Every fact comes from the Legislature&apos;s own published records.</dd>
          </div>
          <div>
            <dt className="font-serif text-lg font-semibold">Facts apart from explanations</dt>
            <dd className="mt-1 text-ink-soft">
              AI explanations and community views are labeled and kept separate from official information.
            </dd>
          </div>
          <div>
            <dt className="font-serif text-lg font-semibold">No account needed</dt>
            <dd className="mt-1 text-ink-soft">Anyone can read every record and report an error.</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}
