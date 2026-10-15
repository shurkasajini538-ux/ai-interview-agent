// Persistence is optional: browser privacy policies must not interrupt a job.
const key = "studio:pending-job";
export function pendingJob(): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
export function savePendingJob(id: string): void {
  try {
    localStorage.setItem(key, id);
  } catch {
    /* Current-page progress still works. */
  }
}
export function clearPendingJob(): void {
  try {
    localStorage.removeItem(key);
  } catch {
    /* Storage may be disabled. */
  }
}
