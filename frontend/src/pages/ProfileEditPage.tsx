import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { profileApi } from "../services/api";
import type { Profile, CommuteItem } from "../types";
import { useUIStore } from "../stores/ui";

const BEIJING_AREAS = ["朝阳区","海淀区","东城区","西城区","丰台区","石景山区","通州区","大兴区","昌平区","顺义区","房山区"];
const LAYOUTS = ["开间","一室一厅","两室一厅","两室两厅","三室+"];
const ENV_KEYS = [
  { k: "quiet_required", label: "必须安静" },
  { k: "lighting_required", label: "采光要好" },
  { k: "no_handshake", label: "不能握手楼" },
  { k: "no_new_renovation", label: "不能新装修" },
];
const TEMPLATES = [
  { name: "打工人", desc: "通勤优先，预算有限", data: { budget_min: 1500, budget_max: 3000, layouts: ["一室一厅"], environment: { quiet_required: true, lighting_required: true } } },
  { name: "双人合租", desc: "平衡两个上班地点", data: { budget_min: 3000, budget_max: 5000, layouts: ["两室一厅"], occupants: 2 } },
  { name: "养宠人群", desc: "可养宠，环境好", data: { keywords: { must_have: ["可养宠"] }, environment: { lighting_required: true } } },
];

