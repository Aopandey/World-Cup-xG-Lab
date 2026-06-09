import MetricCard from "@/components/MetricCard";

type StatCardProps = {
  label: string;
  value: string | number;
  detail?: string;
  accent?: "statsbomb" | "fbref" | "understat" | "datamb" | "neutral";
};

export default function StatCard({ label, value, detail, accent = "neutral" }: StatCardProps) {
  return <MetricCard label={label} value={value} detail={detail} accent={accent} source={accent === "neutral" ? undefined : accent} />;
}
