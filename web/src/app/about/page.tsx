import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <article className="max-w-3xl space-y-8">
      <header className="space-y-3">
        <h1 className="text-4xl">About Civic Texas</h1>
        <p className="text-xl text-ink-soft">
          An independent, nonpartisan civic technology project that makes Texas state legislation easier to follow and
          understand.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-2xl">Mission</h2>
        <p>
          Civic Texas exists to narrow the distance between Texans and their state government. We bring official
          legislative records into one readable place so anyone can see what has been filed, what has changed and where
          a bill stands, without needing to know how the Legislature&apos;s systems work.
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li>
            <strong>Transparency:</strong> every fact links back to the official record.
          </li>
          <li>
            <strong>Civic education:</strong> plain explanations of how the process works.
          </li>
          <li>
            <strong>Accessibility:</strong> plain language and pages built to WCAG 2.2 AA.
          </li>
          <li>
            <strong>Informed participation:</strong> context for forming your own views.
          </li>
          <li>
            <strong>Neutrality:</strong> we do not endorse or oppose legislation, parties or legislators.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl">Independence</h2>
        <p>
          Civic Texas is <strong>not affiliated</strong> with the State of Texas, the Texas Legislature, the Texas
          Legislative Council, any government agency or any political party. We do not use official seals or branding.
          The information here is for general understanding and is not legal advice.
        </p>
        <p>
          Comments and feedback from the community, when they are added, will represent the views of the people who post
          them, and will always be shown separately from official records.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl">Where things stand</h2>
        <p>
          This is an early proof of concept with a small sample of real bills. It shows how official data flows from the
          Legislature&apos;s published files into a searchable directory. Accounts, notifications, AI summaries and
          community discussion are not available yet.
        </p>
        <p>
          Read the{" "}
          <Link href="/methodology" className="text-sienna underline">
            methodology
          </Link>{" "}
          or see the{" "}
          <a href="https://github.com/rockysahooart/civictexas" className="text-sienna underline">
            source code on GitHub
          </a>
          .
        </p>
      </section>
    </article>
  );
}
