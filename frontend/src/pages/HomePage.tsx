import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listingApi } from "../services/api";
import type { Listing } from "../types";
import ListingCard from "../components/ListingCard";

export default function HomePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listingApi
      .list({ page: 1, page_size: 24 })
      .then((data) => setListings(data.items))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      {/* Hero */}
      <section className="card overflow-hidden">
        <div className="bg-gradient-to-r from-brand-500 to-brand-600 p-8 text-white">
          <h1 className="text-3xl font-bold mb-2">找房先看好房，少走弯路</h1>
          <p className="text-brand-50 opacity-90">
            聚合豆瓣等平台租房信息 · 多维度智能评估 · 帮你节省 90% 筛选时间
          </p>
          <div className="mt-4 flex gap-3">
            <Link to="/search" className="btn bg-white text-brand-600 hover:bg-brand-50">
              开始找房
            </Link>
            <Link to="/profiles/new" className="btn bg-brand-700 text-white hover:bg-brand-800">
              设置需求画像
            </Link>
          </div>
        </div>
      </section>

      {/* 好房信息流 */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-bold text-gray-800">今日好房</h2>
          <Link to="/listings" className="text-sm text-brand-600 hover:underline">
            查看全部 →
          </Link>
        </div>
        {loading ? (
          <div className="text-center py-12 text-gray-400">加载中...</div>
        ) : listings.length === 0 ? (
          <div className="card p-12 text-center text-gray-400">
            暂无房源数据。请先启动爬虫 worker 抓取数据。
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {listings.map((l) => (
              <ListingCard key={l.id} listing={l} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
