import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { GitBranch, RefreshCw, Loader2 } from "lucide-react";
import { apiClient } from "../services/api";
import { BranchColumn } from "../components/Branch/BranchColumn";
import { BranchDetail } from "../components/Branch/BranchDetail";
import type { BranchCard, Repository } from "../types";

const STAGES = ["created", "active", "in_review", "merged", "qa", "released"];

export function BranchBoardPage() {
  const queryClient = useQueryClient();
  const [selectedRepoId, setSelectedRepoId] = useState<string>("");
  const [selectedCard, setSelectedCard] = useState<BranchCard | null>(null);

  // Fetch repositories for the selector
  const { data: reposData } = useQuery({
    queryKey: ["repositories"],
    queryFn: () => apiClient.getRepositories(),
  });

  // Fetch branches for selected repo
  const { data: branchesData, isLoading: branchesLoading } = useQuery({
    queryKey: ["branches", selectedRepoId],
    queryFn: () => apiClient.getBranches(selectedRepoId || undefined),
    enabled: !!selectedRepoId,
  });

  // Fetch stages
  const { data: stagesData } = useQuery({
    queryKey: ["branchStages"],
    queryFn: () => apiClient.getBranchStages(),
  });

  // Find repo object for scanning
  const repos: Repository[] = reposData?.repositories || [];
  const selectedRepo = repos.find((r) => r.id === selectedRepoId);

  // Scan mutation
  const scanBranches = useMutation({
    mutationFn: () => {
      if (!selectedRepo) throw new Error("No repo selected");
      return apiClient.scanBranches(selectedRepo.id, selectedRepo.path);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branches", selectedRepoId] });
    },
  });

  const branches: BranchCard[] = branchesData?.branches || [];
  const stages = stagesData?.stages || [];

  // Group branches by stage
  const byStage = new Map<string, BranchCard[]>();
  for (const stage of STAGES) {
    byStage.set(stage, []);
  }
  for (const card of branches) {
    const list = byStage.get(card.stage);
    if (list) list.push(card);
    else byStage.set(card.stage, [card]);
  }

  // When selected card's data might have changed, refresh it
  const handleCardSelect = (card: BranchCard) => {
    setSelectedCard(card.id === selectedCard?.id ? null : card);
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <section className="space-y-1">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-slate-900 dark:text-slate-100">
          <GitBranch className="h-6 w-6" />
          Branch Board
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Track branch lifecycle, generate test checklists, and monitor test progress.
        </p>
      </section>

      {/* Controls */}
      <section className="flex flex-wrap items-center gap-3">
        <select
          value={selectedRepoId}
          onChange={(e) => {
            setSelectedRepoId(e.target.value);
            setSelectedCard(null);
          }}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
        >
          <option value="">Select a repository...</option>
          {repos.map((repo) => (
            <option key={repo.id} value={repo.id}>
              {repo.name}
            </option>
          ))}
        </select>

        <button
          onClick={() => scanBranches.mutate()}
          disabled={!selectedRepoId || scanBranches.isPending}
          className="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          {scanBranches.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
          Scan Branches
        </button>

        {branches.length > 0 && (
          <span className="text-sm text-slate-500 dark:text-slate-400">
            {branches.length} branch{branches.length !== 1 ? "es" : ""} tracked
          </span>
        )}

        {scanBranches.isError && (
          <span className="text-sm text-red-600 dark:text-red-400">
            Scan failed. Check that the repository path is accessible.
          </span>
        )}
      </section>

      {/* Empty state */}
      {!selectedRepoId && (
        <section className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-12 text-center dark:border-slate-700 dark:bg-slate-900">
          <GitBranch className="mx-auto mb-3 h-10 w-10 text-slate-300 dark:text-slate-600" />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Select a repository to view its branch board.
          </p>
        </section>
      )}

      {/* Loading state */}
      {selectedRepoId && branchesLoading && (
        <section className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </section>
      )}

      {/* Kanban board */}
      {selectedRepoId && !branchesLoading && (
        <section className="flex gap-3 overflow-x-auto pb-4">
          {STAGES.map((stage) => (
            <BranchColumn
              key={stage}
              stage={stage}
              cards={byStage.get(stage) || []}
              selectedId={selectedCard?.id ?? null}
              onSelect={handleCardSelect}
            />
          ))}
        </section>
      )}

      {/* No branches after scan */}
      {selectedRepoId && !branchesLoading && branches.length === 0 && !scanBranches.isPending && (
        <section className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center dark:border-slate-700 dark:bg-slate-900">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            No branches tracked yet. Click "Scan Branches" to discover branches in this repository.
          </p>
        </section>
      )}

      {/* Detail panel */}
      {selectedCard && (
        <section>
          <BranchDetail
            key={selectedCard.id}
            card={selectedCard}
            stages={stages}
            onClose={() => setSelectedCard(null)}
          />
        </section>
      )}
    </div>
  );
}
