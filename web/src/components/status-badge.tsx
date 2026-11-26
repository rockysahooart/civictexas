import { Badge } from "@/components/ui/badge";
import { statusLabel, statusTone, type StatusTone } from "@/lib/status";
import { cn } from "@/lib/utils";

// Tones avoid red/blue party associations. Text never relies on color alone:
// the label always states the status.
const TONE_CLASSES: Record<StatusTone, string> = {
  neutral: "border-rule bg-card text-foreground",
  progress: "border-[#b9a98a] bg-[#f3ead6] text-[#4f3a12]",
  enacted: "border-[#9cbfa5] bg-[#e4f0e6] text-[#1c4a2a]",
  stopped: "border-[#c9c4ba] bg-[#ebe8e2] text-[#3c3a36]",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("h-auto rounded-sm px-2 py-0.5 text-xs font-semibold whitespace-normal", TONE_CLASSES[statusTone(status)], className)}
    >
      {statusLabel(status)}
    </Badge>
  );
}
