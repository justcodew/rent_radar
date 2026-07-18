import { NavLink, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { useAuthStore } from "../stores/auth";
import { useUIStore } from "../stores/ui";

const NAV = [
  { to: "/", label: "首页", end: true },
  { to: "/search", label: "搜索" },
  { to: "/case", label: "案例" },
  { to: "/crawl", label: "采集" },
  { to: "/ai-match", label: "AI 选房" },
  { to: "/community-eval", label: "小区测评" },
  { to: "/recommend", label: "推荐" },
  { to: "/profiles", label: "需求画像" },
  { to: "/favorites", label: "收藏" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuthStore();
  const showToast = useUIStore((s) => s.showToast);
  const navigate = useNavigate();

  const onLogout = () => {
    logout();
    showToast("已退出登录");
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <NavLink to="/" className="flex items-center gap-2">
              <span className="text-2xl">🏠</span>
              <span className="font-bold text-lg text-gray-800">好房雷达</span>
            </NavLink>
            <nav className="hidden md:flex items-center gap-1">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    clsx(
                      "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
                      isActive ? "bg-brand-50 text-brand-600" : "text-gray-600 hover:bg-gray-100"
                    )
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="text-sm text-gray-600 hidden sm:inline">
                  {user.nickname || user.phone || user.email}
                </span>
                <button onClick={onLogout} className="btn-ghost text-sm">
                  退出
                </button>
              </>
            ) : (
              <NavLink to="/login" className="btn-primary text-sm">
                登录
              </NavLink>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-6">
        {children}
      </main>

      <footer className="text-center text-xs text-gray-400 py-6">
        好房雷达 · 仅供参考，不介入联系/交易环节
      </footer>

      <Toast />
    </div>
  );
}

function Toast() {
  const toast = useUIStore((s) => s.toast);
  if (!toast) return null;
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg z-50">
      {toast}
    </div>
  );
}
