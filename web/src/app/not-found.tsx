import Link from "next/link";

export default function NotFound() {
  return (
    <div className="space-y-4">
      <h1 className="text-3xl">Page not found</h1>
      <p>
        That page doesn&apos;t exist.{" "}
        <Link href="/bills" className="text-sienna underline">
          Browse bills
        </Link>{" "}
        or go to the{" "}
        <Link href="/" className="text-sienna underline">
          home page
        </Link>
        .
      </p>
    </div>
  );
}
