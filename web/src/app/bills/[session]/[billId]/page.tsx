import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BillText, BillTextLegend } from "@/components/bill-text";
import { DataUnavailable, StaleNotice } from "@/components/notices";
import { StatusBadge } from "@/components/status-badge";
import { StatusProgress } from "@/components/status-progress";
import { SummaryView } from "@/components/summary-view";
import { getBill, getDocumentText, type BillPage } from "@/lib/bills";
import { DataUnavailableError } from "@/lib/db";
import { formatDate, formatDateTime } from "@/lib/format";
import { parseBillSlug } from "@/lib/search-params";
import { statusExplanation } from "@/lib/status";
import { ReportForm } from "./report-form";

export const dynamic = "force-dynamic";

type Params = { session: string; billId: string };

const ROLE_LABELS: Record<string, string> = {
  author: "Authors",
  coauthor: "Coauthors",
  sponsor: "Sponsors",
  cosponsor: "Cosponsors",
};
const ACTOR_LABELS: Record<string, string> = { house: "House", senate: "Senate", executive: "Governor", other: "" };
const VISIBLE_ACTIONS = 12;

async function load(params: Params): Promise<BillPage | null | "unavailable"> {
  const parsed = parseBillSlug(params.billId);
  if (!parsed || !/^\d{2,3}(R|\d)$/.test(params.session)) return null;
  try {
    return await getBill(params.session, parsed.billType, parsed.number);
  } catch (error) {
    if (error instanceof DataUnavailableError) return "unavailable";
    throw error;
  }
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const p = await params;
  const parsed = parseBillSlug(p.billId);
  return { title: parsed ? `${parsed.billType} ${parsed.number} (${p.session})` : "Bill" };
}

