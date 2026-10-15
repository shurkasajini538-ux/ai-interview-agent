export interface Evidence {
  id: string;
  text: string;
  start: number;
  end: number;
  score: number;
  strategy: string;
  matched: boolean;
}
export interface Trace {
  tool: string;
  label: string;
  query?: string;
  source_ids?: string[];
  result_count?: number;
  fact?: string;
  reason?: string;
}
export interface Coach {
  trace?: Trace[];
  fact_gaps?: { fact: string; reason: string }[];
  tool_calls?: number;
}
export interface Dimension {
  key: string;
  label: string;
  score: number;
  max: number;
  evidence: string;
  feedback: string;
}
export interface Metrics {
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  elapsed_ms: number;
  usage_available: boolean;
}
export interface Evaluation {
  dimensions: Dimension[];
  total: number;
  engine: string;
  suggestions: string[];
  optimized: string;
  missing_facts: string[];
  notice: string;
  coach?: Coach;
  metrics?: Metrics;
}
export interface Answer {
  text: string;
  kind: string;
  time: string;
}
export interface Attempt {
  answers: Answer[];
  followup: string;
  result: Evaluation;
}
export interface Question {
  id: string;
  category: string;
  text: string;
  objective: string;
  source: string;
  stage: string;
  answers: Answer[];
  followup: string;
  result: Evaluation | null;
  attempts: Attempt[];
  coach?: Coach;
  followup_coach?: Coach;
  followup_engine?: string;
  evidence?: Evidence[];
  notice?: string;
}
export interface Resume {
  id: string;
  title: string;
  filename: string;
  created_at: string;
  updated_at: string;
  warnings: string[];
  text?: string;
  parsed: {
    name: string;
    education: string;
    skills: string[];
    projects: { title: string; evidence: string }[];
    character_count: number;
    metrics: string[];
  };
}
export interface SessionSummary {
  id: string;
  role: string;
  resume_name: string;
  status: string;
  created_at: string;
  updated_at: string;
  answered: number;
  skipped: number;
  question_count: number;
  average: number | null;
  engine: string;
  current_index: number;
}
export interface Session {
  id: string;
  role: string;
  resume_name: string;
  status: string;
  created_at: string;
  model: string;
  engine: string;
  notice: string;
  current_index: number;
  questions: Question[];
  memory_used: WeakPoint[];
  usage_history?: Metrics[];
}
export interface WeakPoint {
  key: string;
  label: string;
  average: number;
}
export interface Settings {
  mode: string;
  model: string;
  base_url: string;
  has_key: boolean;
  redact_contacts: boolean;
  agent_enabled: boolean;
  stream_enabled: boolean;
  key_storage: string;
  locked_fields?: string[];
  configuration_sources?: Record<string, string>;
}
export interface Bootstrap {
  settings: Settings;
  resumes: Resume[];
  sessions: SessionSummary[];
  weak_points: WeakPoint[];
  stats: {
    resumes: number;
    sessions: number;
    answered: number;
    average: number | null;
    dimensions: Record<string, number>;
    education: Record<string, number>;
    skills: Record<string, number>;
  };
}
export interface JobEvent {
  sequence: number;
  kind: string;
  label?: string;
  preview?: string;
  characters?: number;
  elapsed_ms?: number;
  tool?: string;
  result_count?: number;
}
export interface Job {
  id: string;
  state: string;
  result: unknown;
  error: string;
  events: JobEvent[];
  cancel_accepted?: boolean;
}
