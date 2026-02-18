import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "../services/api";
import type { AgentConfigRequest } from "../services/api";
import Markdown from "react-markdown";
import { Alert } from "../components/ui/Alert";
import { useAutoRepo } from "../hooks/useAutoRepo";

export function AgentPage() {
  const { repoId, isRedirecting } = useAutoRepo();
  const queryClient = useQueryClient();

  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("claude-sonnet-4-5-20250929");
  const [apiKey, setApiKey] = useState("");
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const configQuery = useQuery({
    queryKey: ["agentConfig", repoId],
    queryFn: () => apiClient.getAgentConfig(repoId!),
    enabled: Boolean(repoId),
  });

  const usageQuery = useQuery({
    queryKey: ["agentUsage", repoId],
    queryFn: () => apiClient.getAgentUsage(repoId!),
    enabled: Boolean(repoId),
  });

  const saveMutation = useMutation({
    mutationFn: (config: AgentConfigRequest) =>
      apiClient.saveAgentConfig(repoId!, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentConfig", repoId] });
      setApiKey("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.deleteAgentConfig(repoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentConfig", repoId] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => apiClient.analyzeWithAgent(repoId!),
    onSuccess: () => {
      setAnalyzeError(null);
      queryClient.invalidateQueries({ queryKey: ["agentUsage", repoId] });
    },
    onError: (err: Error) => {
      setAnalyzeError(err.message);
      queryClient.invalidateQueries({ queryKey: ["agentUsage", repoId] });
    },
  });

  const resetUsageMutation = useMutation({
    mutationFn: () => apiClient.resetAgentUsage(repoId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agentUsage", repoId] });
    },
  });

  if (isRedirecting) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-slate-400">Loading...</p>
      </div>
    );
  }

  if (!repoId) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          AI-Enhanced Documentation
        </h1>
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          Select a repository to use AI-powered deep analysis.
        </p>
        <Link
          to="/repositories"
          className="mt-6 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          Go to Repositories
        </Link>
      </div>
    );
  }

  const isConfigured = configQuery.data?.configured ?? false;

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          AI-Enhanced Documentation
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Send your project data to an LLM for enhanced product documentation.
        </p>
      </section>

      {/* Configuration */}
      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
          Configuration
        </h2>
        {isConfigured && (
          <div className="mb-4 rounded-md bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/20 dark:text-green-300">
            Configured: {configQuery.data?.provider} / {configQuery.data?.model} (key: {configQuery.data?.api_key_masked})
          </div>
        )}
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">
              Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            >
              <option value="anthropic">Anthropic</option>
              <option value="openai">OpenAI</option>
              <option value="ollama">Ollama (local)</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">
              Model
            </label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="claude-sonnet-4-5-20250929"
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            />
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <button
            onClick={() =>
              saveMutation.mutate({ provider, model, api_key: apiKey })
            }
            disabled={saveMutation.isPending || !apiKey}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
          >
            {saveMutation.isPending ? "Saving..." : "Save"}
          </button>
          {isConfigured && (
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
            >
              Clear Config
            </button>
          )}
        </div>
      </section>

      {/* Analyze */}
      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
          Analysis
        </h2>
        <button
          onClick={() => analyzeMutation.mutate()}
          disabled={!isConfigured || analyzeMutation.isPending}
          className="rounded-md bg-blue-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          {analyzeMutation.isPending ? "Analyzing..." : "Generate AI Analysis"}
        </button>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400 max-w-xl">
          Sends your project documentation to the configured LLM to generate a structured analysis
          covering architecture, features, user journeys, and recommendations.
          This is a one-time generation, not a conversation.
        </p>
        {!isConfigured && (
          <p className="mt-2 text-xs text-slate-400">
            Configure your API key above to enable analysis.
          </p>
        )}
        {analyzeMutation.isPending && (
          <div className="mt-4 flex items-center gap-3 rounded-md border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
            <svg className="h-5 w-5 animate-spin text-blue-600 dark:text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <div>
              <p className="text-sm font-medium text-blue-700 dark:text-blue-300">
                Project data sent to {configQuery.data?.provider ?? "LLM"} / {configQuery.data?.model ?? "model"}
              </p>
              <p className="text-xs text-blue-500 dark:text-blue-400">
                Waiting for response. This may take a few minutes for large projects.
              </p>
            </div>
          </div>
        )}

        {analyzeError && (
          <div className="mt-4">
            <Alert variant="error">
              {analyzeError}
            </Alert>
          </div>
        )}

        {analyzeMutation.data && (
          <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Enhanced Documentation
              </h3>
              <span className="text-xs text-slate-400">
                model: {analyzeMutation.data.model}
              </span>
            </div>
            <div className="prose prose-sm max-w-none dark:prose-invert text-sm text-slate-700 dark:text-slate-300">
              <Markdown>{analyzeMutation.data.content}</Markdown>
            </div>
          </div>
        )}
      </section>

      {/* Token Usage Widget */}
      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Token Usage
          </h2>
          <button
            onClick={() => resetUsageMutation.mutate()}
            disabled={resetUsageMutation.isPending}
            className="text-xs text-slate-400 underline transition hover:text-slate-600 disabled:opacity-50"
          >
            Reset
          </button>
        </div>
        {usageQuery.data ? (
          <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-5">
            <UsageStat label="Requests" value={usageQuery.data.requests} />
            <UsageStat
              label="Input Tokens"
              value={usageQuery.data.prompt_tokens.toLocaleString()}
            />
            <UsageStat
              label="Output Tokens"
              value={usageQuery.data.completion_tokens.toLocaleString()}
            />
            <UsageStat
              label="Total Tokens"
              value={usageQuery.data.total_tokens.toLocaleString()}
            />
            <UsageStat
              label="Est. Cost"
              value={`$${usageQuery.data.estimated_cost_usd.toFixed(4)}`}
            />
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-400">No usage data yet.</p>
        )}
      </section>
    </div>
  );
}

function UsageStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        {value}
      </p>
    </div>
  );
}
