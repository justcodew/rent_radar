import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import dayjs from "dayjs";
import { profileApi } from "../services/api";
import type { Profile } from "../types";
import { useUIStore } from "../stores/ui";

const BEIJING_AREAS = [
  "朝阳区", "海淀区", "东城区", "西城区", "丰台区",
  "石景山区", "通州区", "大兴区", "昌平区", "顺义区", "房山区",
];

const LAYOUTS = ["开间", "一室一厅", "两室一厅", "两室两厅", "三室+"];

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const showToast = useUIStore((s) => s.showToast);

  const load = () => {
    setLoading(true);
    profileApi.list().then(setProfiles).finally(() => setLoading(false));
  };

  useEffect(() => load, []);

  const onDelete = async (id: string) => {
    if (!confirm("确认删除该画像？")) return;
    try {
      await profileApi.delete(id);
      showToast("已删除");
      load();
    } catch (e: any) {
      showToast(e.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">我的需求画像</h1>
        <Link to="/profiles/new" className="btn-primary">
          + 新建画像
        </Link>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">加载中...</div>
      ) : profiles.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="text-5xl mb-3">🎯</div>
          <h3 className="font-semibold text-gray-700 mb-1">还没有需求画像</h3>
          <p className="text-gray-500 text-sm mb-4">
            创建一个画像，系统会基于你的需求推荐匹配度更高的房源
          </p>
          <Link to="/profiles/new" className="btn-primary">立即创建</Link>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {profiles.map((p) => (
            <div key={p.id} className="card p-5">
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-gray-800">{p.name}</h3>
                <span className="badge bg-green-100 text-green-700">{p.status}</span>
              </div>
              <div className="mt-3 space-y-1 text-sm text-gray-600">
                <div>
                  预算 <span className="font-semibold text-brand-600">¥{p.budget_min}-{p.budget_max}</span> /月
                </div>
                <div>区域：{p.areas?.length ? p.areas.join("、") : "不限"}</div>
                <div>户型：{p.layouts?.length ? p.layouts.join("、") : "不限"}</div>
                {p.commute?.length > 0 && (
                  <div>
                    通勤：{p.commute.map((c) => `${c.location} ≤${c.max_time}分钟`).join("，")}
                  </div>
                )}
              </div>
              <div className="mt-3 text-xs text-gray-400">
                创建于 {dayjs(p.created_at).format("YYYY-MM-DD HH:mm")}
              </div>
              <div className="mt-4 flex gap-2">
                <Link to={`/profiles/${p.id}/edit`} className="btn-secondary text-sm flex-1">编辑</Link>
                <Link to={`/recommend?profile=${p.id}`} className="btn-primary text-sm flex-1">看推荐</Link>
                <button onClick={() => onDelete(p.id)} className="btn-ghost text-sm text-red-500">删除</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
