import type { Metadata } from "next";

export const metadata: Metadata = { title: "Methodology" };

export default function MethodologyPage() {
  return (
    <article className="max-w-3xl space-y-10">
      <header className="space-y-3">
        <h1 className="text-4xl">Methodology</h1>
        <p className="text-xl text-ink-soft">Where our data comes from, how we process it and what its limits are.</p>
      </header>

      <section className="space-y-3" aria-labelledby="sources">
        <h2 id="sources" className="text-2xl">
          Data sources
        </h2>
        <p>
          All legislative records on this site come from the{" "}
          <a href="https://capitol.texas.gov/billlookup/filedownloads.aspx" className="text-sienna underline">
            Texas Legislative Council&apos;s bulk downloads
          </a>{" "}
          (ftp.legis.state.tx.us), the same data behind{" "}
          <a href="https://capitol.texas.gov/" className="text-sienna underline">
            Texas Legislature Online
          </a>
          . These official files are our source of truth. We use them instead of scraping the Legislature&apos;s website,
          as the Council asks automated users to do.
        </p>
        <p>
          Third-party services such as Open States and LegiScan republish official records. We may use them later for
          details the bulk files don&apos;t include, such as member-by-member floor votes. Where they disagree with the
          official record, the official record wins.
        </p>
        <p>
          The Council states that it makes no representation as to the completeness, timeliness or accuracy of the bulk
          data. Always confirm important details against the official bill page linked on each record.
        </p>
      </section>

      <section className="space-y-3" aria-labelledby="sync">
        <h2 id="sync" className="text-2xl">
          How records are updated
        </h2>
        <ul className="ml-5 list-disc space-y-2">
          <li>
            A scheduled job downloads each bill&apos;s official history record, checks that it is well formed, and
            stores it. Requests are spaced out and retried politely when the source is busy.
          </li>
          <li>
            The job uses the Council&apos;s list of recently changed bills, so it only re-downloads what changed. The
            Council&apos;s files themselves are generally refreshed once a day.
          </li>
          <li>
            Each bill shows when it was <strong>last synchronized</strong> and when the source last changed it. If a
            record hasn&apos;t been checked recently, the page says so. This site is <strong>not real-time</strong>.
          </li>
          <li>
            Every version of a bill&apos;s text (introduced, committee report, engrossed, enrolled) is kept. If the
            official text of a version changes, the earlier copy is preserved rather than overwritten.
          </li>
        </ul>
      </section>

      <section className="space-y-3" aria-labelledby="status">
        <h2 id="status" className="text-2xl">
          How we describe a bill&apos;s status
        </h2>
        <p>
          A bill&apos;s status is derived only from the actions in its official history, using fixed rules that are
          published with our source code. For example, a bill is shown as having passed both chambers only when the
          second chamber passes it without changes, or when both chambers agree on the same text. If no rule applies,
          the status is shown as unknown rather than guessed.
        </p>
        <p>
          Proposed legislation is never described as law. A bill becomes law only after it passes both chambers in the
          same form and is signed by the Governor, or becomes law without a signature. Proposed constitutional
          amendments also need voter approval. When a regular session ends, bills that hadn&apos;t passed both chambers
          are shown as not passed.
        </p>
      </section>

      <section className="space-y-3" aria-labelledby="summaries">
        <h2 id="summaries" className="text-2xl">
          Plain-language summaries
        </h2>
        <p>
          Summaries are not published yet. When they are, they will follow these rules:
        </p>
        <ul className="ml-5 list-disc space-y-2">
          <li>Each summary is written from the text of one specific official version of the bill, never from the title alone.</li>
          <li>
            Every statement cites the bill section it comes from, and the cited wording is automatically checked against
            the official text.
          </li>
          <li>
            Statements of fact are kept apart from inferred effects, which are labeled as inferences. Summaries never
            guess at motives or recommend supporting or opposing a bill.
          </li>
          <li>
            Each summary records the bill version, AI model and date it was generated from. When the bill text changes,
            older summaries are withdrawn and regenerated.
          </li>
          <li>
            A person reviews each summary against the official text before it is published. Readers can report a
            problem with any summary, no account needed.
          </li>
          <li>Summaries are clearly labeled as AI-generated. They can contain errors, and the official text is the authority.</li>
        </ul>
      </section>

      <section className="space-y-3" aria-labelledby="limits">
        <h2 id="limits" className="text-2xl">
          Known limitations
        </h2>
        <ul className="ml-5 list-disc space-y-2">
          <li>Only a sample of bills from the 89th and 90th Legislatures is loaded in this proof of concept.</li>
          <li>
            Committee vote totals are shown, but member-by-member floor votes are not available in the bulk files and are
            not shown yet.
          </li>
          <li>
            Legislator names appear as the official records list them. Party and district information is not shown yet.
          </li>
          <li>Bill analyses are linked but not stored. Very long bill versions are shown in part, with a link to the full official text.</li>
        </ul>
      </section>
    </article>
  );
}
