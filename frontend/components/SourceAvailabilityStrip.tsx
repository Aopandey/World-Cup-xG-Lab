import SourceBadge from "@/components/SourceBadge";
import { formatNumber } from "@/lib/format";

type SourceAvailabilityStripProps = {
  statsbombShots?: number;
  fbrefAvailable?: boolean;
  understatAvailable?: boolean;
  understatModelAvailable?: boolean;
  datambAvailable?: boolean;
  compact?: boolean;
};

export default function SourceAvailabilityStrip({
  statsbombShots = 0,
  fbrefAvailable = false,
  understatAvailable = false,
  understatModelAvailable = false,
  datambAvailable = false,
  compact = false
}: SourceAvailabilityStripProps) {
  return (
    <div className={`flex flex-wrap items-center gap-2 ${compact ? "" : "text-sm"}`}>
      <SourceBadge
        source="statsbomb"
        label={statsbombShots > 0 ? `${formatNumber(statsbombShots)} past sample shots` : "No past sample shots"}
        muted={statsbombShots <= 0}
      />
      {datambAvailable ? <SourceBadge source="datamb" label="Percentile profile" /> : null}
      {fbrefAvailable ? <SourceBadge source="fbref" label="Recent form" /> : null}
      {understatAvailable ? <SourceBadge source="understat" label="Club xG" /> : null}
      {understatModelAvailable ? <SourceBadge source="understat" label="Experimental shot model" /> : null}
    </div>
  );
}
