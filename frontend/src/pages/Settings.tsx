import { useEffect, useState } from "react";
import { api } from "../api";
import { useStudio } from "../store";
import type { Settings as Config } from "../types";
import { Header, Note, Tag } from "../components";
export default function Settings() {
  const { data, refresh, busy } = useStudio();
  const [c, setConfig] = useState<Config>(data!.settings);
  const [key, setKey] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  useEffect(() => setConfig(data!.settings), [data?.settings]);
  const locked = (name: string) => c.locked_fields?.includes(name) || false;
  async function save(test = false, clear = false) {
    setPending(true);
    setError("");
    setResult("");
    try {
      const next = await api<Config>("/api/settings", {
        mode: clear ? "local" : c.mode,
        model: c.model,
        base_url: c.base_url,
        redact_contacts: c.redact_contacts,
        api_key: key,
        clear_key: clear,
      });
      setConfig(next);
      setKey("");
      await refresh();
      if (test) {
        const r = await api<{ message: string }>("/api/settings/test", {});
        setResult(r.message);
      } else setResult("设置已保存。");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(false);
    }
  }
  return (
    <>
      <Header
        eyebrow="YOUR MODEL, YOUR CHOICE"
        title="选择适合你的练习方式"
        subtitle="在线模型提供语义反馈；离线模式可以随时练习。"
      />
      <div className="settings-layout">
        <section className="panel">
          {error && <Note type="error">{error}</Note>}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <div className="select-mode">
              {[
                ["online", "在线模型", "更细致的个性化问题与反馈"],
                ["local", "离线练习", "本机规则辅助，无模型调用"],
              ].map(([value, title, description]) => (
                <label className="mode-choice" key={value}>
                  <input
                    type="radio"
                    name="mode"
                    value={value}
                    checked={c.mode === value}
                    disabled={locked("mode")}
                    onChange={() => setConfig({ ...c, mode: value })}
                  />
                  <span>
                    <b>{title}</b>
                    <small>{description}</small>
                  </span>
                </label>
              ))}
            </div>
            <div className="form-field">
              <label htmlFor="model-base">OpenAI 兼容接口地址</label>
              <input
                id="model-base"
                value={c.base_url}
                required
                disabled={locked("base_url")}
                onChange={(e) => setConfig({ ...c, base_url: e.target.value })}
              />
            </div>
            <div className="form-field">
              <label htmlFor="model-name">模型名称</label>
              <input
                id="model-name"
                value={c.model}
                required
                disabled={locked("model")}
                onChange={(e) => setConfig({ ...c, model: e.target.value })}
              />
            </div>
            <div className="form-field">
              <label htmlFor="model-key">
                API Key{" "}
                <Tag type={c.has_key ? "online" : "gray"}>
                  {c.has_key ? "已配置" : "未配置"}
                </Tag>
              </label>
              <input
                id="model-key"
                type="password"
                value={key}
                disabled={locked("api_key")}
                autoComplete="new-password"
                onChange={(e) => setKey(e.target.value)}
                placeholder={
                  c.has_key ? "留空保留当前密钥" : "填写你的 API Key"
                }
              />
              <small>密钥不会回传到浏览器。存储方式：{c.key_storage}。</small>
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={c.redact_contacts}
                disabled={locked("redact_contacts")}
                onChange={(e) =>
                  setConfig({ ...c, redact_contacts: e.target.checked })
                }
              />
              发送给模型前隐藏手机号、邮箱和身份证号
            </label>
            <div className="spacer" />
            {c.locked_fields?.length ? (
              <Note>
                部分字段由环境变量或 .env 管理，修改配置后刷新即可生效。
              </Note>
            ) : null}
            <div className="spacer" />
            <div className="button-row">
              <button className="btn primary" disabled={pending || busy}>
                保存设置
              </button>
              <button
                className="btn"
                type="button"
                disabled={pending || busy}
                onClick={() => void save(true)}
              >
                保存并测试连接
              </button>
              {c.has_key && !locked("api_key") && (
                <button
                  className="btn ghost danger"
                  type="button"
                  disabled={pending || busy}
                  onClick={() => {
                    if (confirm("清除当前密钥并切换到离线模式？"))
                      void save(false, true);
                  }}
                >
                  清除密钥
                </button>
              )}
            </div>
          </form>
          {pending && (
            <p className="busy-inline mt">
              <span className="spinner" />
              正在处理设置…
            </p>
          )}
          {result && (
            <div className="mt">
              <Note>{result}</Note>
            </div>
          )}
        </section>
        <aside className="panel">
          <div className="settings-note">
            <h3>模型与证据</h3>
            在线教练可调用受控工具检索简历、读取历史薄弱点和标记缺失事实。工具记录与引用来源会展示在练习中。
          </div>
          <div className="settings-note">
            <h3>数据存在哪里</h3>
            简历、回答与报告保存在本机数据库。不同浏览器空间分别保存记录，请固定使用一个浏览器并导出重要报告。
          </div>
          <div className="settings-note">
            <h3>哪些内容会发送出去</h3>
            在线模式只发送相关简历摘要、检索片段、岗位要求与回答。文件解析和 OCR
            在本机完成。
          </div>
          <div className="settings-note">
            <h3>怎样理解反馈</h3>AI
            与离线评分都用于练习参考。整理后的回答保留原文事实和待补充标记，建议结合教师意见核对。
          </div>
        </aside>
      </div>
    </>
  );
}
