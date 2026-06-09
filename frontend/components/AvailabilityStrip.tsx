import SourceAvailabilityStrip from "@/components/SourceAvailabilityStrip";

type AvailabilityStripProps = {
  statsbombShots?: number;
  fbrefAvailable?: boolean;
  understatAvailable?: boolean;
  understatModelAvailable?: boolean;
  datambAvailable?: boolean;
  compact?: boolean;
};

export default function AvailabilityStrip({
  statsbombShots = 0,
  fbrefAvailable = false,
  understatAvailable = false,
  understatModelAvailable = false,
  datambAvailable = false,
  compact = false
}: AvailabilityStripProps) {
  return (
    <SourceAvailabilityStrip
      compact={compact}
      statsbombShots={statsbombShots}
      fbrefAvailable={fbrefAvailable}
      understatAvailable={understatAvailable}
      understatModelAvailable={understatModelAvailable}
      datambAvailable={datambAvailable}
    />
  );
}
