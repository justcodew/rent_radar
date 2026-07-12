import type { InsightsResult, Surroundings } from "../types";

const REC_STYLE: Record<string, { bg: string; emoji: string; label: string }> = {
  "值得看": { bg: "from-emerald-500 to-green-600", emoji: "✅", label: "值得看" },
  "谨慎看": { bg: "from-amber-500 to-orange-600", emoji: "⚠️", label: "谨慎看" },
  "别看": { bg: "from-rose-500 to-red-600", emoji: "⛔", label: "别看" },
};

function getRecStyle(rec?: string) {
  if (!rec) return null;
  for (const k of Object.keys(REC_STYLE)) {
    if (rec.includes(k)) return REC_STYLE[k];
  }
  return null;
}

interface Props {
  insights: InsightsResult | null | undefined;
  loading?: boolean;
  onRefresh?: () => void;
}

export default function InsightsCard({ insights, loading, onRefresh }: Props) {
  if (loading) {
    return (
      <div className="rounded-2xl p-6 bg-gradient-to-br from-slate-50 to-orange-50 border border-orange-100">
        <div className="flex items-center gap-3 text-gray-500">
          <div className="w-5 h-5 border-2 border-orange-400 border-t-transparent rounded-full animate-spin" />
          <span>「老广」朋友正在打量这套房子…</span>
        </div>
      </div>
    );
  }

  if (!insights || insights.skipped) {
    return (
      <div className="rounded-2xl p-6 bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 text-center">
        <div className="text-3xl mb-2">🤖</div>
        <div className="text-gray-700 font-medium mb-1">AI 深度洞察未生成</div>
        <div className="text-sm text-gray-500">
          {insights?.reason || "点击下方按钮，让 AI 以「懂行朋友」口吻帮你拆解这套房"}
        </div>
        {onRefresh && (
          <button onClick={onRefresh} className="btn-primary mt-4 text-sm">
            ✨ 生成深度洞察
          </button>
        )}
      </div>
    );
  }

  const rec = getRecStyle(insights.recommendation);
  const confidence = insights.confidence ?? 0;

  return (
    <div className="space-y-4">
      {/* 顶部推荐结论 banner */}
      {rec && (
        <div
          className={`rounded-2xl p-5 bg-gradient-to-r ${rec.bg} text-white shadow-lg`}
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs opacity-80 mb-1">
                「老广」朋友的整体判断
              </div>
              <div className="text-2xl font-bold flex items-center gap-2">
                <span className="text-3xl">{rec.emoji}</span>
                {rec.label}
              </div>
              {insights.summary && (
                <div className="text-sm opacity-90 mt-2 max-w-md">
                  {insights.summary}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-xs opacity-75">置信度</div>
              <div className="text-2xl font-bold">
                {(confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 小区画像 */}
      {insights.community_profile && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-lg">🏘️</span>
            <h3 className="font-semibold text-gray-800">小区画像</h3>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">
            {insights.community_profile}
          </p>
        </div>
      )}

      {/* 周边配套 */}
      {hasSurroundings(insights.surroundings) && (
        <SurroundingsCard
          surroundings={insights.surroundings!}
          confidence={insights.surroundings_confidence}
        />
      )}

      {/* 优缺点对比 */}
      <div className="grid md:grid-cols-2 gap-4">
        {insights.pros && insights.pros.length > 0 && (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">👍</span>
              <h3 className="font-semibold text-emerald-700">真实优点</h3>
            </div>
            <ul className="space-y-2">
              {insights.pros.map((p, i) => (
                <li key={i} className="text-sm text-gray-700 flex gap-2">
                  <span className="text-emerald-500 mt-0.5">•</span>
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {insights.cons && insights.cons.length > 0 && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50/50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">⚠️</span>
              <h3 className="font-semibold text-rose-700">潜在坑点</h3>
            </div>
            <ul className="space-y-2">
              {insights.cons.map((c, i) => (
                <li key={i} className="text-sm text-gray-700 flex gap-2">
                  <span className="text-rose-500 mt-0.5">•</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 价位评价 + 建议 */}
      <div className="grid md:grid-cols-2 gap-4">
        {insights.price_verdict && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">💰</span>
              <h3 className="font-semibold text-gray-800">价位评价</h3>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">
              {insights.price_verdict}
            </p>
            {insights.area_avg_price && (
              <div className="mt-2 text-xs text-gray-500">
                区域均价参考：¥{insights.area_avg_price}/月
              </div>
            )}
          </div>
        )}

        {insights.tips && insights.tips.length > 0 && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">🎯</span>
              <h3 className="font-semibold text-gray-800">避坑建议</h3>
            </div>
            <ul className="space-y-2">
              {insights.tips.map((t, i) => (
                <li key={i} className="text-sm text-gray-700 flex gap-2">
                  <span className="text-brand-500 font-semibold mt-0.5">
                    {i + 1}.
                  </span>
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* footer */}
      <div className="text-xs text-gray-400 flex items-center justify-between px-1">
        <span>
          {insights.from_cache ? "（来自缓存）" : ""}
          {insights.model && ` 模型：${insights.model}`}
          {insights.analyzed_at &&
            ` · ${new Date(insights.analyzed_at).toLocaleDateString("zh-CN")}`}
        </span>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="text-brand-500 hover:text-brand-600"
          >
            重新生成 →
          </button>
        )}
      </div>
    </div>
  );
}

function hasSurroundings(s?: Surroundings | null): boolean {
  if (!s) return false;
  return ["subway", "school", "hospital", "mall"].some(
    (k) => (s as any)[k] && (s as any)[k].length > 0
  );
}

function walkColor(min?: number) {
  if (min == null) return "text-gray-400";
  if (min <= 5) return "text-emerald-600";
  if (min <= 10) return "text-amber-600";
  if (min <= 20) return "text-orange-600";
  return "text-rose-600";
}

const GROUPS: { key: keyof Surroundings; icon: string; label: string }[] = [
  { key: "subway", icon: "🚇", label: "地铁" },
  { key: "mall", icon: "🛒", label: "商场/超市/菜场" },
  { key: "school", icon: "🎓", label: "学校" },
  { key: "hospital", icon: "🏥", label: "医院" },
];

function SurroundingsCard({
  surroundings,
  confidence,
}: {
  surroundings: Surroundings;
  confidence?: number;
}) {
  const conf = confidence ?? 0.5;
  const confLabel =
    conf >= 0.7 ? "高置信" : conf >= 0.4 ? "中置信" : "低置信（可能不准）";
  const confColor =
    conf >= 0.7
      ? "text-emerald-600 bg-emerald-50"
      : conf >= 0.4
        ? "text-amber-600 bg-amber-50"
        : "text-rose-600 bg-rose-50";

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">🗺️</span>
          <h3 className="font-semibold text-gray-800">周边配套</h3>
          <span className="text-xs text-gray-400">（LLM 推断）</span>
        </div>
        <span className={`text-xs px-2 py-0.5 rounded-full ${confColor}`}>
          {confLabel}
        </span>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {GROUPS.map(({ key, icon, label }) => {
          const items = surroundings[key] || [];
          if (items.length === 0) return null;
          return (
            <div key={key}>
              <div className="text-xs text-gray-500 mb-1.5">
                {icon} {label}
              </div>
              <ul className="space-y-1">
                {items.map((it, i) => (
                  <li
                    key={i}
                    className="flex items-center justify-between text-sm py-1"
                  >
                    <span className="text-gray-700 truncate pr-2">
                      {it.name}
                      {(it.type || it.level) && (
                        <span className="ml-1 text-xs text-gray-400">
                          · {it.type || it.level}
                        </span>
                      )}
                    </span>
                    {it.walk_min > 0 && (
                      <span className={`text-xs font-medium ${walkColor(it.walk_min)} shrink-0`}>
                        步行 {it.walk_min}min
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
