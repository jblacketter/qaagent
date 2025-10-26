export interface RunSummary {
  run_id: string;
  created_at: string;
  target: {
    name: string;
    path: string;
  };
  counts: Record<string, number>;
}

export interface RunDetail extends RunSummary {
  tools: Record<string, {
    version?: string;
    executed: boolean;
    exit_code?: number | null;
    error?: string | null;
  }>;
  evidence_files: Record<string, string>;
  diagnostics: string[];
}

export interface RiskRecord {
  risk_id: string;
  component: string;
  score: number;
  band: string;
  severity: string;
  confidence: number;
  title: string;
  description: string;
  factors: Record<string, number>;
  evidence_refs: string[];
  recommendations: string[];
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface RecommendationRecord {
  recommendation_id: string;
  component: string;
  priority: string;
  summary: string;
  details: string;
  metadata?: Record<string, unknown>;
  evidence_refs?: string[];
  created_at?: string;
}

export interface CoverageRecord {
  coverage_id: string;
  type: string;
  component: string;
  value: number;
  total_statements?: number;
  covered_statements?: number;
  sources?: string[];
  linked_cujs?: string[];
  collected_at?: string;
  metadata?: Record<string, unknown>;
}

export interface CujCoverageRecord {
  id: string;
  name: string;
  coverage: number;
  target: number;
  gap: number;
  components: Array<{ component: string; coverage: number }>;
  apis: Array<{ method: string; endpoint: string }>;
  acceptance: string[];
}

export interface RunTrendPoint {
  run_id: string;
  created_at: string;
  average_coverage: number | null;
  overall_coverage: number | null;
  high_risk_count: number;
  total_risks: number;
  risk_counts: Record<string, number>;
  average_risk_score: number | null;
}

export interface Repository {
  id: string;
  name: string;
  path: string;
  repo_type: string;
  last_scan: string | null;
  status: "ready" | "analyzing" | "error";
  run_count: number;
  analysis_options: Record<string, boolean>;
}

export interface RepositoryCreate {
  name: string;
  path: string;
  repo_type: "local" | "github";
  analysis_options: Record<string, boolean>;
}
