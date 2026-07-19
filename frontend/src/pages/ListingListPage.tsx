import { useEffect, useState } from "react";
import { listingApi } from "../services/api";
import type { Listing } from "../types";
import ListingCard from "../components/ListingCard";

export default function ListingListPage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [jumpInput, setJumpInput] = useState("");
  const pageSize = 24;

  const load = (p: number) => {
    setLoading(true);
    setPage(p);
    listingApi
      .list({ page: p, page_size: pageSize })
      .then((data) => {
        setListings(data.items);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => load(1), []);
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">全部房源</h1>
      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : listings.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">暂无数据</div>
      ) : (
        <>
          <div className="text-sm text-gray-500 mb-3">共 {total} 条</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {listings.map((l) => (
              <ListingCard key={l.id} listing={l} />
            ))}
          </div>
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-8">
              <button
                onClick={() => load(page - 1)}
                disabled={page <= 1}
                className="btn-secondary"
              >
                上一页
              </button>
              <span className="px-4 py-2 text-sm text-gray-600">
                第 {page} / {totalPages} 页
              </span>
              <button
                onClick={() => load(page + 1)}
                disabled={page >= totalPages}
                className="btn-secondary"
              >
                下一页
              </button>
              <span className="mx-2 text-sm text-gray-500">| 跳到</span>
              <input
                type="number"
                min={1}
                max={totalPages}
                value={jumpInput}
                onChange={(e) => setJumpInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    const p = parseInt(jumpInput, 10);
                    if (!isNaN(p) && p >= 1 && p <= totalPages) load(p);
                  }
                }}
                className="w-16 border rounded px-2 py-1 text-sm text-center"
                placeholder={String(page)}
              />
              <span className="text-sm text-gray-500">页</span>
              <button
                onClick={() => {
                  const p = parseInt(jumpInput, 10);
                  if (!isNaN(p) && p >= 1 && p <= totalPages) load(p);
                }}
                disabled={!jumpInput || parseInt(jumpInput, 10) === page}
                className="btn-secondary text-sm"
              >
                Go
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
