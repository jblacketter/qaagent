import type {
  RunSummary,
  RunDetail,
  RiskRecord,
  RecommendationRecord,
  CoverageRecord,
  CujCoverageRecord,
  RunTrendPoint,
  Repository,
  RepositoryCreate,
  FixableIssuesSummary,
  ApplyFixRequest,
  ApplyFixResponse,
  AppDocumentation,
  FeatureArea,
  Integration,
  DiscoveredCUJ,
  ArchitectureNode,
  ArchitectureEdge,
  BranchCard,
  BranchChecklist,
  BranchTestRun,
  BranchStageInfo,
  BranchGenerateResult,
} from "../types";

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class QAAgentAPI {
  constructor(private readonly baseURL: string = DEFAULT_BASE_URL) {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });

    if (response.status === 401) {
      // Session expired or not authenticated — redirect to login
      window.location.href = "/login";
      throw new Error("Authentication required");
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed with status ${response.status}`);
    }
    return response.json();
  }

  async getRuns(limit = 50, offset = 0): Promise<{ runs: RunSummary[]; total: number }> {
    return this.request(`/api/runs?limit=${limit}&offset=${offset}`);
  }

  async getRun(runId: string): Promise<RunDetail> {
    return this.request(`/api/runs/${runId}`);
  }

  async getRisks(runId: string): Promise<RiskRecord[]> {
    const result = await this.request<{ risks: RiskRecord[] }>(`/api/runs/${runId}/risks`);
    return result.risks;
  }

  async getRecommendations(runId: string): Promise<RecommendationRecord[]> {
    const result = await this.request<{ recommendations: RecommendationRecord[] }>(`/api/runs/${runId}/recommendations`);
    return result.recommendations;
  }

  async getCoverage(runId: string): Promise<CoverageRecord[]> {
    const result = await this.request<{ coverage: CoverageRecord[] }>(`/api/runs/${runId}/coverage`);
    return result.coverage;
  }

  async getCujCoverage(runId: string): Promise<CujCoverageRecord[]> {
    const result = await this.request<{ journeys: CujCoverageRecord[] }>(`/api/runs/${runId}/cuj`);
    return result.journeys;
  }

  async getRunTrends(limit = 10): Promise<{ trend: RunTrendPoint[]; total: number }> {
    return this.request(`/api/runs/trends?limit=${limit}`);
  }

  // Repository Management
  async getRepositories(): Promise<{ repositories: Repository[] }> {
    return this.request(`/api/repositories`);
  }

  async getRepository(repoId: string): Promise<Repository> {
    return this.request(`/api/repositories/${repoId}`);
  }

  async createRepository(repo: RepositoryCreate): Promise<Repository> {
    return this.request(`/api/repositories`, {
      method: "POST",
      body: JSON.stringify(repo),
    });
  }

  async deleteRepository(repoId: string): Promise<{ status: string; id: string }> {
    return this.request(`/api/repositories/${repoId}`, {
      method: "DELETE",
    });
  }

  async analyzeRepository(repoId: string, force = false): Promise<{ status: string; repo_id: string; message: string }> {
    return this.request(`/api/repositories/${repoId}/analyze`, {
      method: "POST",
      body: JSON.stringify({ force }),
    });
  }

  async getRepositoryStatus(repoId: string): Promise<{ repo_id: string; status: string; last_scan: string }> {
    return this.request(`/api/repositories/${repoId}/status`);
  }

  // Auto-Fix Management
  async getFixableIssues(runId: string): Promise<FixableIssuesSummary> {
    return this.request(`/api/runs/${runId}/fixable-issues`);
  }

  async applyFix(runId: string, request: ApplyFixRequest): Promise<ApplyFixResponse> {
    return this.request(`/api/runs/${runId}/apply-fix`, {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  // App Documentation
  private _docQuery(path: string, repoId?: string): string {
    return repoId ? `${path}?repo_id=${encodeURIComponent(repoId)}` : path;
  }

  async getAppDoc(repoId?: string): Promise<AppDocumentation> {
    return this.request(this._docQuery(`/api/doc`, repoId));
  }

  async getFeatures(repoId?: string): Promise<FeatureArea[]> {
    const result = await this.request<{ features: FeatureArea[] }>(this._docQuery(`/api/doc/features`, repoId));
    return result.features;
  }

  async getFeature(featureId: string, repoId?: string): Promise<FeatureArea> {
    return this.request(this._docQuery(`/api/doc/features/${featureId}`, repoId));
  }

  async getIntegrations(repoId?: string): Promise<Integration[]> {
    const result = await this.request<{ integrations: Integration[] }>(this._docQuery(`/api/doc/integrations`, repoId));
    return result.integrations;
  }

  async getDiscoveredCujs(repoId?: string): Promise<DiscoveredCUJ[]> {
    const result = await this.request<{ cujs: DiscoveredCUJ[] }>(this._docQuery(`/api/doc/cujs`, repoId));
    return result.cujs;
  }

  async getArchitecture(repoId?: string): Promise<{ nodes: ArchitectureNode[]; edges: ArchitectureEdge[] }> {
    return this.request(this._docQuery(`/api/doc/architecture`, repoId));
  }

  async regenerateDoc(noLlm = false, repoId?: string): Promise<AppDocumentation> {
    return this.request(this._docQuery(`/api/doc/regenerate`, repoId), {
      method: "POST",
      body: JSON.stringify({ no_llm: noLlm }),
    });
  }

  async exportDocMarkdown(repoId?: string): Promise<string> {
    const result = await this.request<{ content: string }>(this._docQuery(`/api/doc/export/markdown`, repoId));
    return result.content;
  }

  // Agent endpoints
  private _agentQuery(path: string, repoId?: string): string {
    return repoId ? `${path}?repo_id=${encodeURIComponent(repoId)}` : path;
  }

  async getAgentConfig(repoId: string): Promise<AgentConfigResponse> {
    return this.request(this._agentQuery(`/api/agent/config`, repoId));
  }

  async saveAgentConfig(repoId: string, config: AgentConfigRequest): Promise<AgentConfigResponse> {
    return this.request(this._agentQuery(`/api/agent/config`, repoId), {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  async deleteAgentConfig(repoId: string): Promise<{ status: string }> {
    return this.request(this._agentQuery(`/api/agent/config`, repoId), { method: "DELETE" });
  }

  async analyzeWithAgent(repoId: string): Promise<AgentAnalyzeResponse> {
    return this.request(this._agentQuery(`/api/agent/analyze`, repoId), { method: "POST" });
  }

  async getAgentUsage(repoId: string): Promise<AgentUsageResponse> {
    return this.request(this._agentQuery(`/api/agent/usage`, repoId));
  }

  async resetAgentUsage(repoId: string): Promise<{ status: string }> {
    return this.request(this._agentQuery(`/api/agent/usage`, repoId), { method: "DELETE" });
  }

  // Branch Board
  async getBranches(repoId?: string, stage?: string): Promise<{ branches: BranchCard[] }> {
    const params = new URLSearchParams();
    if (repoId) params.set("repo_id", repoId);
    if (stage) params.set("stage", stage);
    const qs = params.toString();
    return this.request(`/api/branches${qs ? `?${qs}` : ""}`);
  }

  async getBranch(branchId: number): Promise<BranchCard> {
    return this.request(`/api/branches/${branchId}`);
  }

  async updateBranch(
    branchId: number,
    update: Partial<{ stage: string; story_id: string; story_url: string; notes: string }>,
  ): Promise<BranchCard> {
    return this.request(`/api/branches/${branchId}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  }

  async deleteBranch(branchId: number): Promise<{ status: string; id: number }> {
    return this.request(`/api/branches/${branchId}`, { method: "DELETE" });
  }

  async scanBranches(
    repoId: string,
    repoPath: string,
    baseBranch = "main",
  ): Promise<{ branches: BranchCard[]; count: number }> {
    const params = new URLSearchParams({ repo_id: repoId, repo_path: repoPath, base_branch: baseBranch });
    return this.request(`/api/branches/scan?${params}`, { method: "POST" });
  }

  async generateChecklist(branchId: number): Promise<{ checklist: BranchChecklist; diff_summary: Record<string, number> }> {
    return this.request(`/api/branches/${branchId}/checklist/generate`, { method: "POST" });
  }

  async getChecklist(branchId: number): Promise<{ checklist: BranchChecklist | null }> {
    return this.request(`/api/branches/${branchId}/checklist`);
  }

  async updateChecklistItem(
    itemId: number,
    status: string,
    notes?: string,
  ): Promise<{ status: string; id: number }> {
    const params = new URLSearchParams({ status });
    if (notes) params.set("notes", notes);
    return this.request(`/api/branches/checklist-items/${itemId}?${params}`, { method: "PATCH" });
  }

  async generateTests(branchId: number, baseUrl = "http://localhost:8000"): Promise<BranchGenerateResult> {
    const params = new URLSearchParams({ base_url: baseUrl });
    return this.request(`/api/branches/${branchId}/generate-tests?${params}`, { method: "POST" });
  }

  async runTests(branchId: number): Promise<{ test_run: BranchTestRun; summary: Record<string, number> }> {
    return this.request(`/api/branches/${branchId}/run-tests`, { method: "POST" });
  }

  async promoteTestRun(runDbId: number): Promise<{ status: string; id: number }> {
    return this.request(`/api/branches/test-runs/${runDbId}/promote`, { method: "PATCH" });
  }

  async getTestRuns(branchId: number): Promise<{ test_runs: BranchTestRun[] }> {
    return this.request(`/api/branches/${branchId}/test-runs`);
  }

  async getBranchStages(): Promise<{ stages: BranchStageInfo[] }> {
    return this.request(`/api/branches/stages`);
  }

  // Settings
  async getSettings(): Promise<AppSettingsResponse> {
    return this.request(`/api/settings`);
  }

  async clearDatabase(): Promise<{ status: string }> {
    return this.request(`/api/settings/clear-database`, { method: "POST" });
  }

  // Auth: change password
  async changePassword(oldPassword: string, newPassword: string): Promise<{ status: string }> {
    return this.request(`/api/auth/change-password`, {
      method: "POST",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
  }
}

export interface AgentConfigRequest {
  provider: string;
  model: string;
  api_key: string;
}

export interface AgentConfigResponse {
  provider: string;
  model: string;
  api_key_masked: string;
  configured: boolean;
}

export interface AgentAnalyzeResponse {
  content: string;
  model: string;
  usage: Record<string, number>;
}

export interface AgentUsageResponse {
  repo_id: string;
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface AppSettingsResponse {
  version: string;
  db_path: string;
  auth_enabled: boolean;
  username: string | null;
  repos_count: number;
  runs_count: number;
}

export const apiClient = new QAAgentAPI();
