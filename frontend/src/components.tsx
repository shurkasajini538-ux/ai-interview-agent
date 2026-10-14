import { Link } from "react-router-dom";
import { useStudio } from "./store";
import type { Coach, Evaluation, SessionSummary } from "./types";
import { useState } from "react";
export const engineName = (e: string) =>
  ({
    online: "在线模型",
    local: "离线规则",
    local_fallback: "离线规则 · 在线回退",
  })[e] || e;
export const formatDate = (d: string) =>
  new Date(d).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
export function Icon({ name = "file" }: { name?: string }) {
  const paths: Record<string, string> = {
    home: "M3 10 12 3l9 7v10H3ZM9 20v-7h6v7",
    file: "M6 3h8l4 4v14H6ZM14 3v5h4M9 12h6M9 16h6",
    chat: "M3 4h18v13H9l-5 4v-4H3ZM7 9h10M7 12h7",
    clock: "M12 7v5l3 2",
    settings: "M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6",
    plus: "M12 5v14M5 12h14",
    arrow: "M4 12h16m-6-6 6 6-6 6",
    upload: "M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6",
    check: "m5 12 4 4L19 6",
    spark: "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z",
    chart: "M4 3v18h17M8 16v-5m5 5V7m5 9V4",
    info: "M12 10v7M12 6v1",
    close: "m6 6 12 12M18 6 6 18",
    trash: "M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7",
  };
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {["clock", "info"].includes(name) && <circle cx="12" cy="12" r="9" />}
      <path d={paths[name] || paths.file} />
    </svg>
  );
}
export function Tag({
  children,
  type = "",
}: {
  children: React.ReactNode;
  type?: string;
}) {
  return <span className={"tag " + type}>{children}</span>;
}
export function Note({
  children,
  type = "",
}: {
  children: React.ReactNode;
  type?: string;
}) {
  return (
    <div className={"callout " + type}>
      <Icon name="info" />
      <span>{children}</span>
    </div>
  );
}
export function Header({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="button-row">{children}</div>
    </div>
  );
}
export function Empty({
  title,
  text,
  children,
}: {
  title: string;
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Icon />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {children}
    </div>
  );
}
export function Bars({
  values,
  max = 25,
}: {
  values: Record<string, number>;
  max?: number;
}) {
  return (
    <div className="bars">
      {Object.entries(values).map(([label, value]) => (
        <div key={label}>
          <div className="bar-top">
            <span>{label}</span>
            <span>
              {value}
              {max === 25 ? " / 25" : ""}
            </span>
          </div>
          <div className="bar-track">
            <div
              className="bar-fill"
              style={{
                width: Math.min(100, (value / Math.max(1, max)) * 100) + "%",
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
export function SessionRow({ session: s }: { session: SessionSummary }) {
  return (
    <div className="list-row">
      <div className="file-icon">
        <Icon name="chat" />
      </div>
      <div className="row-main">
        <b>{s.role}</b>
        <small>
          {s.resume_name} · {formatDate(s.created_at)} · 已评分 {s.answered}/
          {s.question_count}
        </small>
      </div>
      {s.average !== null && <span className="score-pill">{s.average} 分</span>}
      <Link
        className="btn small"
        to={`/${s.status === "completed" ? "report" : "interview"}/${s.id}`}
      >
        {s.status === "completed" ? "查看报告" : "继续练习"}
      </Link>
    </div>
  );
}
export function CoachTrace({ coach }: { coach?: Coach }) {
  return coach?.trace?.length ? (
    <details className="evidence-box">
      <summary>本次教练的工具与依据 · {coach.tool_calls || 0} 次调用</summary>
      {coach.trace.map((t, i) => (
        <div className="trace-row" key={i}>
          <b>{t.label}</b>
          {t.query && <p>检索：{t.query}</p>}
          {t.result_count !== undefined && <p>返回 {t.result_count} 条记录</p>}
          {t.fact && <p>待确认：{t.fact}</p>}
          {t.reason && <p>{t.reason}</p>}
        </div>
      ))}
    </details>
  ) : null;
}
export function Result({
  result: r,
  report = false,
}: {
  result: Evaluation;
  report?: boolean;
}) {
  const [tab, setTab] = useState("feedback");
  const feedback = (
    <>
      <div>
        {r.dimensions.map((d) => (
          <div className="feedback-detail" key={d.key}>
            <b>
              {d.label} · {d.score}/25
            </b>
            <p>{d.feedback}</p>
            <blockquote>
              {d.evidence
                ? "回答依据：“" + d.evidence + "”"
                : "未引用直接回答证据，请结合建议核对。"}
            </blockquote>
          </div>
        ))}
      </div>
      <h3 className="mt">下次先改进</h3>
      <ul className="tips">
        {r.suggestions.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </>
  );
  const star = (
    <>
      <div className="star-text">{r.optimized}</div>
      <div className="spacer" />
      {r.missing_facts.length > 0 ? (
        <Note>待补充：{r.missing_facts.join("；")}</Note>
      ) : (
        <Note>以上内容来自你的回答，请核对后用自己的语言自然表达。</Note>
      )}
      {!report && (
        <button
          className="btn small mt"
          onClick={() => navigator.clipboard.writeText(r.optimized)}
        >
          复制整理结果
        </button>
      )}
    </>
  );
  return (
    <>
      <div className="result-score">
        <div className="score-number">
          {r.total}
          <small>/ 100</small>
        </div>
        <div>
          <h3>本题练习反馈</h3>
          <p>{engineName(r.engine)} · 总分由四项分数相加</p>
        </div>
      </div>
      <div className="dimension-grid">
        {r.dimensions.map((d) => (
          <div className="dimension" key={d.key}>
            <span>{d.label}</span>
            <b>{d.score}</b>
            <small> /25</small>
          </div>
        ))}
      </div>
      <Note type={r.engine === "local_fallback" ? "warn" : ""}>{r.notice}</Note>
      <CoachTrace coach={r.coach} />
      {r.metrics && (
        <p className="section-note mt">
          本次 {r.metrics.requests} 次模型请求 ·{" "}
          {(r.metrics.elapsed_ms / 1000).toFixed(1)} 秒
          {r.metrics.usage_available
            ? ` · ${r.metrics.prompt_tokens + r.metrics.completion_tokens} tokens`
            : ""}
        </p>
      )}
      {report ? (
        <>
          {feedback}
          <h3 className="mt">STAR 整理 · 只使用已提供的事实</h3>
          {star}
        </>
      ) : (
        <>
          <div className="tabs">
            <button
              className={"tab " + (tab === "feedback" ? "active" : "")}
              onClick={() => setTab("feedback")}
            >
              评分依据与改进
            </button>
            <button
              className={"tab " + (tab === "star" ? "active" : "")}
              onClick={() => setTab("star")}
            >
              STAR 回答整理
            </button>
          </div>
          {tab === "feedback" ? feedback : star}
        </>
      )}
    </>
  );
}
export function Progress() {
  const { busy, events, cancel } = useStudio();
  if (!busy) return null;
  const last = events.filter((e) => e.label).at(-1);
  const preview = events.filter((e) => e.preview).at(-1)?.preview;
  return (
    <section className="job-progress no-print" aria-live="polite">
      <div className="button-row">
        <span className="spinner" />
        <strong>{last?.label || "正在准备本次操作"}</strong>
        <button className="btn ghost small" onClick={() => void cancel()}>
          取消操作
        </button>
      </div>
      {preview && (
        <p className="stream-preview">
          {preview}
          <span className="stream-cursor">▍</span>
        </p>
      )}
      <p className="section-note">
        生成内容将在核对完成后保存。取消是协作式的，正在发送的模型请求可能仍计费。
      </p>
    </section>
  );
}
