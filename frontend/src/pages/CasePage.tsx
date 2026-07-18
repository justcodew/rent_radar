import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";

export default function CasePage() {
  const [caseData, setCaseData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadCase = useCallback((refresh = false) => {
    if (refresh) setRefreshing(true); else setLoading(true);
    const url = `/api/v1/cases/yuexiu-4k-elevator-balcony${refresh ? "?refresh=true" : ""}`;
    fetch(url)
      .then((r) => r.json())
      .then((d) => {
        setCaseData(d.data || d);
        setLoading(false);
        setRefreshing(false);
      })
      .catch(() => { setLoading(false); setRefreshing(false); });
  }, []);

  useEffect(() => { loadCase(); }, [loadCase]);

  if (loading) return <div className="text-center py-12 text-gray-400">加载中...</div>;
  if (!caseData) return <div className="text-center py-12 text-gray-400">案例不存在</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* 标题区 */}
      <div className="rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 p-6 text-white shadow-lg">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-xs opacity-80 mb-1">📋 需求案例</div>
            <h1 className="text-2xl font-bold leading-tight">{caseData.title}</h1>
            <p className="mt-2 text-sm opacity-90">{caseData.subtitle}</p>
          </div>
          <button
            onClick={() => loadCase(true)}
            disabled={refreshing}
            className="flex-shrink-0 bg-white/20 hover:bg-white/30 text-white text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap"
          >
            {refreshing ? "🔄 刷新中..." : "🔄 刷新数据"}
          </button>
        </div>
        <div className="mt-3 flex items-center gap-2 text-xs bg-white/20 rounded-lg px-3 py-1.5 inline-block">
          👤 {caseData.persona}
          {caseData.refreshed && (
            <span className="ml-2 text-green-300">✓ 已更新</span>
          )}
        </div>
      </div>

      {/* 需求清单 */}
      <div className="card p-5">
        <h2 className="text-lg font-semibold mb-3">📝 需求清单</h2>
        <div className="space-y-2">
          {caseData.requirements?.map((req: any, i: number) => (
            <div key={i} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
              <span className="text-xl">{req.icon}</span>
              <span className="text-sm text-gray-500 w-24">{req.label}</span>
              <span className="text-sm text-gray-800 font-medium flex-1">{req.value}</span>
              <span className="text-green-500">✓</span>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-3 border-t text-sm">
          <span className="text-gray-500">预算范围：</span>
          <span className="font-bold text-brand-600">{caseData.budget}</span>
        </div>
      </div>

      {/* AI 推荐片区 */}
      <div className="card p-5">
        <h2 className="text-lg font-semibold mb-3">🤖 AI 推荐片区</h2>
        <div className="space-y-3">
          {caseData.ai_communities?.map((c: any, i: number) => (
            <div key={i} className="border rounded-lg p-3">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium text-gray-800">{i + 1}. {c.name}</h3>
                <div className="flex gap-1 flex-shrink-0">
                  {c.match_tags?.map((t: string) => (
                    <span key={t} className="px-1.5 py-0.5 rounded text-xs bg-blue-50 text-blue-600">{t}</span>
                  ))}
                </div>
              </div>
              <p className="mt-1 text-sm text-gray-600 leading-relaxed">{c.reason}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 现实分析 */}
      {caseData.reality_analysis && (
        <div className="card p-5 border-l-4 border-amber-400">
          <h2 className="text-lg font-semibold mb-2">💡 现实分析</h2>
          <div className="text-sm font-medium text-amber-600 mb-2">
            结论：{caseData.reality_analysis.verdict}
          </div>
          <p className="text-sm text-gray-600 mb-3">{caseData.reality_analysis.detail}</p>
          <div className="space-y-1">
            {caseData.reality_analysis.tips?.map((tip: string, i: number) => (
              <div key={i} className="text-sm text-gray-600 flex gap-2">
                <span className="text-amber-500">💡</span>
                <span>{tip}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 匹配房源 */}
      <div className="card p-5">
        <h2 className="text-lg font-semibold mb-3">
          🏠 数据库匹配房源
          <span className="ml-2 text-sm font-normal text-gray-500">({caseData.total_matched || 0} 条)</span>
        </h2>
        {caseData.matched_listings?.length > 0 ? (
          <div className="space-y-3">
            {caseData.matched_listings.map((l: any) => (
              <Link
                key={l.id}
                to={`/listings/${l.id}`}
                className="block border rounded-lg p-3 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-800 text-sm">{l.title}</h3>
                    <p className="text-xs text-gray-400 mt-1 line-clamp-2">{l.content_preview}</p>
                  </div>
                  {l.price != null && (
                    <div className="text-brand-600 font-bold whitespace-nowrap">
                      ¥{l.price}<span className="text-xs text-gray-400 font-normal">/月</span>
                    </div>
                  )}
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {l.match_tags?.map((t: string) => (
                    <span key={t} className={`px-1.5 py-0.5 rounded text-xs ${
                      t.includes("电梯") ? "bg-blue-50 text-blue-600" :
                      t.includes("阳台") ? "bg-green-50 text-green-600" :
                      t.includes("🚇") ? "bg-cyan-50 text-cyan-600" :
                      "bg-gray-100 text-gray-600"
                    }`}>{t}</span>
                  ))}
                  {l.area_name && (
                    <span className="px-1.5 py-0.5 rounded text-xs bg-purple-50 text-purple-600">📍 {l.area_name}</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-400 text-sm">
            当前数据库暂无完全匹配的房源,建议扩大搜索范围或重新采集
          </div>
        )}
      </div>
    </div>
  );
}
