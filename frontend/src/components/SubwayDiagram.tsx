import type { CommunityInfo, SubwayStation } from "../types/subway";

interface Props {
  station: SubwayStation;
  radiusKm: number;
  communities: CommunityInfo[];
  selectedName?: string | null;
  onSelect?: (name: string) => void;
}

const SIZE = 420;
const CENTER = SIZE / 2;
const MAX_PX = 175;

export default function SubwayDiagram({
  station,
  radiusKm,
  communities,
  selectedName,
  onSelect,
}: Props) {
  // 用半径 + 最远社区距离的最大值做缩放基准
  const maxDist = Math.max(
    ...communities.map((c) => c.distance_km),
    radiusKm * 1.05,
    0.1
  );
  const scale = (km: number) => (km / maxDist) * MAX_PX;
  const radiusPx = scale(radiusKm);

  // 投影到画布:bearing 0°=北=上,顺时针
  const points = communities.map((c) => {
    const r = scale(c.distance_km);
    const rad = (c.bearing_deg * Math.PI) / 180;
    return {
      ...c,
      x: CENTER + Math.sin(rad) * r,
      y: CENTER - Math.cos(rad) * r,
    };
  });

  // 距离刻度环(按半径的一半、全半径画两圈)
  const rings = [radiusKm / 2, radiusKm];

  return (
    <div className="card p-4 flex items-center justify-center">
      <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="max-w-full">
        {/* 距离刻度环 */}
        {rings.map((r, i) => (
          <circle
            key={i}
            cx={CENTER}
            cy={CENTER}
            r={scale(r)}
            fill={i === rings.length - 1 ? "rgba(59, 130, 246, 0.05)" : "none"}
            stroke={i === rings.length - 1 ? "#3b82f6" : "#e5e7eb"}
            strokeWidth={i === rings.length - 1 ? 1.5 : 1}
            strokeDasharray={i === rings.length - 1 ? "5 4" : "2 4"}
          />
        ))}
        {/* 半径标注 */}
        <text
          x={CENTER + 4}
          y={CENTER - radiusPx + 12}
          fill="#3b82f6"
          fontSize={11}
          fontWeight={600}
        >
          {radiusKm} km
        </text>
        <text
          x={CENTER + 4}
          y={CENTER - scale(radiusKm / 2) + 12}
          fill="#9ca3af"
          fontSize={10}
        >
          {(radiusKm / 2).toFixed(1)} km
        </text>

        {/* 方位 */}
        <text x={CENTER} y={14} textAnchor="middle" fill="#9ca3af" fontSize={11}>N</text>
        <text x={CENTER} y={SIZE - 6} textAnchor="middle" fill="#9ca3af" fontSize={11}>S</text>
        <text x={10} y={CENTER + 4} fill="#9ca3af" fontSize={11}>W</text>
        <text x={SIZE - 14} y={CENTER + 4} fill="#9ca3af" fontSize={11}>E</text>

        {/* 社区点 */}
        {points.map((p) => {
          const count = p.listings_count ?? 0;
          const has = count > 0;
          const r = has ? 7 : 4;
          const isSel = p.name === selectedName;
          const fill = has ? "#3b82f6" : "#d1d5db";
          return (
            <g
              key={p.name + p.lat}
              onClick={() => onSelect?.(p.name)}
              style={{ cursor: "pointer" }}
            >
              <circle
                cx={p.x}
                cy={p.y}
                r={r + (isSel ? 3 : 0)}
                fill={fill}
                stroke={isSel ? "#1e3a8a" : "#fff"}
                strokeWidth={isSel ? 2 : 1}
              />
              {has && (
                <text
                  x={p.x}
                  y={p.y + 3}
                  textAnchor="middle"
                  fontSize={9}
                  fill="#fff"
                  fontWeight={700}
                >
                  {count}
                </text>
              )}
              <text
                x={p.x}
                y={p.y - r - 4}
                textAnchor="middle"
                fontSize={9}
                fontWeight={has ? 600 : 400}
                fill={has ? "#1f2937" : "#9ca3af"}
              >
                {p.name.length > 8 ? p.name.slice(0, 7) + "…" : p.name}
              </text>
            </g>
          );
        })}

        {/* 中心:地铁站 */}
        <circle cx={CENTER} cy={CENTER} r={9} fill="#ef4444" stroke="#fff" strokeWidth={2} />
        <circle cx={CENTER} cy={CENTER} r={12} fill="none" stroke="#ef4444" strokeWidth={1.5} opacity={0.5}>
          <animate attributeName="r" values="9;18;9" dur="2.5s" repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.6;0;0.6" dur="2.5s" repeatCount="indefinite" />
        </circle>
        <text x={CENTER} y={CENTER + 28} textAnchor="middle" fontSize={13} fontWeight={700} fill="#dc2626">
          {station.name}
        </text>
        <text x={CENTER} y={CENTER + 42} textAnchor="middle" fontSize={10} fill="#9ca3af">
          {station.lines.map((l) => `${l}号线`).join(" · ")}
        </text>
      </svg>
    </div>
  );
}
