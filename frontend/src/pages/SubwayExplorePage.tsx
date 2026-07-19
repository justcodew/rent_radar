import { useEffect, useMemo, useState } from "react";
import { subwayApi } from "../services/api";
import type { SubwayStation, SubwayExploreResult } from "../types/subway";
import SubwayDiagram from "../components/SubwayDiagram";
import ListingCard from "../components/ListingCard";

const RADIUS_PRESETS = [0.5, 1, 1.5, 2];

export default function SubwayExplorePage() {
  const [stationQuery, setStationQuery] = useState("公园前");
  const [selectedStation, setSelectedStation] = useState<SubwayStation | null>(null);
  const [suggestions, setSuggestions] = useState<SubwayStation[]>([]);
  const [showSug, setShowSug] = useState(false);
  const [radius, setRadius] = useState(1);
  const [result, setResult] = useState<SubwayExploreResult | null>(null);
  const [filterNoListing, setFilterNoListing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  // 自动补全
  useEffect(() => {
    const q = stationQuery.trim();
    if (!q) {
      setSuggestions([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const res = await subwayApi.stations(q);
        setSuggestions(res.stations);
      } catch {
        setSuggestions([]);
      }
    }, 200);
    return () => clearTimeout(t);
  }, [stationQuery]);

  // 触发探索
  const explore = async (stationName: string, radiusKm: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await subwayApi.explore(stationName, radiusKm);
      setResult(res);
      setSelectedStation(res.station);
      setExpanded(res.communities.find((c) => (c.listings_count ?? 0) > 0)?.name ?? null);
    } catch (e: any) {
      setError(e?.message || "查询失败");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  // 选中建议项
  const pickStation = (s: SubwayStation) => {
    setStationQuery(s.name);
    setSelectedStation(s);
    setShowSug(false);
    explore(s.name, radius);
  };

  // 半径变化时,如果已选站,自动重新查
  useEffect(() => {
    if (selectedStation) {
      explore(selectedStation.name, radius);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [radius]);

  const totalListings = useMemo(
    () => (result?.communities ?? []).reduce((s, c) => s + (c.listings_count ?? 0), 0),
    [result]
  );
  const visibleCommunities = useMemo(
    () => (result?.communities ?? []).filter((c) => !filterNoListing || (c.listings_count ?? 0) > 0),
    [result, filterNoListing]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 className="text-2xl font-bold text-gray-800">地铁找房</h1>
        {result && (
          <span className="text-sm text-gray-500">
            {result.station.name} · {radius}km 内 · 共 {totalListings} 套
          </span>
        )}
      </div>

      {/* 搜索 + 半径 */}
      <div className="card p-4 space-y-3">
        <div className="flex flex-wrap gap-4 items-end">
          <div className="relative flex-1 min-w-[200px]">
            <label className="block text-sm text-gray-500 mb-1">地铁站</label>
            <input
              value={stationQuery}
              onChange={(e) => {
                setStationQuery(e.target.value);
                setShowSug(true);
              }}
              onFocus={() => setShowSug(true)}
              onBlur={() => setTimeout(() => setShowSug(false), 150)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  const exact = suggestions.find((s) => s.name === stationQuery.trim());
                  if (exact) pickStation(exact);
                  else if (suggestions[0]) pickStation(suggestions[0]);
                }
              }}
              className="input w-full"
              placeholder="输入站名,如:公园前、体育西路"
            />
            {showSug && suggestions.length > 0 && (
              <div className="absolute z-10 mt-1 w-full bg-white border rounded shadow max-h-64 overflow-auto">
                {suggestions.map((s) => (
                  <button
                    key={s.name}
                    onClick={() => pickStation(s)}
                    className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b last:border-0 flex justify-between items-center"
                  >
                    <span className="font-medium">{s.name}</span>
                    <span className="text-xs text-gray-400">
                      {s.lines.map((l) => `${l}号线`).join(" · ")}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => {
              const q = stationQuery.trim();
              if (!q) return;
              const exact = suggestions.find((s) => s.name === q);
              if (exact) pickStation(exact);
              else if (suggestions[0]) pickStation(suggestions[0]);
              else explore(q, radius);
            }}
            disabled={loading || !stationQuery.trim()}
            className="btn-primary"
          >
            {loading ? "查询中…" : "搜索"}
          </button>
          <div>
            <label className="block text-sm text-gray-500 mb-1">
              半径:<span className="text-brand-600 font-bold">{radius} km</span>
            </label>
            <input
              type="range"
              min={0.5}
              max={2}
              step={0.5}
              value={radius}
              onChange={(e) => setRadius(Number(e.target.value))}
              className="w-48"
            />
          </div>
        </div>
        <div className="text-xs text-gray-400">
          小区数据来自 OpenStreetMap(免费),房源按小区名匹配标题/正文。
        </div>
        <div className="flex gap-2 flex-wrap">
          {RADIUS_PRESETS.map((r) => (
            <button
              key={r}
              onClick={() => setRadius(r)}
              className={`px-3 py-1 rounded-full text-xs ${
                radius === r
                  ? "bg-brand-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {r} km
            </button>
          ))}
        </div>
        {error && <div className="text-sm text-red-500">{error}</div>}
      </div>

      {/* 主体:SVG + 社区列表 */}
      {loading && !result ? (
        <div className="card p-12 text-center text-gray-400">
          正在从 OpenStreetMap 拉取附近小区数据,首次可能需要 10-30 秒…
        </div>
      ) : result ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SubwayDiagram
            station={result.station}
            radiusKm={result.radius_km}
            communities={result.communities}
            selectedName={expanded}
            onSelect={(name) => setExpanded(expanded === name ? null : name)}
          />

          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">
                共 {result.communities.length} 个小区 · {totalListings} 套匹配房源
              </span>
              <label className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filterNoListing}
                  onChange={(e) => setFilterNoListing(e.target.checked)}
                  className="w-3 h-3"
                />
                <span className="text-gray-500">只看有房源的</span>
              </label>
            </div>
            {visibleCommunities.length === 0 ? (
              <div className="card p-8 text-center text-gray-400">
                {result.communities.length === 0
                  ? `${radius}km 内未找到小区数据(OSM 数据可能缺失)`
                  : "无匹配,试试关闭过滤"}
              </div>
            ) : (
              visibleCommunities.map((c) => {
                const has = (c.listings_count ?? 0) > 0;
                return (
                  <div
                    key={c.name + c.lat}
                    className={`card overflow-hidden ${has ? "" : "opacity-60"}`}
                  >
                    <button
                      onClick={() => setExpanded(expanded === c.name ? null : c.name)}
                      className="w-full p-3 flex items-center justify-between hover:bg-gray-50 disabled:cursor-default"
                      disabled={!has}
                    >
                      <div className="text-left">
                        <div className="font-semibold text-gray-800 flex items-center gap-2">
                          <span>{c.name}</span>
                          {has && (
                            <span className="px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700">
                              {c.listings_count} 套
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          距 {result.station.name} {c.distance_km} km · 方位 {c.bearing_deg}°
                        </div>
                      </div>
                      {has && (
                        <span className="text-gray-400">
                          {expanded === c.name ? "▲" : "▼"}
                        </span>
                      )}
                    </button>
                    {expanded === c.name && c.sample_listings && (
                      <div className="border-t bg-gray-50 p-3">
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {c.sample_listings.map((l) => (
                            <ListingCard key={l.id} listing={l} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
