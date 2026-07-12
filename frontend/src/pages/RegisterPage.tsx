import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../services/api";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";

export default function RegisterPage() {
  const [form, setForm] = useState({
    phone: "",
    email: "",
    nickname: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const showToast = useUIStore((s) => s.showToast);
  const navigate = useNavigate();

  const set = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.phone && !form.email) {
      showToast("手机号或邮箱至少填写一项");
      return;
    }
    setLoading(true);
    try {
      const payload = { ...form };
      if (!payload.phone) delete (payload as any).phone;
      if (!payload.email) delete (payload as any).email;
      if (!payload.nickname) delete (payload as any).nickname;
      const data = await authApi.register(payload as any);
      login({ access_token: data.access_token, refresh_token: data.refresh_token }, data.user);
      showToast("注册成功");
      navigate("/");
    } catch (err: any) {
      showToast(err.message || "注册失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10">
      <div className="card p-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">注册</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">手机号（可选）</label>
            <input
              className="input"
              value={form.phone}
              onChange={(e) => set("phone", e.target.value)}
              placeholder="13812345678"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">邮箱（可选）</label>
            <input
              className="input"
              value={form.email}
              onChange={(e) => set("email", e.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">昵称（可选）</label>
            <input
              className="input"
              value={form.nickname}
              onChange={(e) => set("nickname", e.target.value)}
              placeholder="好房用户"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">密码</label>
            <input
              type="password"
              className="input"
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
              placeholder="至少 6 位"
              minLength={6}
              required
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "注册中..." : "注册"}
          </button>
        </form>
        <div className="mt-4 text-center text-sm text-gray-500">
          已有账号？{" "}
          <Link to="/login" className="text-brand-600 hover:underline">
            直接登录
          </Link>
        </div>
      </div>
    </div>
  );
}
