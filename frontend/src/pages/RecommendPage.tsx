import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { profileApi, recommendApi } from "../services/api";
import type { Listing, Profile } from "../types";
import ListingCard from "../components/ListingCard";

export default function RecommendPage() {
  const [params, setParams] = useSearchParams();
  const profileId = params.get("profile");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    profileApi.list().then(setProfiles);
  }, []);

  useEffect(() => {
    if (!profileId && profiles.length > 0) {
      setParams({ profile: profiles[0].id });
      return;
    }
    if (!profileId) return;
    setLoading(true);
    recommendApi
      .recommend(profileId, 1, 30)
      .then((data) => setListings(data.items))
      .finally(() => setLoading(false));
  }, [profileId, profiles]);

  const selectedProfile = profiles.find((p) => p.id === profileId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-2xl font-bold text-gray-800">为你推荐</h1>
        <div className="flex items-center gap-2">
          <select
            className="input w-auto"
            value={profileId || ""}
            onChange={(e) => setParams({ profile: e.target.value })}
          >
            {profiles.length === 0 && <option value="">（无画像）</option>}
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <Link to="/profiles/new" className="btn-secondary text-sm">+ 新建画像</Link>
        </div>
      </div>

      {selectedProfile && (
        <div className="card p-4 text-sm text-gray-600">
          <div className="flex flex-wrap gap-4">
            <span>预算 ¥{selectedProfile.budget_min}-{selectedProfile.budget_max}/月</span>
            <span>区域：{selectedProfile.areas?.join("、") || "不限"}</span>
            <span>户型：{selectedProfile.layouts?.join("、") || "不限"}</span>
            {selectedProfile.commute?.length > 0 && (
              <span>
                通勤：{selectedProfile.commute.map((c) => `${c.location}≤${c.max_time}min`).join("，")}
              </span>
            )}
          </div>
        </div>
      )}

      {!profileId ? (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-3">🎯</div>
          <p className="text-gray-600 mb-4">先创建需求画像，再获取个性化推荐</p>
          <Link to="/profiles/new" className="btn-primary">创建画像</Link>
        </div>
      ) : loading ? (
        <div className="text-center py-12 text-gray-400">推荐计算中...</div>
      ) : listings.length === 0 ? (
        <div className="card p-12 text-center text-gray-400">
          暂无匹配房源，稍后再来看看
        </div>
      ) : (
        <>
          <div className="text-sm text-gray-500">基于「个性化推荐分 = 好房指数*0.6 + 匹配度*0.4」排序</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {listings.map((l) => (
              <ListingCard key={l.id} listing={l} matchScore={l.match_score} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
