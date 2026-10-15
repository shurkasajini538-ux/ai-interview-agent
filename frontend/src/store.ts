import { create } from "zustand";
import { api, ApiError, requestId, watchJob } from "./api";
import { pendingJob, savePendingJob, clearPendingJob } from "./pending";
import type { Bootstrap, Job, JobEvent } from "./types";
interface State {
  data: Bootstrap | null;
  error: string;
  job: Job | null;
  events: JobEvent[];
  busy: boolean;
  refresh: () => Promise<void>;
  clearError: () => void;
  run: <T>(kind: string, payload: unknown, session_id?: string) => Promise<T>;
  cancel: () => Promise<void>;
  recover: () => Promise<unknown>;
}
function awaitJob(
  id: string,
  set: (state: Partial<State>) => void,
): Promise<unknown> {
  return new Promise((resolve, reject) => {
    watchJob(
      id,
      (e) => set({ events: [...useStudio.getState().events.slice(-30), e] }),
      (job) => {
        clearPendingJob();
        set({ busy: false, job });
        if (job.state === "done") resolve(job.result);
        else reject(new Error(job.error || "操作已取消。"));
      },
      (e) => {
        set({ busy: false, error: e.message });
        reject(e);
      },
    );
  });
}
export const useStudio = create<State>((set, get) => ({
  data: null,
  error: "",
  job: null,
  events: [],
  busy: false,
  refresh: async () => {
    set({ data: await api<Bootstrap>("/api/bootstrap") });
  },
  clearError: () => set({ error: "" }),
  run: async <T>(
    kind: string,
    payload: unknown,
    session_id?: string,
  ): Promise<T> => {
    if (get().busy) throw Error("当前操作尚未完成。");
    set({ busy: true, error: "", events: [] });
    try {
      const job = await api<Job>("/api/jobs", {
        kind,
        payload,
        session_id,
        request_id: requestId(),
      });
      set({ job });
      savePendingJob(job.id);
      const result = await awaitJob(job.id, set);
      await get().refresh();
      return result as T;
    } catch (e) {
      set({ busy: false, error: (e as Error).message });
      throw e;
    }
  },
  cancel: async () => {
    const job = get().job;
    if (job) {
      const r = await api<Job>(`/api/jobs/${job.id}/cancel`, {});
      set({ job: r });
      if (!r.cancel_accepted)
        set({ error: "操作已保存或结束，请查看当前结果。" });
    }
  },
  recover: async () => {
    const id = pendingJob();
    if (!id) return null;
    try {
      const job = await api<Job>("/api/jobs/" + id);
      set({
        job,
        events: job.events,
        busy: !["done", "failed", "cancelled"].includes(job.state),
      });
      if (job.state === "done") {
        clearPendingJob();
        await get().refresh();
        return job.result;
      }
      if (["failed", "cancelled"].includes(job.state)) {
        clearPendingJob();
        set({ error: job.error });
        return null;
      }
      const result = await awaitJob(id, set);
      await get().refresh();
      return result;
    } catch (e) {
      // Preserve the recovery handle on a transient network failure.
      if (e instanceof ApiError && e.status === 404) clearPendingJob();
      set({ busy: false, error: (e as Error).message });
      return null;
    }
  },
}));
