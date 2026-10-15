import { Link } from "react-router-dom";
import { useStudio } from "../store";
import { api } from "../api";
import { Empty, Header, Icon, Tag } from "../components";
export default function History() {
  const { data, refresh } = useStudio();
  const sessions = data?.sessions || [];
  async function remove(id: string) {
    if (confirm("确定删除这次练习及相关回答、反馈吗？")) {
      await api(`/api/sessions/${id}/delete`, {});
      await refresh();
    }
  }
  return (
    <>
      <Header
        eyebrow="YOUR PRACTICE JOURNAL"
        title="每一次练习，都能回看"
        subtitle="继续未完成的练习，或查看回答、反馈与报告。"
      >
        <Link className="btn primary" to="/new">
          <Icon name="plus" />
          新建练习
        </Link>
      </Header>
      <section className="panel">
        {sessions.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>目标岗位</th>
                  <th>简历 / 时间</th>
                  <th>进度</th>
                  <th>平均分</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id}>
                    <td>{s.role}</td>
                    <td>
                      {s.resume_name}
                      <br />
                      <span className="text-muted">
                        {new Date(s.created_at).toLocaleString("zh-CN")}
                      </span>
                    </td>
                    <td>
                      {s.answered} 已评分 / {s.question_count} 题
                      {s.skipped > 0 && (
                        <>
                          <br />
                          {s.skipped} 已跳过
                        </>
                      )}
                    </td>
                    <td>{s.average ?? "—"}</td>
                    <td>
                      <Tag type={s.status === "completed" ? "" : "gray"}>
                        {s.status === "completed" ? "已完成" : "进行中"}
                      </Tag>
                    </td>
                    <td>
                      <div className="button-row">
                        <Link
                          className="btn small"
                          to={`/${s.status === "completed" ? "report" : "interview"}/${s.id}`}
                        >
                          {s.status === "completed" ? "报告" : "继续"}
                        </Link>
                        {s.status !== "completed" && (
                          <Link
                            className="btn ghost small"
                            to={"/report/" + s.id}
                          >
                            报告
                          </Link>
                        )}
                        <button
                          className="btn ghost small"
                          aria-label="删除练习"
                          onClick={() => void remove(s.id)}
                        >
                          <Icon name="trash" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="还没有练习记录"
            text="从一份简历开始，建立你的第一份练习档案。"
          >
            <Link className="btn primary" to="/new">
              开始练习
            </Link>
          </Empty>
        )}
      </section>
    </>
  );
}
