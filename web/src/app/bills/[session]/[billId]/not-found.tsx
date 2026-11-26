import Link from "next/link";

export default function BillNotFound() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl">Bill not found</h1>
      <p className="max-w-2xl">
        We don&apos;t have this bill. This proof of concept holds only a sample of bills, so it may still exist. Check{" "}
        <a href="https://capitol.texas.gov/" className="text-sienna underline">
          Texas Legislature Online
        </a>{" "}
        or{" "}
        <Link href="/bills" className="text-sienna underline">
          search the bills we have
        </Link>
        .
      </p>
    </div>
  );
}
