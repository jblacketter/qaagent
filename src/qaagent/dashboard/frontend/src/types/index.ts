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

export interface FixableCategory {
  category: string;
  tool: string;
  file_count: number;
  issue_count: number;
  auto_fixable: boolean;
  severity_breakdown: Record<string, number>;
  description: string;
}

export interface FixableIssuesSummary {
  categories: FixableCategory[];
  total_fixable_files: number;
  total_fixable_issues: number;
  total_manual_files: number;
}

export interface ApplyFixRequest {
  category: string;
  tool: string;
  files?: string[];
}

export interface ApplyFixResponse {
  status: string;
  files_modified: number;
  files_failed: number;
  message: string;
  errors: string[];
}

// App Documentation types
export interface RouteDoc {
  path: string;
  method: string;
  summary: string | null;
  description: string | null;
  auth_required: boolean;
  params: Record<string, unknown>;
  responses: Record<string, unknown>;
  tags: string[];
}

export interface FeatureArea {
  id: string;
  name: string;
  description: string;
  routes: RouteDoc[];
  crud_operations: string[];
  auth_required: boolean;
  integration_ids: string[];
  tags: string[];
}

export interface Integration {
  id: string;
  name: string;
  type: string;
  description: string;
  package: string | null;
  env_vars: string[];
  connected_features: string[];
  source: string;
}

export interface CujStep {
  order: number;
  action: string;
  route: string | null;
  method: string | null;
}

export interface DiscoveredCUJ {
  id: string;
  name: string;
  description: string;
  pattern: string;
  steps: CujStep[];
  feature_ids: string[];
  confidence: number;
}

export interface ArchitectureNode {
  id: string;
  label: string;
  type: string;
  metadata: Record<string, unknown>;
  position: { x: number; y: number } | null;
}

export interface ArchitectureEdge {
  id: string;
  source: string;
  target: string;
  label: string | null;
  type: string;
}

export interface AppDocumentation {
  app_name: string;
  summary: string;
  generated_at: string;
  content_hash: string;
  source_dir: string | null;
  features: FeatureArea[];
  integrations: Integration[];
  discovered_cujs: DiscoveredCUJ[];
  architecture_nodes: ArchitectureNode[];
  architecture_edges: ArchitectureEdge[];
  total_routes: number;
  metadata: Record<string, unknown>;
}
