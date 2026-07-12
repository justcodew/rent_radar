import type { ScoreDetail } from "../types";

const LABELS: Record<string, string> = {
  poster_frequency: "发布频率",
  poster_age: "账号年龄",
  poster_diversity: "内容多样性",
  poster_contact_reuse: "联系方式",
  image_authenticity: "图片真实",
  description: "描述详尽",
  price_reasonable: "价格合理",
  info_completeness: "信息完整",
};

const MAX: Record<string, number> = {
  poster_frequency: 9,
  poster_age: 7.5,
  poster_diversity: 7.5,
  poster_contact_reuse: 6,
  image_authenticity: 17.5,
  description: 21,
  price_reasonable: 14,
  info_completeness: 17.5,
};

const KEYS = Object.keys(LABELS);

export default function ScoreRadar({ score }: { score: ScoreDetail }) {
  const size = 260;
  const center = size / 2;
  const radius = 100;
  const levels = 4;

  // 把分数（0-100 pt）映射到 0-1
  const points = KEYS.map((k) => {
    const val = score.sub_scores?.[k] ?? 0;
    const max = MAX[k] || 1;
    return Math.max(0, Math.min(1, val / max));
  });

  // 计算每个顶点坐标
  const angle = (i: number) => (Math.PI * 2 * i) / KEYS.length - Math.PI / 2;
  const pointAt = (ratio: number, i: number) => {
    const r = radius * ratio;
    return [center + r * Math.cos(angle(i)), center + r * Math.sin(angle(i))];
  };

  const dataPath = points
    .map((p, i) => {
      const [x, y] = pointAt(p, i);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ") + " Z";

  return (
    <div className="flex justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* 背景网格 */}
        {Array.from({ length: levels }).map((_, li) => {
          const ratio = (li + 1) / levels;
          const polyPoints = KEYS.map((_, i) => {
            const [x, y] = pointAt(ratio, i);
            return `${x.toFixed(1)},${y.toFixed(1)}`;
          }).join(" ");
          return (
            <polygon
              key={li}
              points={polyPoints}
              fill="none"
              stroke="#e5e7eb"
              strokeWidth={1}
            />
          );
        })}

        {/* 轴线 */}
        {KEYS.map((_, i) => {
          const [x, y] = pointAt(1, i);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={x}
              y2={y}
              stroke="#e5e7eb"
              strokeWidth={1}
            />
          );
        })}

        {/* 数据多边形 */}
        <path
          d={dataPath}
          fill="rgba(249, 115, 22, 0.18)"
          stroke="#f97316"
          strokeWidth={2}
          strokeLinejoin="round"
        />

        {/* 顶点圆点 */}
        {points.map((p, i) => {
          const [x, y] = pointAt(p, i);
          return <circle key={i} cx={x} cy={y} r={3} fill="#ea580c" />;
        })}

        {/* 标签 */}
        {KEYS.map((k, i) => {
          const [x, y] = pointAt(1.18, i);
          const anchor =
            Math.abs(x - center) < 10 ? "middle" : x > center ? "start" : "end";
          return (
            <text
              key={k}
              x={x}
              y={y}
              fontSize={11}
              fill="#6b7280"
              textAnchor={anchor}
              dominantBaseline="middle"
            >
              {LABELS[k]}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