export default async function BillDetailPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<{ version?: string }>;
}) {
  const [p, sp] = await Promise.all([params, searchParams]);
  const data = await load(p);
  if (data === "unavailable") return <DataUnavailable />;
  if (!data) notFound();

  const { bill, sponsors, actions, committees, floorVotes, versions, fiscalNotes, summaries } = data;
  const selected =
    versions.find((v) => v.version_code === sp.version?.toUpperCase()) ?? versions[versions.length - 1] ?? null;
  const text = selected?.document_id ? await getDocumentText(selected.document_id) : null;
  const sponsorGroups = Object.keys(ROLE_LABELS)
    .map((role) => ({ role, names: sponsors.filter((s) => s.role === role).map((s) => s.display_name) }))
    .filter((g) => g.names.length > 0);
  const isBillLike = !["HR", "SR"].includes(bill.bill_type);
  const lastAction = actions[actions.length - 1];

  return (
    <article className="space-y-10">
      <nav aria-label="Breadcrumb" className="text-sm">
        <Link href="/bills" className="underline">
          Bills
        </Link>{" "}
        <span aria-hidden="true">/</span> {bill.session_name}
      </nav>

      {/* ---- Official facts ---- */}
      <header className="space-y-4">
        <p className="text-sm font-semibold tracking-wider text-ink-soft uppercase">{bill.session_name}</p>
        <h1 className="text-4xl sm:text-5xl">{bill.identifier}</h1>
        <p className="max-w-3xl font-serif text-xl leading-snug sm:text-2xl">{bill.caption}</p>
        <p className="text-sm text-ink-soft">
          Official caption{bill.caption_version ? `, ${bill.caption_version} version` : ""}.
        </p>
        <div className="max-w-3xl space-y-2 border-l-4 border-sienna bg-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm font-semibold">Current status</span>
            <StatusBadge status={bill.status} className="text-sm" />
            {bill.status_date && <span className="text-sm text-ink-soft">as of {formatDate(bill.status_date)}</span>}
          </div>
          <p className="text-sm">{statusExplanation(bill.status, bill.bill_type)}</p>
          {isBillLike && <StatusProgress status={bill.status} />}
          {lastAction && (
            <p className="text-sm text-ink-soft">
              Last official action: {lastAction.description} ({formatDate(lastAction.action_date)})
            </p>
          )}
        </div>
        <StaleNotice lastSynced={bill.last_synced_at} />
      </header>

      <section aria-labelledby="people" className="space-y-3">
        <h2 id="people" className="border-b border-foreground pb-2 text-2xl">
          Sponsors and details
        </h2>
        <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-[12rem_1fr]">
          {sponsorGroups.map((g) => (
            <div key={g.role} className="contents">
              <dt className="font-semibold">{ROLE_LABELS[g.role]}</dt>
              <dd>
                {g.names.length > 8 ? (
                  <details>
                    <summary className="cursor-pointer">
                      {g.names.slice(0, 5).join(", ")} and {g.names.length - 5} more
                    </summary>
                    <p className="mt-1">{g.names.join(", ")}</p>
                  </details>
                ) : (
                  g.names.join(", ")
                )}
              </dd>
            </div>
          ))}
          {committees.length > 0 && (
            <>
              <dt className="font-semibold">Committees</dt>
              <dd>
                <ul className="space-y-1">
                  {committees.map((c) => (
                    <li key={`${c.chamber}-${c.name}`}>
                      {c.chamber === "house" ? "House" : "Senate"} {c.name}
                      {c.status ? ` — ${c.status}` : ""}
                      {c.yeas !== null && (
                        <span className="text-ink-soft">
                          {" "}
                          (committee vote: {c.yeas} ayes, {c.nays} nays, {c.present_not_voting} present not voting,{" "}
                          {c.absent} absent)
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </dd>
            </>
          )}
          {floorVotes.length > 0 && (
            <>
              <dt className="font-semibold">Record votes</dt>
              <dd>
                <Collapsible items={floorVotes} visible={3} noun="record votes">
                  {(v) => (
                    <li key={`${v.chamber}-${v.source_reference}`}>
                      {v.chamber === "house" ? "House" : "Senate"} {v.source_reference}, {formatDate(v.vote_date)}
                      {v.motion ? ` (${v.motion})` : ""}
                    </li>
                  )}
                </Collapsible>
                <p className="mt-1 text-sm text-ink-soft">
                  Member-by-member votes are published in the House and Senate journals and are not shown here yet.
                </p>
              </dd>
            </>
          )}
          {bill.subjects.length > 0 && (
            <>
              <dt className="font-semibold">Subjects</dt>
              <dd>
                <Collapsible items={bill.subjects} visible={10} noun="subjects" listClassName="flex flex-wrap gap-2">
                  {(s) => (
                    <li key={s}>
                      <Link
                        href={`/bills?topic=${encodeURIComponent(s)}`}
                        className="inline-block rounded-sm border border-rule bg-card px-2 py-0.5 text-sm hover:border-sienna"
                      >
                        {s.replace(/\s*\([A-Z]\d+\)$/, "")}
                      </Link>
                    </li>
                  )}
                </Collapsible>
              </dd>
            </>
          )}
          {bill.companions && (
            <>
              <dt className="font-semibold">Companion bills</dt>
              <dd>{bill.companions}</dd>
            </>
          )}
        </dl>
      </section>

      <section aria-labelledby="history" className="space-y-3">
        <h2 id="history" className="border-b border-foreground pb-2 text-2xl">
          Legislative history
        </h2>
        <p className="text-sm text-ink-soft">{actions.length} official actions, newest first.</p>
        <ActionsTable actions={[...actions].reverse().slice(0, VISIBLE_ACTIONS)} />
        {actions.length > VISIBLE_ACTIONS && (
          <details>
            <summary className="cursor-pointer font-medium">Show {actions.length - VISIBLE_ACTIONS} earlier actions</summary>
            <ActionsTable actions={[...actions].reverse().slice(VISIBLE_ACTIONS)} />
          </details>
        )}
      </section>

      <section aria-labelledby="text" className="space-y-4">
        <h2 id="text" className="border-b border-foreground pb-2 text-2xl">
          Bill text
        </h2>
        {versions.length === 0 ? (
          <p>No text has been published for this measure yet.</p>
        ) : (
          <>
            <nav aria-label="Bill versions">
              <ul className="flex flex-wrap gap-2">
                {versions.map((v) => {
                  const active = v.version_code === selected?.version_code;
                  return (
                    <li key={v.id}>
                      <Link
                        href={`?version=${v.version_code}#text`}
                        aria-current={active ? "page" : undefined}
                        className={
                          active
                            ? "inline-block rounded-sm border border-foreground bg-foreground px-3 py-1 text-sm text-background"
                            : "inline-block rounded-sm border border-rule bg-card px-3 py-1 text-sm hover:border-foreground"
                        }
                      >
                        {v.description}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>
            {selected && (
              <div className="space-y-3">
                <p className="text-sm">
                  Showing the <strong>{selected.description}</strong> version.{" "}
                  {selected.html_url && (
                    <a href={selected.html_url} className="text-sienna underline">
                      Official HTML
                    </a>
                  )}
                  {selected.pdf_url && (
                    <>
                      {" · "}
                      <a href={selected.pdf_url} className="text-sienna underline">
                        Official PDF
                      </a>
                    </>
                  )}
                  {selected.retrieved_at && (
                    <span className="text-ink-soft"> · Retrieved {formatDateTime(selected.retrieved_at)}</span>
                  )}
                  {selected.snapshot_count > 1 && (
                    <span className="text-ink-soft">
                      {" "}
                      · The official text of this version has changed since we first stored it ({selected.snapshot_count}{" "}
                      copies kept).
                    </span>
                  )}
                </p>
                <BillTextLegend />
                {text ? (
                  <BillText text={text} officialUrl={selected.html_url} />
                ) : (
                  <p className="rounded border border-rule bg-card p-4">
                    We haven&apos;t stored the text of this version yet. Read it on the official site using the links
                    above.
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </section>

      <section aria-labelledby="fiscal" className="space-y-3">
        <h2 id="fiscal" className="border-b border-foreground pb-2 text-2xl">
          Fiscal notes
        </h2>
        {fiscalNotes.length === 0 ? (
          <p>No fiscal note has been published for this measure.</p>
        ) : (
          <>
            <p className="text-sm text-ink-soft">
              Fiscal notes are prepared by the Legislative Budget Board and estimate a bill&apos;s cost to the state and
              local governments.
            </p>
            <ul className="space-y-1">
              {fiscalNotes.map((f) => (
                <li key={f.version_code}>
                  {f.description}:{" "}
                  {f.html_url && (
                    <a href={f.html_url} className="text-sienna underline">
                      HTML
                    </a>
                  )}
                  {f.pdf_url && (
                    <>
                      {" · "}
                      <a href={f.pdf_url} className="text-sienna underline">
                        PDF
                      </a>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      {/* ---- AI explanations: visually and structurally separate from official facts ---- */}
      <section aria-labelledby="summary" className="space-y-3 rounded border-2 border-dashed border-rule p-5">
        <h2 id="summary" className="text-2xl">
          Plain-language summary
        </h2>
        {summaries.length === 0 ? (
          <p>
            No reviewed summary is available for this bill yet. Summaries are generated from the official text and
            published only after a person has checked them against it. See the{" "}
            <Link href="/methodology#summaries" className="text-sienna underline">
              methodology
            </Link>
            .
          </p>
        ) : (
          summaries.map((s) => (
            <div key={s.id} className="space-y-3">
              <SummaryView summary={s} />
              <ReportForm targetType="ai_summary" targetId={s.id} />
            </div>
          ))
        )}
      </section>

      <section aria-labelledby="sources" className="space-y-3">
        <h2 id="sources" className="border-b border-foreground pb-2 text-2xl">
          Sources and freshness
        </h2>
        <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-[14rem_1fr]">
          <dt className="font-semibold">Official bill page</dt>
          <dd>
            <a href={bill.official_url} className="text-sienna underline break-all">
              Texas Legislature Online: {bill.identifier} ({bill.session_id})
            </a>
          </dd>
          <dt className="font-semibold">Data source</dt>
          <dd>
            {bill.source_name}.{" "}
            <span className="break-all text-ink-soft">{bill.source_url}</span>
          </dd>
          <dt className="font-semibold">Source last updated</dt>
          <dd>{formatDateTime(bill.source_updated_at)}</dd>
          <dt className="font-semibold">Last synchronized</dt>
          <dd>{formatDateTime(bill.last_synced_at)}</dd>
          {bill.source_license_notes && (
            <>
              <dt className="font-semibold">Source disclaimer</dt>
              <dd className="text-ink-soft">{bill.source_license_notes}</dd>
            </>
          )}
        </dl>
        <ReportForm targetType="bill_data" targetId={bill.id} />
      </section>
    </article>
  );
}

function ActionsTable({ actions }: { actions: BillPage["actions"] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] border-collapse text-sm">
        <caption className="sr-only">Official actions</caption>
        <thead>
          <tr className="border-b border-rule text-left">
            <th scope="col" className="py-2 pr-4 font-semibold">
              Date
            </th>
            <th scope="col" className="py-2 pr-4 font-semibold">
              Where
            </th>
            <th scope="col" className="py-2 font-semibold">
              Action
            </th>
          </tr>
        </thead>
        <tbody>
          {actions.map((a) => (
            <tr key={a.sequence} className="border-b border-rule/60 align-top">
              <td className="py-2 pr-4 whitespace-nowrap">{formatDate(a.action_date)}</td>
              <td className="py-2 pr-4">{ACTOR_LABELS[a.actor]}</td>
              <td className="py-2">
                {a.description}
                {a.comment && <span className="text-ink-soft"> — {a.comment}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Collapsible<T>({
  items,
  visible,
  noun,
  listClassName = "space-y-1",
  children,
}: {
  items: T[];
  visible: number;
  noun: string;
  listClassName?: string;
  children: (item: T) => React.ReactNode;
}) {
  const head = items.slice(0, visible);
  const rest = items.slice(visible);
  return (
    <>
      <ul className={listClassName}>{head.map(children)}</ul>
      {rest.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-sm font-medium">
            Show {rest.length} more {noun}
          </summary>
          <ul className={`mt-2 ${listClassName}`}>{rest.map(children)}</ul>
        </details>
      )}
    </>
  );
}
