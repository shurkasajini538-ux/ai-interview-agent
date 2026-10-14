import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useStudio } from "../store";
import type { Resume } from "../types";
import {
  Bars,
  Empty,
  Header,
  Icon,
  Note,
  Tag,
  formatDate,
} from "../components";
export default function Resumes() {
  const { data: d, refresh, run, busy } = useStudio();
  const [modal, setModal] = useState<"import" | "edit" | null>(null);
  const [search, setSearch] = useState("");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [editing, setEditing] = useState<Resume | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) setModal(null);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [busy]);
  if (!d) return null;
  async function sample() {
    try {
      const sample = await api<{ text: string }>("/api/sample");
      await api("/api/resumes", {
        text: sample.text,
        title: "示例 · 后端实习简历",
        filename: "示例简历.md",
      });
      await refresh();
      setModal(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function edit(r: Resume) {
    try {
      const full = await api<Resume>("/api/resumes/" + r.id);
      setEditing(full);
      setText(full.text || "");
      setTitle(full.title);
      setError("");
      setModal("edit");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function save() {
    setSaving(true);
    setError("");
    try {
      await api(
        modal === "edit"
          ? `/api/resumes/${editing!.id}/update`
          : "/api/resumes",
        { text, title },
      );
      await refresh();
      setModal(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }
  async function importFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (list.length > 5) {
      setError("一次最多导入 5 份简历。");
      return;
    }
    setSaving(true);
    setError("");
    const failures: string[] = [];
    for (let i = 0; i < list.length; i++) {
      const file = list[i];
      setStatus(`正在解析 ${i + 1}/${list.length}：${file.name}`);
      try {
        if (file.size > 12 * 1024 * 1024) throw Error("单份文件最大 12 MB");
        const encoded = await new Promise<string>((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(String(r.result).split(",")[1]);
          r.onerror = () => reject(Error("文件读取失败"));
          r.readAsDataURL(file);
        });
        await run("import", {
          filename: file.name,
          file_data: encoded,
          title: list.length === 1 ? title : "",
        });
      } catch (e) {
        failures.push(file.name + "：" + (e as Error).message);
      }
    }
    setSaving(false);
    setStatus("");
    if (failures.length) setError(failures.join("；"));
    else setModal(null);
  }
  async function remove(r: Resume) {
    if (confirm("确定删除这份简历吗？已有练习中的简历快照会保留。")) {
      await api(`/api/resumes/${r.id}/delete`, {});
      await refresh();
    }
  }
  const filtered = d.resumes.filter((r) =>
    (r.title + " " + r.parsed.skills.join(" "))
      .toLowerCase()
      .includes(search.toLowerCase()),
  );
  return (
    <>
      <Header
        eyebrow="RESUME LIBRARY"
        title="从你的经历，找到练习起点"
        subtitle="支持文字、Word、PDF 与图片；所有解析结果都可以核对修改。"
      >
        <button
          className="btn primary"
          onClick={() => {
            setTitle("");
            setText("");
            setError("");
            setModal("import");
          }}
        >
          <Icon name="plus" />
          导入简历
        </button>
      </Header>
      {error && !modal && <Note type="error">{error}</Note>}
      <div className="library-controls">
        <input
          aria-label="搜索简历"
          placeholder="搜索简历名称或技能…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className="btn" onClick={() => void sample()}>
          使用示例简历
        </button>
      </div>
      {filtered.length ? (
        <div className="library-grid">
          {filtered.map((r) => (
            <article className="resume-card" key={r.id}>
              <div className="button-row">
                <div className="file-icon">
                  <Icon />
                </div>
                <Tag type="gray">{r.parsed.education || "学历未提供"}</Tag>
              </div>
              <h3>{r.title}</h3>
              <p>
                {formatDate(r.created_at)} 导入 · {r.parsed.character_count} 字
                · {r.parsed.projects.length} 段识别项目
              </p>
              <div className="tag-row">
                {r.parsed.skills.slice(0, 5).map((s) => (
                  <Tag key={s}>{s}</Tag>
                ))}
              </div>
              <div className="button-row">
                <Link className="btn primary small" to={"/new?resume=" + r.id}>
                  开始练习
                </Link>
                <button className="btn small" onClick={() => void edit(r)}>
                  查看 / 编辑
                </button>
                <button
                  className="btn ghost small"
                  aria-label="删除简历"
                  onClick={() => void remove(r)}
                >
                  <Icon name="trash" />
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title={search ? "没有匹配的简历" : "你的简历档案还是空的"}
          text="可以先使用示例体验，再导入自己的真实简历。"
        />
      )}
      {d.resumes.length > 0 && (
        <div className="stats-summary">
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>档案中的技能</h2>
                <p>按实际简历中出现的次数统计</p>
              </div>
            </div>
            <Bars
              values={d.stats.skills}
              max={Math.max(1, ...Object.values(d.stats.skills))}
            />
          </section>
          <section className="panel">
            <div className="panel-head">
              <div>
                <h2>学历分布</h2>
                <p>仅显示明确提供的学历，缺失值保持未知</p>
              </div>
            </div>
            <Bars values={d.stats.education} max={d.resumes.length} />
            <div className="spacer" />
            <Note>
              统计直接来自实际导入的简历，不推断薪资、工作年限或招聘优先级。
            </Note>
          </section>
        </div>
      )}
      {modal && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="resume-modal-title"
          >
            <div className="modal-head">
              <h2 id="resume-modal-title">
                {modal === "import" ? "导入你的简历" : "核对简历内容"}
              </h2>
              <button
                className="btn ghost"
                aria-label="关闭"
                disabled={busy || saving}
                onClick={() => setModal(null)}
              >
                <Icon name="close" />
              </button>
            </div>
            {error && <Note type="error">{error}</Note>}
            <div className="form-field">
              <label htmlFor="resume-title">
                {modal === "edit" ? "名称" : "简历名称（可选）"}
              </label>
              <input
                id="resume-title"
                value={title}
                maxLength={100}
                onChange={(e) => setTitle(e.target.value)}
                disabled={saving}
              />
            </div>
            {modal === "import" ? (
              <>
                <label
                  className="drop-zone"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (!saving) void importFiles(e.dataTransfer.files);
                  }}
                >
                  <Icon name="upload" />
                  <strong>拖入文件，或点击选择</strong>
                  <span>PDF / DOCX / PNG / JPG / WEBP / TXT / MD</span>
                  <span>每份最大 12 MB · 一次最多 5 份 · 本地 OCR</span>
                  <input
                    id="resume-files"
                    type="file"
                    multiple
                    disabled={saving}
                    accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.bmp,.txt,.md"
                    onChange={(e) => {
                      if (e.target.files) void importFiles(e.target.files);
                    }}
                  />
                </label>
                <div className="upload-status" role="status">
                  {status}
                </div>
                <div className="divider">或者粘贴文字</div>
              </>
            ) : (
              <>
                <div className="detail-facts">
                  <div className="detail-fact">
                    <span>识别姓名</span>
                    <b>{editing?.parsed.name || "未明确提供"}</b>
                  </div>
                  <div className="detail-fact">
                    <span>明确学历</span>
                    <b>{editing?.parsed.education || "未明确提供"}</b>
                  </div>
                </div>
                {editing?.warnings.map((w) => (
                  <Note key={w} type="warn">
                    {w}
                  </Note>
                ))}
              </>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void save();
              }}
            >
              <div className="form-field mt">
                <label htmlFor="resume-text">
                  {modal === "edit" ? "可编辑全文" : "简历文字"}
                </label>
                <textarea
                  id="resume-text"
                  value={text}
                  maxLength={60000}
                  onChange={(e) => setText(e.target.value)}
                  disabled={saving}
                />
                <small>已有练习保留当时的简历快照。</small>
              </div>
              <div className="button-row">
                <button
                  className="btn primary"
                  type="submit"
                  disabled={saving || busy}
                >
                  {modal === "edit" ? "保存并重新解析" : "保存文字简历"}
                </button>
                {modal === "import" && (
                  <button
                    className="btn"
                    type="button"
                    disabled={saving}
                    onClick={() => void sample()}
                  >
                    使用示例简历
                  </button>
                )}
              </div>
            </form>
            {busy && (
              <Note>
                {status || "正在处理文件…"}{" "}
                <button
                  className="btn small"
                  onClick={() => void useStudio.getState().cancel()}
                >
                  取消当前文件
                </button>
              </Note>
            )}
          </section>
        </div>
      )}
    </>
  );
}
