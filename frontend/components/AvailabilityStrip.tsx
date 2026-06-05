import SourceBadge from "@/components/SourceBadge";
import { formatNumber } from "@/lib/format";

type AvailabilityStripProps = {
  statsbombShots?: number;
  fbrefAvailable?: boolean;
  understatAvailable?: boolean;
  understatModelAvailable?: boolean;
  compact?: boolean;
};

export default function AvailabilityStrip({
  statsbombShots = 0,
  fbrefAvailable = false,
  understatAvailable = false,
  understatModelAvailable = false,
  compact = false
}: AvailabilityStripProps) {
  return (
    <div className={`flex flex-wrap items-center gap-2 ${compact ? "" : "text-sm"}`}>
      <SourceBadge
        source="statsbomb"
        label={statsbombShots > 0 ? `${formatNumber(statsbombShots)} SB shots` : "No SB shots"}
        muted={statsbombShots <= 0}
      />
      {fbrefAvailable ? <SourceBadge source="fbref" label="FBref" /> : null}
      {understatAvailable ? <SourceBadge source="understat" label="Understat" /> : null}
      {understatModelAvailable ? <SourceBadge source="understat" label="Understat model" /> : null}
    </div>
  );
}
