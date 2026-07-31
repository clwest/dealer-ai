import { cn } from "@/lib/utils";

interface Props {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "default" | "warn" | "good";
  icon?: React.ReactNode;
}

const toneStyle: Record<NonNullable<Props["tone"]>, string> = {
  default: "text-brand-blue",
  warn: "text-amber-600",
  good: "text-emerald-600",
};

export default function StatCard({
  label,
  value,
  hint,
  tone = "default",
  icon,
}: Props) {
  return (
    <div className="card flex flex-col gap-1 p-5">
      <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-slate-500">
        <span>{label}</span>
        {icon ? <span className="text-slate-400">{icon}</span> : null}
      </div>
      <div className={cn("text-3xl font-bold", toneStyle[tone])}>{value}</div>
      {hint ? <div className="text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}