export default function ProfileEditPage() {
  const { id } = useParams();
  const isEdit = !!id;
  const navigate = useNavigate();
  const showToast = useUIStore((s) => s.showToast);

  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<Partial<Profile>>({
    name: "我的找房需求",
    city: "北京",
    budget_min: 1500,
    budget_max: 3500,
    occupants: 1,
    areas: [],
    layouts: [],
    size_range: [10, 30],
    commute: [],
    environment: {},
    keywords: { must_have: [], exclude: [] },
    preferences: {},
  });
  // 新增通勤项的临时输入
  const [commuteDraft, setCommuteDraft] = useState<CommuteItem>({
    location: "", max_time: 45, mode: "transit", weight: 1,
  });

  useEffect(() => {
    if (id) {
      profileApi.get(id).then((p) => {
        setForm(p);
      });
    }
  }, [id]);

  const set = (k: string, v: any) => setForm((p) => ({ ...p, [k]: v }));

  const applyTemplate = (tpl: any) => {
    setForm((p) => ({ ...p, ...tpl.data, name: `${tpl.name}·需求` }));
    showToast(`已应用「${tpl.name}」模板`);
  };

  const toggleInArray = (key: "areas" | "layouts", val: string) => {
    const arr = (form[key] as string[]) || [];
    set(key, arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val]);
  };

  const addCommute = () => {
    if (!commuteDraft.location.trim()) return;
    set("commute", [...(form.commute || []), { ...commuteDraft }]);
    setCommuteDraft({ location: "", max_time: 45, mode: "transit", weight: 1 });
  };

  const removeCommute = (idx: number) => {
    set("commute", (form.commute || []).filter((_, i) => i !== idx));
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isEdit) {
        await profileApi.update(id!, form);
        showToast("已更新");
      } else {
        await profileApi.create(form);
        showToast("画像创建成功");
      }
      navigate("/profiles");
    } catch (err: any) {
      showToast(err.message || "保存失败");
    } finally {
      setLoading(false);
    }
  };

  const steps = ["模板", "基础", "通勤", "房源", "环境"];

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">
        {isEdit ? "编辑画像" : "新建画像"}
      </h1>

      {/* 步骤指示 */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto">
        {steps.map((label, i) => (
          <button
            key={label}
            onClick={() => setStep(i)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap ${
              step === i ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-600"
            }`}
          >
            <span className="w-5 h-5 rounded-full bg-white/40 text-xs flex items-center justify-center">
              {i + 1}
            </span>
            {label}
          </button>
        ))}
      </div>

      <form onSubmit={onSubmit} className="card p-6 space-y-5">
        {step === 0 && (
          <>
            <h2 className="font-semibold text-gray-700">选择模板（可选）</h2>
            <div className="grid sm:grid-cols-3 gap-3">
              {TEMPLATES.map((t) => (
                <button
                  type="button"
                  key={t.name}
                  onClick={() => applyTemplate(t)}
                  className="card hover:border-brand-300 hover:shadow-md p-4 text-left"
                >
                  <div className="font-semibold text-gray-800">{t.name}</div>
                  <div className="text-xs text-gray-500 mt-1">{t.desc}</div>
                </button>
              ))}
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">画像名称</label>
              <input
                className="input"
                value={form.name || ""}
                onChange={(e) => set("name", e.target.value)}
                required
              />
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <h2 className="font-semibold text-gray-700">基础约束</h2>
            <div>
              <label className="block text-sm text-gray-600 mb-1">预算范围（元/月）</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  className="input"
                  value={form.budget_min}
                  onChange={(e) => set("budget_min", +e.target.value)}
                />
                <span className="text-gray-400">~</span>
                <input
                  type="number"
                  className="input"
                  value={form.budget_max}
                  onChange={(e) => set("budget_max", +e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">居住人数</label>
              <input
                type="number"
                min={1}
                max={10}
                className="input"
                value={form.occupants}
                onChange={(e) => set("occupants", +e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">入住时间</label>
              <input
                className="input"
                value={form.move_in || ""}
                onChange={(e) => set("move_in", e.target.value)}
                placeholder="如：2026-08-01 / 随时"
              />
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h2 className="font-semibold text-gray-700">通勤需求</h2>
            <p className="text-xs text-gray-500">支持多人通勤（如双人合租），每个地点可设置不同时间上限和权重</p>
            {(form.commute || []).map((c, idx) => (
              <div key={idx} className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg">
                <span className="flex-1 text-sm">📍 {c.location}</span>
                <span className="text-sm text-gray-500">≤{c.max_time}分钟</span>
                <button type="button" onClick={() => removeCommute(idx)} className="text-red-400 text-xs">移除</button>
              </div>
            ))}
            <div className="border-t pt-3 mt-3">
              <div className="grid sm:grid-cols-2 gap-2">
                <input
                  className="input"
                  placeholder="上班地点（如 国贸 / 中关村）"
                  value={commuteDraft.location}
                  onChange={(e) => setCommuteDraft({ ...commuteDraft, location: e.target.value })}
                />
                <div className="flex gap-2">
                  <input
                    type="number"
                    className="input"
                    placeholder="分钟"
                    value={commuteDraft.max_time}
                    onChange={(e) => setCommuteDraft({ ...commuteDraft, max_time: +e.target.value })}
                  />
                  <button type="button" onClick={addCommute} className="btn-secondary">添加</button>
                </div>
              </div>
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h2 className="font-semibold text-gray-700">房源要求</h2>
            <div>
              <label className="block text-sm text-gray-600 mb-2">倾向区域（多选）</label>
              <div className="flex flex-wrap gap-2">
                {BEIJING_AREAS.map((a) => {
                  const active = (form.areas || []).includes(a);
                  return (
                    <button
                      type="button"
                      key={a}
                      onClick={() => toggleInArray("areas", a)}
                      className={`px-3 py-1 rounded-full text-sm ${
                        active ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {a}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-2">户型（多选）</label>
              <div className="flex flex-wrap gap-2">
                {LAYOUTS.map((a) => {
                  const active = (form.layouts || []).includes(a);
                  return (
                    <button
                      type="button"
                      key={a}
                      onClick={() => toggleInArray("layouts", a)}
                      className={`px-3 py-1 rounded-full text-sm ${
                        active ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                    >
                      {a}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">租住方式</label>
              <div className="flex gap-2">
                {["整租", "合租"].map((r) => (
                  <button
                    type="button"
                    key={r}
                    onClick={() => set("rent_type", r)}
                    className={`px-3 py-1 rounded-full text-sm ${
                      form.rent_type === r ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {step === 4 && (
          <>
            <h2 className="font-semibold text-gray-700">环境偏好</h2>
            <div className="space-y-2">
              {ENV_KEYS.map(({ k, label }) => (
                <label key={k} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={!!(form.environment as any)?.[k]}
                    onChange={(e) =>
                      set("environment", { ...(form.environment || {}), [k]: e.target.checked })
                    }
                  />
                  <span className="text-sm">{label}</span>
                </label>
              ))}
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">关键词 - 必须有（逗号分隔）</label>
              <input
                className="input"
                value={(form.keywords?.must_have || []).join("，")}
                onChange={(e) =>
                  set("keywords", {
                    ...form.keywords,
                    must_have: e.target.value ? e.target.value.split(/[，,]/).map((s) => s.trim()).filter(Boolean) : [],
                  })
                }
                placeholder="电梯，民水民电，阳台"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">关键词 - 不能有（逗号分隔）</label>
              <input
                className="input"
                value={(form.keywords?.exclude || []).join("，")}
                onChange={(e) =>
                  set("keywords", {
                    ...form.keywords,
                    exclude: e.target.value ? e.target.value.split(/[，,]/).map((s) => s.trim()).filter(Boolean) : [],
                  })
                }
                placeholder="隔断房，底楼"
              />
            </div>
          </>
        )}

        <div className="flex items-center justify-between border-t pt-4">
          <button
            type="button"
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="btn-ghost"
          >
            ← 上一步
          </button>
          <div className="flex gap-2">
            {step < steps.length - 1 ? (
              <button type="button" onClick={() => setStep(step + 1)} className="btn-primary">
                下一步 →
              </button>
            ) : (
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? "保存中..." : isEdit ? "保存修改" : "创建画像"}
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
