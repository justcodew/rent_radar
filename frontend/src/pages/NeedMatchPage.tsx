import { useState } from "react";
import { Link } from "react-router-dom";
import { insightsApi } from "../services/api";
import type { NeedMatchResult, ExtractedNeed, CommunityRecommendation } from "../types";
import ListingCard from "../components/ListingCard";
import { useUIStore } from "../stores/ui";

const EXAMPLES = [
  "我在珠江新城上班，预算 4000 左右，希望地铁 30 分钟内，要一室一厅带电梯，民水民电，不要中介",
  "暨大学生，预算 2500，希望走路 15 分钟到学校，可以接受合租但要独立卫浴",
  "天河公园附近上班，两个人合租预算 6000 内，两室一厅，希望小区环境好有绿化",
  "琶洲上班，预算 5000，希望 3 号线或 8 号线通勤 25 分钟内，朝南，押一付一",
];

export default function NeedMatchPage() {
  const [description, setDescription] = useState("");
  const [city, setCity] = useState("广州");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<NeedMatchResult | null>(null);
  const showToast = useUIStore((s) => s.showToast);

  const submit = async (force = false) => {
    if (description.trim().length < 5) {
      showToast("描述太短了，再详细一点");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const r = await insightsApi.match({
        description: description.trim(),
        city,
        force,
      });
      setResult(r as NeedMatchResult);
      if (r.skipped) showToast(`AI 暂不可用：${r.reason}`);
    } catch (e: any) {
      showToast(e.message || "请求失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-indigo-500 via-brand-500 to-orange-500 p-6 text-white shadow-lg">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          🎯 AI 选房
        </h1>
        <p className="mt-2 text-sm opacity-95 max-w-2xl">
          用一句话描述你的需求，AI 帮你提取关键参数、推荐 3-5 个匹配小区，
          并从数据库里挑出现有可用房源。比规则搜索更聪明，比中介更懂你。
        </p>
      </div>

      {/* 输入区 */}
      <div className="card p-5 space-y-4">
        <div className="flex gap-3 items-start">
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="input max-w-[120px]"
          >
            <option value="广州">广州</option>
            <option value="北京">北京</option>
            <option value="上海">上海</option>
            <option value="深圳">深圳</option>
            <option value="杭州">杭州</option>
          </select>
          <div className="flex-1" />
        </div>

        <textarea
          className="input min-h-[110px] text-base"
          placeholder="比如：我在珠江新城上班，预算 4000，希望地铁 30 分钟内，要一室一厅带电梯，民水民电，不要中介不要合租"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-gray-500 self-center mr-1">示例：</span>
          {EXAMPLES.map((ex, i) => (
            <button
              key={i}
              onClick={() => setDescription(ex)}
              className="text-xs px-2 py-1 bg-gray-100 hover:bg-brand-50 hover:text-brand-600 rounded-full text-gray-600 transition-colors max-w-xs truncate"
              title={ex}
            >
              {ex.slice(0, 18)}…
            </button>
          ))}
        </div>

        <div className="flex gap-2 pt-1">
          <button
            onClick={() => submit(false)}
            disabled={loading}
            className="btn-primary flex-1"
          >
            {loading ? "🤔 AI 正在帮你找..." : "✨ 开始匹配"}
          </button>
          {result && !result.skipped && (
            <button
              onClick={() => submit(true)}
              disabled={loading}
              className="btn-secondary"
              title="忽略缓存重新生成"
            >
              🔄 强制刷新
            </button>
          )}
        </div>
      </div>

      {/* 结果 */}
      {result && !result.skipped && (
        <>
          {/* 用户画像 + 提取的需求 */}
          {result.extracted && (
            <ExtractedNeedCard extracted={result.extracted} />
          )}

          {/* AI 推荐的小区 */}
          {result.communities && result.communities.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">🏘️</span>
                <h2 className="font-semibold text-gray-800">AI 推荐小区</h2>
                <span className="text-xs text-gray-400">
                  · 针对你的需求，差异化推荐
                </span>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                {result.communities.map((c, i) => (
                  <CommunityCard key={i} index={i} community={c} />
                ))}
              </div>
            </div>
          )}

          {/* 实际匹配的房源 */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-xl">📋</span>
              <h2 className="font-semibold text-gray-800">数据库匹配房源</h2>
              <span className="text-xs text-gray-400">
                · {result.listings?.length || 0} 套实时匹配
              </span>
            </div>
            {result.listings && result.listings.length > 0 ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {result.listings.map((l) => (
                  <ListingCard key={l.id} listing={l} />
                ))}
              </div>
            ) : (
              <div className="card p-6 text-center text-gray-500">
                <div className="text-3xl mb-2">🔍</div>
                <div className="font-medium mb-1">数据库里暂无完全匹配的房源</div>
                <div className="text-sm text-gray-400">
                  抓取周期内的帖子没覆盖到，可以参考上面 AI 推荐的小区去豆瓣/小红书搜
                </div>
              </div>
            )}
          </div>

          <div className="text-xs text-gray-400 text-center">
            {result.from_cache ? "（结果来自缓存）" : ""}
            {result.model && `模型：${result.model}`}
            {result.analyzed_at &&
              ` · ${new Date(result.analyzed_at).toLocaleString("zh-CN")}`}
          </div>
        </>
      )}

      {result?.skipped && (
        <div className="card p-6 text-center text-gray-500">
          <div className="text-3xl mb-2">😴</div>
          <div className="font-medium mb-1">AI 暂时不可用</div>
          <div className="text-sm">{result.reason}</div>
        </div>
      )}

      {!result && !loading && (
        <div className="card p-8 text-center text-gray-400">
          <div className="text-4xl mb-3">💬</div>
          <div className="font-medium text-gray-500 mb-1">
            告诉 AI 你的真实需求
          </div>
          <div className="text-xs">
            上班地点 + 预算 + 户型 + 关键偏好，越具体推荐越准
          </div>
        </div>
      )}
    </div>
  );
}

function ExtractedNeedCard({ extracted }: { extracted: ExtractedNeed }) {
  const chips: { label: string; value?: string }[] = [];

  if (extracted.budget_min != null || extracted.budget_max != null) {
    const bmin = extracted.budget_min ?? "";
    const bmax = extracted.budget_max ?? "";
    chips.push({ label: "预算", value: `¥${bmin}-${bmax}/月` });
  }
  if (extracted.areas && extracted.areas.length > 0) {
    chips.push({ label: "区域", value: extracted.areas.join(" / ") });
  }
  if (extracted.layouts && extracted.layouts.length > 0) {
    chips.push({ label: "户型", value: extracted.layouts.join(" / ") });
  }
  if (extracted.size_min != null || extracted.size_max != null) {
    chips.push({
      label: "面积",
      value: `${extracted.size_min ?? ""}-${extracted.size_max ?? ""}㎡`,
    });
  }
  if (extracted.commute_target) {
    chips.push({
      label: "通勤",
      value: `${extracted.commute_target}${
        extracted.commute_max_min ? ` ${extracted.commute_max_min}min` : ""
      }${extracted.commute_mode ? ` (${extracted.commute_mode})` : ""}`,
    });
  }
  if (extracted.must_have && extracted.must_have.length > 0) {
    chips.push({ label: "必备", value: extracted.must_have.join(" / ") });
  }
  if (extracted.exclude && extracted.exclude.length > 0) {
    chips.push({ label: "排除", value: extracted.exclude.join(" / ") });
  }

  return (
    <div className="card p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">🧠</span>
        <h3 className="font-semibold text-gray-800">AI 读懂的需求</h3>
        {extracted.lifestyle && (
          <span className="ml-auto text-xs text-gray-500 italic max-w-md truncate">
            「{extracted.lifestyle}」
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {chips.map((c, i) => (
          <div
            key={i}
            className="px-3 py-1 bg-brand-50 text-brand-700 rounded-full text-sm"
          >
            <span className="text-brand-400 mr-1 text-xs">{c.label}</span>
            {c.value}
          </div>
        ))}
      </div>
    </div>
  );
}

function CommunityCard({
  index,
  community,
}: {
  index: number;
  community: CommunityRecommendation;
}) {
  const colors = [
    "border-l-brand-500",
    "border-l-emerald-500",
    "border-l-indigo-500",
    "border-l-amber-500",
    "border-l-rose-500",
  ];
  const color = colors[index % colors.length];

  return (
    <div className={`card p-5 border-l-4 ${color}`}>
      <div className="flex items-start justify-between mb-1">
        <h4 className="font-semibold text-gray-900">{community.name}</h4>
        {community.area && (
          <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full shrink-0 ml-2">
            {community.area}
          </span>
        )}
      </div>
      {community.est_price_range && (
        <div className="text-xs text-brand-600 font-medium mb-2">
          💰 {community.est_price_range}
        </div>
      )}
      {community.reason && (
        <p className="text-sm text-gray-700 leading-relaxed mb-3">
          {community.reason}
        </p>
      )}
      {community.highlights && community.highlights.length > 0 && (
        <div className="mb-2">
          {community.highlights.map((h, i) => (
            <div key={i} className="text-xs text-emerald-700 flex gap-1">
              <span>✓</span>
              <span>{h}</span>
            </div>
          ))}
        </div>
      )}
      {community.watch_outs && community.watch_outs.length > 0 && (
        <div>
          {community.watch_outs.map((w, i) => (
            <div key={i} className="text-xs text-amber-700 flex gap-1">
              <span>!</span>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
