import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import dayjs from "dayjs";
import { listingApi, scoreApi, favoriteApi, markApi } from "../services/api";
import type { Listing, ScoreDetail, InsightsResult } from "../types";
import ScorePanel from "../components/ScorePanel";
import ScoreRadar from "../components/ScoreRadar";
import InsightsCard from "../components/InsightsCard";
import RiskTag from "../components/RiskTag";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";

export default function ListingDetailPage() {
  const { id } = useParams();
  const [listing, setListing] = useState<Listing | null>(null);
  const [score, setScore] = useState<ScoreDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [tab, setTab] = useState<"insights" | "score" | "original">("insights");
  const isAuth = useAuthStore((s) => !!s.accessToken);
  const showToast = useUIStore((s) => s.showToast);

  const load = () => {
    setLoading(true);
    Promise.all([listingApi.get(id!), scoreApi.get(id!).catch(() => null)])
      .then(([l, s]) => {
        setListing(l as Listing);
        setScore(s as ScoreDetail);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (id) load();
  }, [id]);

  const onFav = async (category: string) => {
    if (!isAuth) return showToast("请先登录");
    try {
      await favoriteApi.add(id!, category);
      showToast(`已加入「${category}」`);
    } catch (e: any) {
      showToast(e.message);
    }
  };

  const onMark = async (markType: string) => {
    if (!isAuth) return showToast("请先登录");
    try {
      await markApi.create(id!, markType);
      showToast("已提交，感谢反馈");
    } catch (e: any) {
      showToast(e.message);
    }
  };

  const onInsights = async () => {
    setAiLoading(true);
    try {
      const result = await scoreApi.insights(id!, false);
      if (result?.skipped) {
        showToast(`AI 暂不可用：${result.reason}`);
      } else {
        showToast("AI 深度分析完成");
        load();
      }
    } catch (e: any) {
      showToast(e.message);
    } finally {
      setAiLoading(false);
    }
  };

  if (loading) return <div className="text-center py-12 text-gray-400">加载中...</div>;
  if (!listing) return <div className="text-center py-12 text-gray-400">房源不存在</div>;

  const hasInsights = !!score?.ai_insights && !score.ai_insights.skipped;
  const heroImg = listing.image_urls?.[0];

  return (
    <div className="space-y-6">
      {/* 顶部 hero：标题 + 评分头部 */}
      <div className="card overflow-hidden">
        <div className="grid md:grid-cols-[1fr_280px] gap-0">
          {/* 主信息 */}
          <div className="p-6">
            <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
              <Link to="/search" className="hover:text-brand-600">← 搜索</Link>
              <span>·</span>
              <span>{listing.source === "douban" ? "豆瓣" : listing.source}</span>
              {listing.area_name && (
                <>
                  <span>·</span>
                  <span className="text-brand-600 font-medium">{listing.area_name}</span>
                </>
              )}
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-3 leading-tight">
              {listing.title || "（无标题）"}
            </h1>
            <div className="flex items-baseline gap-3 mb-4">
              {listing.price != null && (
                <span className="text-3xl font-bold text-brand-600">
                  ¥{listing.price}
                  <span className="text-base text-gray-400 font-normal"> /月</span>
                </span>
              )}
              <div className="flex flex-wrap gap-2 text-sm text-gray-600">
                {listing.layout && (
                  <span className="px-2 py-0.5 bg-gray-100 rounded">{listing.layout}</span>
                )}
                {listing.size_sqm != null && (
                  <span className="px-2 py-0.5 bg-gray-100 rounded">{listing.size_sqm}㎡</span>
                )}
                {listing.orientation && (
                  <span className="px-2 py-0.5 bg-gray-100 rounded">{listing.orientation}</span>
                )}
                {listing.floor_info && (
                  <span className="px-2 py-0.5 bg-gray-100 rounded">{listing.floor_info}</span>
                )}
              </div>
            </div>

            {listing.risk_tags && listing.risk_tags.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-1">
                {listing.risk_tags.map((t) => <RiskTag key={t} tag={t} />)}
              </div>
            )}

            {listing.location_detail && (
              <div className="text-sm text-gray-600 mb-2">
                📍 {listing.location_detail}
              </div>
            )}

            <div className="mt-4 pt-3 border-t flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400">
              {listing.posted_at && (
                <span>发布于 {dayjs(listing.posted_at).format("YYYY-MM-DD HH:mm")}</span>
              )}
              {listing.poster_name && <span>发布者：{listing.poster_name}</span>}
              {listing.source_url && (
                <a href={listing.source_url} target="_blank" rel="noreferrer" className="text-brand-600 hover:underline">
                  查看原帖 →
                </a>
              )}
            </div>
          </div>

          {/* 评分 mini */}
          {score && (
            <div className="bg-gradient-to-br from-orange-50 to-amber-50 p-5 flex flex-col items-center justify-center border-l border-orange-100">
              <div className="text-xs text-gray-500 mb-1">好房指数</div>
              <div className="text-5xl font-bold text-brand-600 leading-none">
                {score.general_score}
              </div>
              <div className="text-xs text-gray-500 mt-1">/ 100 · {score.level}</div>
              <div className="mt-2 text-amber-400 text-lg">
                {"★".repeat(score.stars)}
                <span className="text-gray-200">{"★".repeat(5 - score.stars)}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-3 text-xs">
                <div className="text-gray-500">发布者</div>
                <div className="font-semibold text-blue-600 text-right">{score.poster_score}</div>
                <div className="text-gray-500">房源</div>
                <div className="font-semibold text-emerald-600 text-right">{score.listing_score}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 图片栅格 */}
      {listing.image_urls?.length > 0 && (
        <div className="card p-4">
          {heroImg && (
            <div className="mb-3 rounded-xl overflow-hidden bg-gray-100 max-h-[480px]">
              <img src={heroImg} alt="" className="w-full object-cover max-h-[480px]" />
            </div>
          )}
          {listing.image_urls.length > 1 && (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {listing.image_urls.slice(1).map((url, idx) => (
                <a key={idx} href={url} target="_blank" rel="noreferrer" className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
                  <img src={url} alt="" className="w-full h-full object-cover hover:scale-105 transition-transform" />
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 切换 */}
      <div className="flex gap-1 border-b">
        <button
          onClick={() => setTab("insights")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "insights" ? "border-brand-500 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          ✨ AI 深度洞察
        </button>
        <button
          onClick={() => setTab("score")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "score" ? "border-brand-500 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          📊 评分雷达
        </button>
        <button
          onClick={() => setTab("original")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === "original" ? "border-brand-500 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          📄 原帖
        </button>
      </div>

      {/* Tab 内容 */}
      {tab === "insights" && (
        <InsightsCard
          insights={score?.ai_insights as InsightsResult | null}
          loading={aiLoading}
          onRefresh={hasInsights ? undefined : onInsights}
        />
      )}

      {tab === "score" && score && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="card p-5">
            <h3 className="font-semibold text-gray-800 mb-2 text-center">8 维度雷达图</h3>
            <ScoreRadar score={score} />
          </div>
          <ScorePanel score={score} />
        </div>
      )}

      {tab === "original" && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3">原帖内容</h3>
          <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-4 rounded-lg leading-relaxed">
            {listing.content}
          </pre>

          {listing.contact_info && Object.keys(listing.contact_info).length > 0 && (
            <div className="mt-4 text-sm">
              <span className="text-gray-500">联系方式：</span>
              {listing.contact_info.wechat && (
                <span className="ml-2">微信 {listing.contact_info.wechat}</span>
              )}
              {listing.contact_info.phone && (
                <span className="ml-2">电话 {listing.contact_info.phone}</span>
              )}
            </div>
          )}

          {score?.evidence?.description_quality?.hit_keywords && score.evidence.description_quality.hit_keywords.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">原文关键信息</h4>
              <div className="flex flex-wrap gap-1">
                {score.evidence.description_quality.hit_keywords.map((k: string) => (
                  <span key={k} className="badge bg-blue-50 text-blue-700">{k}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 操作面板 */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="card p-4 space-y-2">
          <div className="text-sm font-medium text-gray-700 mb-1">收藏到</div>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => onFav("待看")} className="btn-secondary text-sm">待看</button>
            <button onClick={() => onFav("看过")} className="btn-secondary text-sm">看过</button>
            <button onClick={() => onFav("不考虑")} className="btn-secondary text-sm">不考虑</button>
            <button onClick={() => onFav("已租")} className="btn-secondary text-sm">已租</button>
          </div>
        </div>

        <div className="card p-4 space-y-2">
          <div className="text-sm font-medium text-gray-700 mb-1">标记反馈</div>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => onMark("agent")} className="btn-secondary text-sm">标记中介</button>
            <button onClick={() => onMark("fake")} className="btn-secondary text-sm">疑似虚假</button>
            <button onClick={() => onMark("noisy")} className="btn-secondary text-sm">环境吵</button>
            <button onClick={() => onMark("quiet")} className="btn-secondary text-sm">环境安静</button>
          </div>
        </div>

        <div className="card p-4 flex flex-col gap-2 justify-center">
          <button onClick={onInsights} disabled={aiLoading} className="btn-primary">
            {aiLoading ? "AI 分析中..." : "✨ 重新生成 AI 洞察"}
          </button>
          <button onClick={() => scoreApi.recalc(id!).then(() => load())} className="btn-ghost text-sm">
            🔄 重新评分（规则）
          </button>
        </div>
      </div>
    </div>
  );
}
