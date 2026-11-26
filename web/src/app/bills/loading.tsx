import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="space-y-6" aria-busy="true">
      <p className="sr-only" role="status">
        Loading legislative data…
      </p>
      <Skeleton className="h-10 w-48 bg-muted" />
      <Skeleton className="h-28 w-full bg-muted" />
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="space-y-2 border-b border-rule pb-4">
          <Skeleton className="h-5 w-32 bg-muted" />
          <Skeleton className="h-4 w-full max-w-2xl bg-muted" />
        </div>
      ))}
    </div>
  );
}
