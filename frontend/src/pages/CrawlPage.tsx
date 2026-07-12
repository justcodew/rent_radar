import { useState } from "react";
import { crawlApi } from "../services/api";

export default function CrawlPage() {
  const [platform, setPlatform] = useState("xhs");
  const [keywords, setKeywords] = useState("广州越秀两房出租");
  const [maxCount, setMaxCount] = useState(20);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [listings, setListings] = useState<any[]>([]);
  const [ingestResult, setIngestResult] = useState<any>(null);

  const trigger = async () => {
    setLoading(true);
    try {
      const res = await crawlApi.trigger({ platform, keywords, max_count: maxCount });
      setResult(res);
    } catch (e: any) {
      setResult({ error: e?.message || "采集失败" });
    } finally {
      setLoading(false);
    }
  };

  const fetchListings = async () => {
    setLoading(true);
    try {
      const res = await crawlApi.listings({ platform, limit: 50, only_with_price: true });
      setListings(res.listings || []);
    } catch (e) {
      setListings([]);
    } finally {
      setLoading(false);
    }
  };

  const ingest = async () => {
    setLoading(true);
    try {
      const res = await crawlApi.ingest({ platform, limit: 100 });
      setIngestResult(res);
    } catch (e: any) {
      setIngestResult({ error: e?.message || "入库失败" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-4 space-y-6">
      <h1 className="text-2xl font-bold">采集控制台</h1>

      {/* 采集触发 */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <h2 className="text-lg font-semibold">触发采集</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm text-gray-500 mb-1">平台</label>
            <select value={platform} onChange={(e) => setPlatform(e.target.value)}
              className="border rounded px-3 py-2">
              <option value="xhs">小红书</option>
              <option value="douban">豆瓣</option>
              <option value="wb">微博</option>
            </select>
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm text-gray-500 mb-1">关键词</label>
            <input value={keywords} onChange={(e) => setKeywords(e.target.value)}
              className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm text-gray-500 mb-1">最大条数</label>
            <input type="number" value={maxCount} onChange={(e) => setMaxCount(Number(e.target.value))}
              className="border rounded px-3 py-2 w-20" />
          </div>
          <button onClick={trigger} disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
            {loading ? "采集中..." : "开始采集"}
          </button>
        </div>
        {result && (
          <div className="bg-gray-50 rounded p-3 text-sm">
            <pre className="whitespace-pre-wrap">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
      </div>

      {/* 已采集数据 */}
      <div className="bg-white rounded-lg shadow p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">已采集数据(有价格)</h2>
          <div className="flex gap-2">
            <button onClick={fetchListings} disabled={loading}
              className="border rounded px-4 py-1.5 text-sm hover:bg-gray-50">
              查看数据
            </button>
            <button onClick={ingest} disabled={loading}
              className="bg-green-600 text-white rounded px-4 py-1.5 text-sm hover:bg-green-700">
              入库+评分
            </button>
          </div>
        </div>
        {ingestResult && (
          <div className="bg-green-50 rounded p-3 text-sm">
            入库: {ingestResult.ingested || 0} 条, 跳过: {ingestResult.skipped || 0} 条
          </div>
        )}
        {listings.length > 0 && (
          <div className="space-y-2">
            {listings.map((l, i) => (
              <div key={i} className="border rounded p-3 flex justify-between items-center">
                <div>
                  <span className="font-medium">{l.title || "无标题"}</span>
                  <span className="text-gray-400 text-sm ml-2">{l.area_name || "未知区域"}</span>
                </div>
                <div className="text-right">
                  <span className="text-green-600 font-bold">{l.price ? `${l.price}元/月` : "价格未知"}</span>
                  <span className="text-gray-400 text-sm ml-2">{l.layout || ""}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
