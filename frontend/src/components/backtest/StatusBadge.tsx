import { Badge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";

type BacktestStatus = "PENDING" | "RUNNING" | "COMPLETE" | "FAILED";

interface StatusBadgeProps {
  status: BacktestStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const variants: Record<BacktestStatus, "default" | "secondary" | "success" | "destructive" | "warning"> = {
    PENDING: "warning",
    RUNNING: "secondary",
    COMPLETE: "success",
    FAILED: "destructive",
  };

  const labels: Record<BacktestStatus, string> = {
    PENDING: "Pending",
    RUNNING: "Running",
    COMPLETE: "Complete",
    FAILED: "Failed",
  };

  return (
    <Badge variant={variants[status]} className="gap-1">
      {status === "RUNNING" && <Loader2 className="h-3 w-3 animate-spin" />}
      {labels[status]}
    </Badge>
  );
}
