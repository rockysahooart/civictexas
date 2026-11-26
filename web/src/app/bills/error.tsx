"use client";

import { Button } from "@/components/ui/button";

export default function BillsError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="space-y-4 rounded border border-rule bg-card p-6" role="alert">
      <h1 className="text-2xl">Something went wrong loading this page</h1>
      <p>
        The legislative data could not be loaded. This is a problem on our side, not with the official records. You can
        try again, or look up the bill on{" "}
        <a href="https://capitol.texas.gov/" className="text-sienna underline">
          Texas Legislature Online
        </a>
        .
      </p>
      <Button onClick={() => reset()}>Try again</Button>
    </div>
  );
}
