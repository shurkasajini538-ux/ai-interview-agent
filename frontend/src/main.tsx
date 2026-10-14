import React, { Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  HashRouter,
  NavLink,
  Routes,
  Route,
  Link,
  useNavigate,
} from "react-router-dom";
import { useStudio } from "./store";
import { Icon, Note, Progress } from "./components";
import "./styles.css";
const Overview = lazy(() => import("./pages/Overview"));
const Resumes = lazy(() => import("./pages/Resumes"));
const Setup = lazy(() => import("./pages/Setup"));
const Interview = lazy(() => import("./pages/Interview"));
const History = lazy(() => import("./pages/History"));
const Settings = lazy(() => import("./pages/Settings"));
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: string }
> {
  state = { error: "" };
  static getDerivedStateFromError(e: Error) {
    return { error: e.message };
  }
  render() {
    return this.state.error ? (
      <div className="panel">
        <h2>页面暂时无法显示</h2>
        <p>已保存记录仍保留，请刷新重试。</p>
        <button className="btn" onClick={() => location.reload()}>
          刷新页面
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}
function App() {
  const { data, error, clearError, refresh, recover } = useStudio();
  const navigate = useNavigate();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let live = true;
    void (async () => {
      try {
        await refresh();
        if (live) setReady(true);
        const result = (await recover()) as {
          id?: string;
          questions?: unknown;
          status?: string;
        } | null;
        if (result?.questions && result.id)
          navigate(
            `/${result.status === "completed" ? "report" : "interview"}/${result.id}`,
          );
      } catch (e) {
        useStudio.setState({ error: (e as Error).message });
      } finally {
        if (live) setReady(true);
      }
    })();
    return () => {
      live = false;
    };
  }, []);
  if (!ready || !data)
    return (
      <div className="boot">{error || "面试工坊正在准备你的练习空间…"}</div>
    );
  const nav = [
    ["/overview", "home", "练习总览"],
    ["/resumes", "file", "简历档案"],
    ["/new", "chat", "开始练习"],
    ["/history", "clock", "练习记录"],
    ["/settings", "settings", "模型设置"],
  ];
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/overview" className="brand">
          <img src="/assets/icon.svg" alt="" />
          <div>
            <strong>面试工坊</strong>
            <small>INTERVIEW STUDIO</small>
          </div>
        </Link>
        <div className="nav-label">我的练习空间</div>
        <nav>
          {nav.map(([path, icon, label]) => (
            <NavLink
              key={path}
              aria-label={label}
              to={path}
              className={({ isActive }) =>
                "nav-item " + (isActive ? "active" : "")
              }
            >
              <Icon name={icon} />
              <span>{label}</span>
              {path === "/resumes" && (
                <span className="nav-count" aria-hidden="true">
                  {data.resumes.length}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-card">
            <h3>每次练习，都有依据。</h3>
            <p>从真实经历出发，逐题深入，把回答讲得更清楚。</p>
            <Link className="btn small" to="/new">
              开始一轮练习 <Icon name="arrow" />
            </Link>
          </div>
          <div className="local-profile">
            <div className="avatar">练</div>
            <div>
              <span>我的本地空间</span>
              <small>记录保存在这台电脑</small>
            </div>
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            工作台 <b>/ 面试工坊</b>
          </div>
          <div className="top-status">
            <span className="engine-chip">
              <i className="dot" />
              {data.settings.mode === "online"
                ? "在线模型已选择"
                : "离线练习模式"}
            </span>
            <span className="date">
              {new Date().toLocaleDateString("zh-CN", {
                year: "numeric",
                month: "long",
                day: "numeric",
              })}
            </span>
          </div>
        </header>
        <div className="content">
          {error && (
            <div className="button-row">
              <Note type="error">{error}</Note>
              <button className="btn small" onClick={clearError}>
                收起
              </button>
            </div>
          )}
          <Progress />
          <ErrorBoundary>
            <Suspense fallback={<div className="boot">正在准备页面…</div>}>
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/overview" element={<Overview />} />
                <Route path="/resumes" element={<Resumes />} />
                <Route path="/new" element={<Setup />} />
                <Route path="/interview/:id" element={<Interview />} />
                <Route path="/report/:id" element={<Interview report />} />
                <Route path="/history" element={<History />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
          <div className="footer-note">
            面试工坊 · 以真实经历为起点，让每一次练习留下进步
          </div>
        </div>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(
  <HashRouter>
    <App />
  </HashRouter>,
);
