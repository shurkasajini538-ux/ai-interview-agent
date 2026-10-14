import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useStudio } from "../store";
import { Empty, Header, Icon, Note, Tag, formatDate } from "../components";
import type { Session } from "../types";
export default function Setup() {
  const { data: d, run, busy } = useStudio();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [resume, setResume] = useState(
    params.get("resume") || d?.resumes[0]?.id || "",
  );
  const [role, setRole] = useState("后端开发实习生");
  const [count, setCount] = useState(6);
  const [difficulty, setDifficulty] = useState("标准");
  const [jd, setJd] = useState("");
  if (!d) return null;
  async function start() {
    try {
      const s = await run<Session>("session", {
        resume_id: resume,
        role,
        count,
        difficulty,
        job_description: jd,
      });
      navigate("/interview/" + s.id);
    } catch {
      /* store displays failure and retains fields */
    }
  }
  const steps = [
    ["针对性提问", "结合简历证据、目标岗位与近期薄弱点。"],
    ["回答与追问", "每题先回答，再通过一道追问补齐关键细节。"],
    ["有依据的反馈", "查看分项分数、回答引用和待补充事实。"],
    ["整理与重新练习", "按 STAR 组织真实事实，保留重答历史。"],
    ["保存报告", "记录自动保存，支持导出与打印。"],
  ];
  return (
    <>
      <Header
        eyebrow="A PRACTICE THAT FITS YOU"
        title="准备好，开始这一轮"
        subtitle="选择简历与目标岗位，生成本次固定题目。"
      >
        <Link className="btn" to="/resumes">
          管理简历
        </Link>
      </Header>
      <div className="setup-layout">
        <section className="panel">
          <div className="panel-head">
            <h2>练习设置</h2>
            <Tag type={d.settings.mode === "online" ? "online" : "gray"}>
              {d.settings.mode === "online" ? "在线模型" : "离线规则"}
            </Tag>
          </div>
          {d.resumes.length ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void start();
              }}
            >
              <div className="form-field">
                <label htmlFor="setup-resume">本次使用的简历</label>
                <select
                  id="setup-resume"
                  value={resume}
                  onChange={(e) => setResume(e.target.value)}
                >
                  {d.resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.title} · {formatDate(r.updated_at)} 更新
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-field">
                <label htmlFor="setup-role">目标岗位或面试方向</label>
                <input
                  id="setup-role"
                  required
                  value={role}
                  maxLength={100}
                  onChange={(e) => setRole(e.target.value)}
                />
                <div className="role-chips">
                  {[
                    "后端开发实习生",
                    "前端开发实习生",
                    "数据分析师",
                    "产品经理",
                    "计算机保研",
                  ].map((r) => (
                    <button
                      className="role-chip"
                      type="button"
                      key={r}
                      onClick={() => setRole(r)}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </div>
              <div className="form-inline">
                <div className="form-field">
                  <label htmlFor="setup-count">本轮题数</label>
                  <select
                    id="setup-count"
                    value={count}
                    onChange={(e) => setCount(Number(e.target.value))}
                  >
                    {[6, 8, 10].map((n) => (
                      <option key={n} value={n}>
                        {n} 题 · 约 {Math.round(n * 2.5)} 分钟
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-field">
                  <label htmlFor="setup-difficulty">追问深度</label>
                  <select
                    id="setup-difficulty"
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                  >
                    {["标准", "入门引导", "深入挑战"].map((n) => (
                      <option key={n}>{n}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="form-field">
                <label htmlFor="setup-jd">岗位描述 / 导师方向 （可选）</label>
                <textarea
                  id="setup-jd"
                  maxLength={6000}
                  value={jd}
                  onChange={(e) => setJd(e.target.value)}
                  placeholder="粘贴岗位职责与要求，帮助问题更贴合目标。"
                />
              </div>
              <Note>
                {d.settings.mode === "online"
                  ? "开始后，相关简历与岗位描述会发送至配置的模型服务，联系方式默认隐藏。"
                  : "离线模式根据真实简历出题并提供规则辅助。可在模型设置中启用在线反馈。"}
              </Note>
              <div className="spacer" />
              <button className="btn primary" disabled={busy}>
                <Icon name="spark" />
                生成题目并开始
              </button>
            </form>
          ) : (
            <Empty
              title="先准备一份简历"
              text="导入后就能开始练习，也可以使用示例简历。"
            >
              <Link className="btn primary" to="/resumes">
                去导入简历
              </Link>
            </Empty>
          )}
        </section>
        <aside className="panel">
          <div className="panel-head">
            <h2>这一轮，你会经历</h2>
          </div>
          <div className="steps">
            {steps.map(([a, b], i) => (
              <div className="step" key={a}>
                <div className="step-number">{i + 1}</div>
                <div>
                  <b>{a}</b>
                  <p>{b}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="spacer" />
          <Note>
            {d.weak_points.length
              ? "本次将关注：" + d.weak_points.map((w) => w.label).join("；")
              : "准备一个真实项目、一次问题解决经历，以及能够核对的成果证据。"}
          </Note>
        </aside>
      </div>
    </>
  );
}
