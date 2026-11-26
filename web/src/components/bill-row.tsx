import Link from "next/link";
import { StatusBadge } from "@/components/status-badge";
import type { BillListItem } from "@/lib/bills";
import { formatDate } from "@/lib/format";
import { billSlug } from "@/lib/search-params";

export function BillRow({ bill }: { bill: BillListItem }) {
  const href = `/bills/${bill.session_id}/${billSlug(bill.bill_type, bill.bill_number)}`;
  return (
    <li className="border-b border-rule py-4 first:pt-0">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h3 className="font-serif text-lg">
          <Link href={href} className="underline decoration-rule decoration-2 hover:decoration-sienna">
            {bill.identifier}
            <span className="sr-only">, {bill.session_id} session</span>
          </Link>
          <span className="ml-2 font-sans text-sm font-normal text-ink-soft" aria-hidden="true">
            {bill.session_id}
          </span>
        </h3>
        <StatusBadge status={bill.status} />
      </div>
      <p className="mt-1 max-w-3xl">{bill.caption}</p>
      {bill.last_action_text && (
        <p className="mt-1 text-sm text-ink-soft">
          Last action {formatDate(bill.last_action_date)}: {bill.last_action_text.replace(/^\d{2}\/\d{2}\/\d{4}\s+[HSE]\s+/, "")}
        </p>
      )}
    </li>
  );
}
