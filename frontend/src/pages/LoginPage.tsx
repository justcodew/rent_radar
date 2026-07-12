import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "../services/api";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";

export default function LoginPage() {
  const [account, setAccount] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const login = useAuthStore((s) => s.login);
  const showToast = useUIStore((s) => s.showToast);
  const navigate = useNavigate();

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await authApi.login({ account, password });
      login({ access_token: data.access_token, refresh_token: data.refresh_token }, data.user);
      showToast("登录成功");
      navigate("/");
    } catch (err: any) {
      showToast(err.message || "登录失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10">
      <div className="card p-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">登录</h1>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">手机号 / 邮箱</label>
            <input
              className="input"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              placeholder="输入手机号或邮箱"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">密码</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
              required
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "登录中..." : "登录"}
          </button>
        </form>
        <div className="mt-4 text-center text-sm text-gray-500">
          还没账号？{" "}
          <Link to="/register" className="text-brand-600 hover:underline">
            立即注册
          </Link>
        </div>
      </div>
    </div>
  );
}
