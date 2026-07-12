import { FormEvent, useEffect, useState } from "react";
import { searchApi } from "../services/api";
import type { Listing } from "../types";
import ListingCard from "../components/ListingCard";

const AREAS = ["朝阳区","海淀区","东城区","西城区","丰台区","石景山区","通州区","大兴区","昌平区","顺义区","房山区"];
const LAYOUTS = ["开间","一室一厅","两室一厅","两室两厅","三室+"];

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState({
    area: [] as string[],
    layout: [] as string[],
    price_min: undefined as number | undefined,
    price_max: undefined as number | undefined,
    min_score: undefined as number | undefined,
    posted_within_days: undefined as number | undefined,
  });
  const [sort, setSort] = useState("default");
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const toggle = (key: "area" | "layout", val: string) => {
    setFilters((p) => {
      const arr = p[key];
      return { ...p, [key]: arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val] };
    });
  };

  const onSearch = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    try {
      const params: Record<string, any> = { sort, page: 1, page_size: 30 };
      if (q.trim()) params.q = q.trim();
      if (filters.area.length) params.area = filters.area;
      if (filters.layout.length) params.layout = filters.layout;
      if (filters.price_min != null) params.price_min = filters.price_min;
      if (filters.price_max != null) params.price_max = filters.price_max;
      if (filters.min_score != null) params.min_score = filters.min_score;
      if (filters.posted_within_days != null) params.posted_within_days = filters.posted_within_days;
      const data = await searchApi.search(params);
      setResults(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    onSearch();
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-800">搜索房源</h1>

      <form onSubmit={onSearch} className="card p-4 space-y-3">
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="试试：朝阳区一居室 2500 以内 近地铁"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <select className="input w-32" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="default">综合</option>
            <option value="score">评分优先</option>
            <option value="price_asc">价格↑</option>
            <option value="price_desc">价格↓</option>
            <option value="newest">最新</option>
          </select>
          <button type="button" onClick={() => setShowFilters(!showFilters)} className="btn-secondary">
            筛选
          </button>
          <button type="submit" className="btn-primary">搜索</button>
        </div>

        {showFilters && (
          <div className="border-t pt-3 space-y-3">
            <div>
              <div className="text-sm text-gray-600 mb-1">区域</div>
              <div className="flex flex-wrap gap-1">
                {AREAS.map((a) => (
                  <button
                    type="button"
                    key={a}
                    onClick={() => toggle("area", a)}
                    className={`px-2 py-0.5 rounded-full text-xs ${
                      filters.area.includes(a) ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {a}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">户型</div>
              <div className="flex flex-wrap gap-1">
                {LAYOUTS.map((a) => (
                  <button
                    type="button"
                    key={a}
                    onClick={() => toggle("layout", a)}
                    className={`px-2 py-0.5 rounded-full text-xs ${
                      filters.layout.includes(a) ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {a}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-gray-500">最低价格</label>
                <input
                  type="number"
                  className="input"
                  value={filters.price_min ?? ""}
                  onChange={(e) => setFilters((p) => ({ ...p, price_min: e.target.value ? +e.target.value : undefined }))}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">最高价格</label>
                <input
                  type="number"
                  className="input"
                  value={filters.price_max ?? ""}
                  onChange={(e) => setFilters((p) => ({ ...p, price_max: e.target.value ? +e.target.value : undefined }))}
                />
              </div>
              <div>
                <label className="text-xs text-gray-500">最低评分</label>
                <input
                  type="number"
                  className="input"
                  value={filters.min_score ?? ""}
                  onChange={(e) => setFilters((p) => ({ ...p, min_score: e.target.value ? +e.target.value : undefined }))}
                />
              </div>
            </div>
          </div>
        )}
      </form>

      <div className="text-sm text-gray-500">共 {total} 条结果</div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">搜索中...</div>
      ) : results.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">没有找到匹配的房源</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {results.map((l) => (
            <ListingCard key={l.id} listing={l} />
          ))}
        </div>
      )}
    </div>
  );
}
