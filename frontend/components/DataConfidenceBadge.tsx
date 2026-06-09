import EvidenceBadge from "@/components/EvidenceBadge";
import type { DataConfidence } from "@/lib/types";

type DataConfidenceBadgeProps = {
  value: DataConfidence | string;
  hasHistoricalSample?: boolean;
  hasExternalContext?: boolean;
};

export default function DataConfidenceBadge({
  value,
  hasHistoricalSample = false,
  hasExternalContext = false
}: DataConfidenceBadgeProps) {
  return (
    <EvidenceBadge
      level={value}
      hasHistoricalSample={hasHistoricalSample}
      hasExternalContext={hasExternalContext}
    />
  );
}
