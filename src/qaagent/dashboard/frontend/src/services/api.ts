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
} from "../types";

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class QAAgentAPI {
  constructor(private readonly baseURL: string = DEFAULT_BASE_URL) {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });

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
}

export const apiClient = new QAAgentAPI();
