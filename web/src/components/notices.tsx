import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { formatDateTime, isStale, relativeAge, staleAfterHours } from "@/lib/format";

export function StaleNotice({ lastSynced }: { lastSynced: Date | null }) {
  if (!isStale(lastSynced)) return null;
  return (
    <Alert role="note" className="border-[#e2c77f] bg-warning-bg text-warning-ink">
      <AlertTitle>This record may be out of date</AlertTitle>
      <AlertDescription className="text-warning-ink">
        It was last checked against the official source{" "}
        {lastSynced ? `${relativeAge(lastSynced)} (${formatDateTime(lastSynced)})` : "at an unknown time"}, which is
        longer than our {staleAfterHours()}-hour target. Check the official record for the latest information.
      </AlertDescription>
    </Alert>
  );
}

export function DataUnavailable() {
  return (
    <Alert role="note" className="border-rule bg-card">
      <AlertTitle>Legislative data is unavailable right now</AlertTitle>
      <AlertDescription>
        We couldn&apos;t reach our database. You can still find every bill on{" "}
        <a href="https://capitol.texas.gov/" className="text-sienna underline">
          Texas Legislature Online
        </a>
        , the official source. If you run this site locally, see the{" "}
        <Link href="/methodology" className="text-sienna underline">
          methodology
        </Link>{" "}
        page and the project README for setup steps.
      </AlertDescription>
    </Alert>
  );
}

export function ProofOfConceptNotice() {
  return (
    <p className="border-l-4 border-sienna bg-card px-4 py-3 text-sm">
      <strong>Proof of concept.</strong> This directory holds a small sample of bills from the 89th and 90th Texas
      Legislatures, not every bill. It is not updated in real time.
    </p>
  );
}
