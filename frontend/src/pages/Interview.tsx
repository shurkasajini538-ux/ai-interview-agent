import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useStudio } from "../store";
import type { Question, Session } from "../types";
import {
  CoachTrace,
  Empty,
  Header,
  Icon,
  Note,
  Result,
  Tag,
  engineName,
} from "../components";
function Evidence({ question: q }: { question: Question }) {
  return (
    <details className="evidence-box">
      <summary>简历依据与考察要点</summary>
      <pre>{q.source}</pre>
      <div className="spacer" />
      <b>考察要点：</b>
      {q.objective}
      {q.evidence?.map((e) => (
        <div className="trace-row" key={e.id}>
          <b>来源 {e.id}</b>
          <p>
            原文位置 {e.start}–{e.end} · {e.strategy}
          </p>
          <pre>{e.text}</pre>
        </div>
      ))}
    </details>
  );
}
export default function Interview({ report = false }: { report?: boolean }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { run, busy, refresh } = useStudio();
  const [s, setSession] = useState<Session | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    setSession(null);
    setError("");
    void api<Session>("/api/sessions/" + id)
      .then((v) => {
        if (mounted.current) setSession(v);
      })
      .catch((e) => setError(e.message));
    return () => {
      mounted.current = false;
    };
  }, [id]);
  const q = s?.questions[s.current_index];
  const key = q ? `studio:draft:${s!.id}:${q.id}:${q.stage}` : "";
  useEffect(() => {
    try {
      setAnswer(localStorage.getItem(key) || "");
    } catch {
      setAnswer("");
    }
  }, [key]);
  if (error) return <Note type="error">{error}</Note>;
  if (!s || !q) return <Empty title="正在读取练习" text="请稍候。" />;
  const session = s,
    question = q,
    showReport = report || s.status === "completed";
  async function act(kind: string, evaluateNow = false) {
    if (busy) return;
    try {
      const updated = await run<Session>(
        kind,
        {
          question_id: question.id,
          answer: kind === "answer" ? answer : "",
          evaluate_now: evaluateNow,
        },
        session.id,
      );
      if (kind === "answer")
        try {
          localStorage.removeItem(key);
        } catch {}
      if (mounted.current) {
        setSession(updated);
        if (updated.status === "completed") navigate("/report/" + session.id);
      }
    } catch {
      /* global error is visible */
    }
  }
  function draft(value: string) {
    setAnswer(value);
    try {
      localStorage.setItem(key, value);
    } catch {}
  }
  const results = s.questions.flatMap((q) => (q.result ? [q.result] : []));
  const average = results.length
    ? Math.round(
        (results.reduce((n, r) => n + r.total, 0) / results.length) * 10,
      ) / 10
    : null;
  if (showReport)
    return (
      <>
        <Header
          eyebrow="A RECORD OF YOUR PROGRESS"
          title="练习报告"
          subtitle={`${s.resume_name} · ${new Date(s.created_at).toLocaleString("zh-CN")}`}
        >
          {s.status === "active" && (
            <Link className="btn primary" to={"/interview/" + s.id}>
              继续练习
            </Link>
          )}
          <a className="btn" href={`/api/sessions/${s.id}/export?format=md`}>
            导出 Markdown
          </a>
          <a className="btn" href={`/api/sessions/${s.id}/export?format=json`}>
            JSON
          </a>
          <button
            className="btn"
            onClick={() => {
              document
                .querySelectorAll<HTMLDetailsElement>(".report-question")
                .forEach((n) => (n.open = true));
              window.print();
            }}
          >
            打印 / 保存 PDF
          </button>
        </Header>
        <div className="report-head">
          <div>
            <div className="eyebrow">
              {s.status === "completed" ? "本轮练习已完成" : "本轮练习进行中"}
            </div>
            <h2>{s.role}</h2>
            <p>
              已评分 {results.length}/{s.questions.length} 题 ·{" "}
              {engineName(s.engine)} {s.model}
            </p>
          </div>
          <div className="report-total">
            {average ?? "—"}
            <small> / 100</small>
          </div>
        </div>
        <Note>
          平均分仅包含已评分题目。不同模型或模式的分数不可直接等同，请优先查看回答依据与改进。
        </Note>
        <section className="panel mt">
          <h2>下一轮练习计划</h2>
          <ol className="tips">
            <li>补齐待确认事实，准备可以核对的测试、反馈或产出。</li>
            <li>选择得分较低的维度重新练习，并请教师或同伴核对。</li>
            <li>在相同模型与评分模式下比较内容和表达的变化。</li>
          </ol>
        </section>
        {s.questions.map((x, i) => (
          <details
            className="panel report-question"
            key={x.id}
            open={!!x.result}
          >
            <summary>
              <span>
                第 {i + 1} 题 · {x.category}
              </span>
              <span className="score-pill">
                {x.result
                  ? x.result.total + " / 100"
                  : x.stage === "skipped"
                    ? "已跳过"
                    : "尚未评分"}
              </span>
            </summary>
            <div>
              <div className="question-bubble">{x.text}</div>
              <Evidence question={x} />
              {x.answers.map((a, j) => (
                <div className="answer-bubble" key={j}>
                  <div className="chat-label">{j ? "补充" : "首次"}回答</div>
                  {a.text}
                </div>
              ))}
              {x.followup && (
                <div className="followup-bubble">追问：{x.followup}</div>
              )}
              {x.result ? (
                <Result result={x.result} report />
              ) : (
                <p className="section-note">本题尚无评分，不计入平均分。</p>
              )}
              {x.attempts.length > 0 && (
                <details className="evidence-box">
                  <summary>查看此前 {x.attempts.length} 次作答</summary>
                  {x.attempts.map((a, j) => (
                    <div className="feedback-detail" key={j}>
                      <b>
                        第 {j + 1} 次 · {a.result.total}/100
                      </b>
                      <pre>{a.answers.map((x) => x.text).join("\n")}</pre>
                    </div>
                  ))}
                </details>
              )}
            </div>
          </details>
        ))}
      </>
    );
  const done = s.questions.filter(
    (x) => x.result || x.stage === "skipped",
  ).length;
  return (
    <>
      <Header
        eyebrow="IN THE INTERVIEW"
        title={s.role}
        subtitle={`${s.resume_name} · 练习随进度自动保存`}
      >
        <Link className="btn" to={"/report/" + s.id}>
          查看当前报告
        </Link>
        <Link className="btn ghost" to="/history">
          返回记录
        </Link>
      </Header>
      <div className="interview-layout">
        <aside className="panel question-rail">
          <div className="rail-title">本轮题目 · {s.questions.length} 题</div>
          {s.questions.map((x, i) => (
            <div
              key={x.id}
              className={`rail-item ${i === s.current_index ? "current" : ""} ${x.result ? "done" : ""}`}
            >
              <span className="num">
                {x.result ? "✓" : x.stage === "skipped" ? "–" : i + 1}
              </span>
              <div>
                <b>{x.category}</b>
                <small>
                  {x.result
                    ? x.result.total + " / 100"
                    : x.stage === "skipped"
                      ? "已跳过"
                      : i === s.current_index
                        ? "正在练习"
                        : "等待作答"}
                </small>
              </div>
            </div>
          ))}
          <div className="rail-summary">
            <div className="bar-top">
              <span>本轮进度</span>
              <span>
                {done}/{s.questions.length}
              </span>
            </div>
            <div className="progress-track">
              <div style={{ width: (done / s.questions.length) * 100 + "%" }} />
            </div>
            <p className="section-note">
              {engineName(s.engine)} {s.model}
            </p>
            {s.memory_used.map((w) => (
              <p key={w.key} className="section-note mt">
                本次关注：{w.label}
              </p>
            ))}
          </div>
        </aside>
        <section className="panel">
          <div className="question-header">
            <h2>
              第 {s.current_index + 1} 题 / {s.questions.length}
            </h2>
            <Tag>{q.category}</Tag>
          </div>
          {s.notice && (
            <>
              <Note type="warn">{s.notice}</Note>
              <div className="spacer" />
            </>
          )}
          <div className="chat-label">
            <Icon name="chat" />
            面试官
          </div>
          <div className="question-bubble">{q.text}</div>
          <Evidence question={q} />
          <CoachTrace coach={q.coach} />
          {q.answers.map((a, i) => (
            <div key={i}>
              <div className="answer-bubble">
                <div className="chat-label">你的{i ? "补充" : "回答"}</div>
                {a.text}
              </div>
              {i === 0 && q.followup && (
                <>
                  <div className="followup-bubble">
                    <div className="chat-label">
                      <Icon name="chat" />
                      深入追问 · {engineName(q.followup_engine || "local")}
                    </div>
                    {q.followup}
                  </div>
                  <CoachTrace coach={q.followup_coach} />
                </>
              )}
            </div>
          ))}
          {q.notice && q.stage === "followup" && (
            <Note type="warn">{q.notice}</Note>
          )}
          {q.result ? (
            <>
              <Result result={q.result} />
              <div className="compose-footer mt">
                <span className="section-note">
                  {q.attempts.length
                    ? "已保留 " + q.attempts.length + " 次历史作答。"
                    : "重新作答会保留已有反馈。"}
                </span>
                <div className="button-row">
                  <button
                    className="btn"
                    disabled={busy}
                    onClick={() => void act("retry")}
                  >
                    重新作答本题
                  </button>
                  <button
                    className="btn primary"
                    disabled={busy}
                    onClick={() => void act("next")}
                  >
                    {s.current_index === s.questions.length - 1
                      ? "完成并查看报告"
                      : "继续下一题"}
                    <Icon name="arrow" />
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="answer-compose">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void act("answer");
                }}
              >
                <div className="form-field">
                  <label htmlFor="answer-text">
                    {q.stage === "followup" ? "补充回答" : "你的回答"}
                  </label>
                  <textarea
                    id="answer-text"
                    maxLength={10000}
                    value={answer}
                    onChange={(e) => draft(e.target.value)}
                    disabled={busy}
                    placeholder="交代背景、你的任务、实际行动和结果。没有统计数字时说明验证方法。"
                  />
                </div>
                <div className="compose-footer">
                  <small>
                    {answer.length} / 10,000 字 · 草稿保存在此浏览器
                  </small>
                  <div className="button-row">
                    <button
                      className="btn ghost"
                      type="button"
                      disabled={busy}
                      onClick={() => {
                        if (confirm("确定跳过本题吗？跳过题目不计入平均分。"))
                          void act("skip");
                      }}
                    >
                      跳过本题
                    </button>
                    {q.stage === "followup" && (
                      <button
                        className="btn"
                        type="button"
                        disabled={busy}
                        onClick={() => void act("answer", true)}
                      >
                        以现有回答评分
                      </button>
                    )}
                    <button className="btn primary" disabled={busy}>
                      {q.stage === "followup"
                        ? "提交补充并评分"
                        : "提交回答并追问"}
                      <Icon name="arrow" />
                    </button>
                  </div>
                </div>
              </form>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
