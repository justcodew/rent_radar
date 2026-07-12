import clsx from "clsx";

const RISK_STYLE: Record<string, string> = {
  疑似中介: "bg-red-100 text-red-700",
  联系方式复用: "bg-red-100 text-red-700",
  价格异常低: "bg-amber-100 text-amber-700",
  价格异常: "bg-amber-100 text-amber-700",
  图片存疑: "bg-amber-100 text-amber-700",
  描述过简: "bg-gray-100 text-gray-600",
  用户标记虚假: "bg-red-100 text-red-700",
};

export default function RiskTag({ tag }: { tag: string }) {
  const style = RISK_STYLE[tag] || "bg-gray-100 text-gray-600";
  return <span className={clsx("badge", style)}>{tag}</span>;
}
