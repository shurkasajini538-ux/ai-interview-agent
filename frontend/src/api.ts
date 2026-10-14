import type { Job, JobEvent } from "./types";
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Studio-Request": "1",
          },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "请求失败，请重试。");
  return data as T;
}
export const requestId = () => crypto.randomUUID();
export function watchJob(
  id: string,
  onEvent: (e: JobEvent) => void,
  onFinal: (job: Job) => void,
  onError: (e: Error) => void,
) {
  const stream = new EventSource(`/api/jobs/${id}/events`);
  stream.onmessage = (e) => onEvent(JSON.parse(e.data));
  stream.addEventListener("final", (e) => {
    stream.close();
    onFinal(JSON.parse((e as MessageEvent).data));
  });
  let failures = 0;
  stream.onerror = () => {
    if (++failures > 4) {
      stream.close();
      onError(
        new Error(
          "进度连接暂时断开，操作可能仍在继续。可刷新恢复或查看练习记录。",
        ),
      );
    }
  };
  return () => stream.close();
}
