import { useState } from "react";
import { insightsApi } from "../services/api";
import type { InsightsResult } from "../types";
import InsightsCard from "../components/InsightsCard";
import { useUIStore } from "../stores/ui";

const EMPTY_FORM = {
  community_name: "",
  city: "广州",
  area_name: "",
  layout: "",
  price: "",
  size_sqm: "",
  floor_info: "",
  orientation: "",
  extra_note: "",
};

export default function CommunityEvalPage() {
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InsightsResult | null>(null);
  const [history, setHistory] = useState<string[]>([]);
  const showToast = useUIStore((s) => s.showToast);

  const set = (k: keyof typeof form, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  const submit = async (force = false) => {
    if (!form.community_name.trim()) {
      showToast("请至少输入小区名");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const payload: any = { community_name: form.community_name.trim(), force };
      // 只传非空字段
      if (form.city.trim()) payload.city = form.city.trim();
      for (const k of [
        "area_name",
        "layout",
        "floor_info",
        "orientation",
        "extra_note",
      ] as const) {
        if (form[k].trim()) payload[k] = form[k].trim();
      }
      const priceNum = parseInt(form.price, 10);
      if (!isNaN(priceNum) && priceNum > 0) payload.price = priceNum;
      const sizeNum = parseFloat(form.size_sqm);
      if (!isNaN(sizeNum) && sizeNum > 0) payload.size_sqm = sizeNum;

      const r = await insightsApi.community(payload);
      setResult(r as InsightsResult);
      if (r.skipped) {
        showToast(`AI 暂不可用：${r.reason}`);
      } else {
        setHistory((h) =>
          [form.community_name.trim(), ...h.filter((x) => x !== form.community_name.trim())].slice(0, 8)
        );
      }
    } catch (e: any) {
      showToast(e.message || "请求失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-brand-500 to-orange-600 p-6 text-white shadow-lg">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          🏘️ 小区测评
        </h1>
        <p className="mt-2 text-sm opacity-90 max-w-xl">
          只要知道小区名，AI 「老广」朋友帮你综合分析：小区画像、周边配套、优缺点、看房建议。
          信息越全，结论越准；信息越少，confidence 会如实降低。
        </p>
      </div>

      {/* 表单 */}
      <div className="card p-5 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            小区/地名 <span className="text-rose-500">*</span>
          </label>
          <input
            className="input"
            placeholder="如：华景新城 / 体育西华苑大厦 / 珠江新城某公寓"
            value={form.community_name}
            onChange={(e) => set("community_name", e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !loading) submit(false);
            }}
          />
        </div>

        <div className="grid sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">城市</label>
            <input
              className="input"
              value={form.city}
              onChange={(e) => set("city", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">区域</label>
            <input
              className="input"
              placeholder="如：天河区"
              value={form.area_name}
              onChange={(e) => set("area_name", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">户型</label>
            <input
              className="input"
              placeholder="如：一室一厅"
              value={form.layout}
              onChange={(e) => set("layout", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">月租金</label>
            <input
              className="input"
              type="number"
              placeholder="元"
              value={form.price}
              onChange={(e) => set("price", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">面积 (㎡)</label>
            <input
              className="input"
              type="number"
              value={form.size_sqm}
              onChange={(e) => set("size_sqm", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">楼层</label>
            <input
              className="input"
              placeholder="如：中层 / 6/9层"
              value={form.floor_info}
              onChange={(e) => set("floor_info", e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">朝向</label>
            <input
              className="input"
              placeholder="如：南向"
              value={form.orientation}
              onChange={(e) => set("orientation", e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">其他补充（可选）</label>
          <textarea
            className="input min-h-[60px]"
            placeholder="比如：靠近地铁站 / 民水民电 / 押一付一 / 任何你想让 AI 知道的"
            value={form.extra_note}
            onChange={(e) => set("extra_note", e.target.value)}
          />
        </div>

        <div className="flex gap-2 pt-1">
          <button
            onClick={() => submit(false)}
            disabled={loading}
            className="btn-primary flex-1"
          >
            {loading ? "🤔 老广正在打量..." : "✨ 生成综合测评"}
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

        {history.length > 0 && (
          <div className="flex flex-wrap items-center gap-1 pt-2 text-xs">
            <span className="text-gray-500">最近：</span>
            {history.map((name) => (
              <button
                key={name}
                onClick={() => {
                  setForm((f) => ({ ...EMPTY_FORM, community_name: name, city: f.city }));
                  setResult(null);
                }}
                className="badge bg-gray-100 text-gray-600 hover:bg-gray-200"
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 结果 */}
      {result && (
        <InsightsCard
          insights={result}
          loading={loading}
          onRefresh={() => submit(true)}
        />
      )}

      {!result && !loading && (
        <div className="card p-8 text-center text-gray-400">
          <div className="text-4xl mb-3">🎯</div>
          <div className="font-medium text-gray-500 mb-1">输入小区名，立即开始测评</div>
          <div className="text-xs">
            即使只有一个名字也能分析，AI 会用城市常识帮你补全
          </div>
        </div>
      )}
    </div>
  );
}
