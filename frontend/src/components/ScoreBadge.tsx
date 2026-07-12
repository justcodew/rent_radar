import clsx from "clsx";

interface Props {
  score?: number;
  size?: "sm" | "md" | "lg";
  showLevel?: boolean;
}

const levelFromScore = (score: number) => {
  if (score >= 90) return { label: "精选好房", color: "bg-emerald-500", text: "text-white" };
  if (score >= 75) return { label: "优质好房", color: "bg-blue-500", text: "text-white" };
  if (score >= 60) return { label: "一般", color: "bg-amber-500", text: "text-white" };
  return { label: "不推荐", color: "bg-gray-400", text: "text-white" };
};

export default function ScoreBadge({ score, size = "md", showLevel = false }: Props) {
  if (score == null) {
    return <span className="badge bg-gray-100 text-gray-400">未评分</span>;
  }
  const { label, color, text } = levelFromScore(score);
  const sizeCls = size === "lg" ? "w-16 h-16 text-2xl" : size === "sm" ? "w-10 h-10 text-sm" : "w-12 h-12 text-base";

  return (
    <div className="flex items-center gap-2">
      <div className={clsx("rounded-full flex items-center justify-center font-bold", color, text, sizeCls)}>
        {score}
      </div>
      {showLevel && (
        <div>
          <div className="text-sm font-semibold text-gray-800">{label}</div>
          <div className="text-xs text-gray-500">好房指数</div>
        </div>
      )}
    </div>
  );
}
