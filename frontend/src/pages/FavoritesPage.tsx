import { useEffect, useState } from "react";
import { favoriteApi } from "../services/api";
import type { Listing } from "../types";
import ListingCard from "../components/ListingCard";
import clsx from "clsx";

const CATEGORIES = ["待看", "看过", "不考虑", "已租"];

export default function FavoritesPage() {
  const [category, setCategory] = useState<string>("");
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    favoriteApi
      .list(category || undefined)
      .then((data) => setListings(data.items))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(), [category]);

  const onRemove = async (id: string) => {
    try {
      await favoriteApi.remove(id);
      load();
    } catch (e) {
      // ignore
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-800">我的收藏</h1>

      <div className="flex gap-2">
        <button
          onClick={() => setCategory("")}
          className={clsx(
            "px-3 py-1 rounded-full text-sm",
            !category ? "bg-brand-500 text-white" : "bg-white text-gray-600 border"
          )}
        >
          全部
        </button>
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setCategory(c)}
            className={clsx(
              "px-3 py-1 rounded-full text-sm",
              category === c ? "bg-brand-500 text-white" : "bg-white text-gray-600 border"
            )}
          >
            {c}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : listings.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">还没有收藏任何房源</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {listings.map((l) => (
            <div key={l.id} className="relative">
              <ListingCard listing={l} />
              {l.favorite_category && (
                <div className="absolute top-2 right-2 z-10">
                  <span className="badge bg-brand-500 text-white">{l.favorite_category}</span>
                </div>
              )}
              <button
                onClick={() => onRemove(l.id)}
                className="absolute bottom-2 right-2 z-10 bg-white/95 px-2 py-0.5 rounded text-xs text-red-500"
              >
                移除
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
