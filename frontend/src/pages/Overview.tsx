import { Link } from "react-router-dom";
import { useStudio } from "../store";
import { Bars, Empty, Header, Icon, SessionRow } from "../components";
export default function Overview() {
  const d = useStudio((s) => s.data)!;
  const active = d.sessions.find((s) => s.status === "active");
  const history = d.sessions
    .filter((s) => s.average !== null)
    .slice(0, 8)
    .reverse();
  const stats = [
    ["简历档案", d.stats.resumes, "份", "file"],
    ["练习次数", d.stats.sessions, "次", "chat"],
    ["已评分回答", d.stats.answered, "题", "check"],
    ["平均练习分", d.stats.average ?? "—", "/ 100", "chart"],
  ];
  return (
    <>
      <Header
        eyebrow="YOUR PRACTICE, IN FOCUS"
        title="让下一次面试，更有把握"
        subtitle="整理经历，练习表达，回看每一步进展。"
      >
        <Link className="btn primary" to="/new">
          <Icon name="plus" />
          新建练习
        </Link>
      </Header>
      <section className="hero">
        <div>
          <div className="eyebrow">从真实经历开始</div>
          <h2>
            把经历讲清楚，
            <br />
            把准备变成底气。
          </h2>
          <p>
            导入简历，针对目标岗位逐题练习。用追问补齐细节，用有依据的反馈改进下一次回答。
          </p>
          <div className="button-row">
            <Link className="btn lime" to="/new">
              开始面试练习 <Icon name="arrow" />
            </Link>
            {active && (
              <Link
                className="btn ghost hero-continue"
                to={"/interview/" + active.id}
              >
                继续上次练习
              </Link>
            )}
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit" />
          <div className="art-badge">真实经历 · 有据可循</div>
          <div className="art-card">
            <b>我的面试准备</b>
            <div className="art-line" />
            <div className="art-line short" />
            <div className="art-line" />
            <div className="tag-row">
              <span className="tag">项目经历</span>
              <span className="tag">个人贡献</span>
            </div>
            <div className="art-line" />
          </div>
          <div className="art-score">
            <small>练习的每一步</small>
            <strong>都有进步 ↗</strong>
            <small>回答 · 追问 · 反馈</small>
          </div>
        </div>
      </section>
      <div className="stat-grid">
        {stats.map(([label, value, unit, icon]) => (
          <div className="stat-card" key={label}>
            <div className="stat-icon">
              <Icon name={String(icon)} />
            </div>
            <div className="stat-label">{label}</div>
            <div className="stat-value">
              {value}
              <small>{unit}</small>
            </div>
            <div className="stat-foot">
              {label === "平均练习分"
                ? "请结合评分依据理解分数"
                : "数据来自实际保存记录"}
            </div>
          </div>
        ))}
      </div>
      <div className="two-col">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>最近练习</h2>
              <p>保存每次回答，随时回到上次的位置。</p>
            </div>
            <Link className="btn ghost small" to="/history">
              查看全部 <Icon name="arrow" />
            </Link>
          </div>
          {d.sessions.length ? (
            d.sessions
              .slice(0, 4)
              .map((s) => <SessionRow key={s.id} session={s} />)
          ) : (
            <Empty
              title="还没有练习记录"
              text="先导入一份简历，再开始你的第一轮面试。"
            >
              <Link className="btn small" to="/resumes">
                导入简历
              </Link>
            </Empty>
          )}
        </section>
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>能力观察</h2>
              <p>已评分回答的分项均值 · 每项 25 分</p>
            </div>
            <Icon name="chart" />
          </div>
          {Object.keys(d.stats.dimensions).length ? (
            <Bars values={d.stats.dimensions} />
          ) : (
            <Empty
              title="等待你的第一份反馈"
              text="完成回答后，这里会展示结构、深度、表达和证据表现。"
            />
          )}
        </section>
      </div>
      <div className="spacer" />
      <div className="two-col">
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>练习轨迹</h2>
              <p>最近 {history.length} 次有评分的练习</p>
            </div>
          </div>
          {history.length ? (
            <>
              <div className="trend-wrap">
                <div className="mini-trend">
                  {history.map((s) => (
                    <div
                      className="trend-column"
                      key={s.id}
                      style={{ height: Math.max(3, s.average || 0) + "%" }}
                    >
                      <span>{s.average}</span>
                      <small>
                        {new Date(s.created_at).toLocaleDateString("zh-CN", {
                          month: "numeric",
                          day: "numeric",
                        })}
                      </small>
                    </div>
                  ))}
                </div>
              </div>
              <p className="section-note">
                不同模型与模式的分数可能不同，建议在相同设置下对照练习。
              </p>
            </>
          ) : (
            <Empty
              title="进步会在这里留下轨迹"
              text="完成练习后，回来看看你在哪些地方讲得更好了。"
            />
          )}
        </section>
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2>下一次，重点练什么</h2>
              <p>根据近期分项表现生成</p>
            </div>
          </div>
          {d.weak_points.length ? (
            d.weak_points.map((w, i) => (
              <div className="step mt" key={w.key}>
                <div className="step-number">{i + 1}</div>
                <div>
                  <b>{w.label}</b>
                  <p>近期对应维度均分 {w.average}/25。</p>
                </div>
              </div>
            ))
          ) : (
            <Empty
              title="先建立你的练习基线"
              text="有了实际回答，才有适合你的改进建议。"
            />
          )}
        </section>
      </div>
    </>
  );
}
