import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, GitBranch, ExternalLink, FileText, GitCommit, ListChecks, Loader2, Save, Play, FlaskConical, ArrowUpRight } from "lucide-react";
import { clsx } from "clsx";
import { apiClient } from "../../services/api";
import { ChecklistView } from "./ChecklistView";
import type { BranchCard, BranchStageInfo } from "../../types";

const STAGE_LABELS: Record<string, string> = {
  created: "Created",
  active: "Active",
  in_review: "In Review",
  merged: "Merged",
  qa: "QA",
  released: "Released",
};

interface BranchDetailProps {
  card: BranchCard;
  stages: BranchStageInfo[];
  onClose: () => void;
}

export function BranchDetail({ card, stages, onClose }: BranchDetailProps) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editStage, setEditStage] = useState(card.stage);
  const [editStoryId, setEditStoryId] = useState(card.story_id || "");
  const [editStoryUrl, setEditStoryUrl] = useState(card.story_url || "");
  const [editNotes, setEditNotes] = useState(card.notes || "");

  const { data: checklistData, isLoading: checklistLoading } = useQuery({
    queryKey: ["checklist", card.id],
    queryFn: () => apiClient.getChecklist(card.id),
  });

  const { data: testRunsData } = useQuery({
    queryKey: ["testRuns", card.id],
    queryFn: () => apiClient.getTestRuns(card.id),
  });

  const generateChecklist = useMutation({
    mutationFn: () => apiClient.generateChecklist(card.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["checklist", card.id] });
    },
  });

  const generateTests = useMutation({
    mutationFn: () => apiClient.generateTests(card.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["testRuns", card.id] });
    },
  });

  const runTests = useMutation({
    mutationFn: () => apiClient.runTests(card.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["testRuns", card.id] });
    },
  });

  const promoteRun = useMutation({
    mutationFn: (runDbId: number) => apiClient.promoteTestRun(runDbId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["testRuns", card.id] });
    },
  });

  const updateBranch = useMutation({
    mutationFn: () =>
      apiClient.updateBranch(card.id, {
        stage: editStage,
        story_id: editStoryId || undefined,
        story_url: editStoryUrl || undefined,
        notes: editNotes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branches"] });
      setEditing(false);
    },
  });

  const checklist = checklistData?.checklist;
  const testRuns = testRunsData?.test_runs || [];

  return (
    <div className="rounded-lg border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      {/* Header */}
      <div className="flex items-start justify-between border-b border-slate-200 p-4 dark:border-slate-700">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 shrink-0 text-slate-400" />
            <h2 className="truncate text-lg font-semibold text-slate-900 dark:text-slate-100">
              {card.branch_name}
            </h2>
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Base: <span className="font-mono">{card.base_branch}</span>
            {card.merged_at && <> &middot; Merged {new Date(card.merged_at).toLocaleDateString()}</>}
          </p>
        </div>
        <button onClick={onClose} className="rounded p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="space-y-4 p-4">
        {/* Info row */}
        <div className="flex flex-wrap gap-4 text-sm">
          <span className={clsx(
            "rounded-full px-2.5 py-0.5 text-xs font-semibold",
            card.stage === "released" && "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
            card.stage === "qa" && "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
            card.stage === "merged" && "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400",
            card.stage === "in_review" && "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
            card.stage === "active" && "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
            card.stage === "created" && "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400",
          )}>
            {STAGE_LABELS[card.stage] || card.stage}
          </span>
          {card.commit_count > 0 && (
            <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
              <GitCommit className="h-4 w-4" /> {card.commit_count} commits
            </span>
          )}
          {card.files_changed > 0 && (
            <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
              <FileText className="h-4 w-4" /> {card.files_changed} files
            </span>
          )}
          {card.story_id && (
            <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
              {card.story_url ? (
                <a href={card.story_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-blue-600 hover:underline dark:text-blue-400">
                  {card.story_id} <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                card.story_id
              )}
            </span>
          )}
        </div>

        {/* Change summary */}
        {card.change_summary && (
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Change Summary</h3>
            <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{card.change_summary}</p>
          </div>
        )}

        {/* Notes */}
        {card.notes && !editing && (
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Notes</h3>
            <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{card.notes}</p>
          </div>
        )}

        {/* Edit form */}
        {editing ? (
          <div className="space-y-3 rounded-md border border-slate-200 p-3 dark:border-slate-700">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Stage</label>
              <select
                value={editStage}
                onChange={(e) => setEditStage(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
              >
                {stages.map((s) => (
                  <option key={s.value} value={s.value}>
                    {STAGE_LABELS[s.value] || s.value}{s.auto ? " (auto)" : ""}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Story ID</label>
              <input
                value={editStoryId}
                onChange={(e) => setEditStoryId(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                placeholder="e.g. PROJ-123"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Story URL</label>
              <input
                value={editStoryUrl}
                onChange={(e) => setEditStoryUrl(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                placeholder="https://jira.example.com/browse/PROJ-123"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Notes</label>
              <textarea
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                rows={3}
                className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                placeholder="Add notes..."
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => updateBranch.mutate()}
                disabled={updateBranch.isPending}
                className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <Save className="h-3.5 w-3.5" />
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="rounded px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setEditing(true)}
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            Edit card...
          </button>
        )}

        {/* Checklist section */}
        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700 dark:text-slate-300">
              <ListChecks className="h-4 w-4" />
              Test Checklist
            </h3>
            <button
              onClick={() => generateChecklist.mutate()}
              disabled={generateChecklist.isPending}
              className="flex items-center gap-1 rounded bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              {generateChecklist.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : null}
              {checklist ? "Regenerate" : "Generate"}
            </button>
          </div>

          {checklistLoading && (
            <p className="text-sm text-slate-400">Loading checklist...</p>
          )}

          {!checklistLoading && checklist && (
            <ChecklistView checklist={checklist} branchId={card.id} />
          )}

          {!checklistLoading && !checklist && !generateChecklist.isPending && (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              No checklist generated yet. Click "Generate" to create one from the branch diff.
            </p>
          )}

          {generateChecklist.isError && (
            <p className="mt-2 text-sm text-red-600 dark:text-red-400">
              Failed to generate checklist. Make sure the repository is accessible.
            </p>
          )}
        </div>

        {/* Test execution section */}
        <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-700 dark:text-slate-300">
              <FlaskConical className="h-4 w-4" />
              Automated Tests
            </h3>
            <div className="flex gap-2">
              <button
                onClick={() => generateTests.mutate()}
                disabled={generateTests.isPending}
                className="flex items-center gap-1 rounded bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
              >
                {generateTests.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Generate Tests
              </button>
              <button
                onClick={() => runTests.mutate()}
                disabled={runTests.isPending}
                className="flex items-center gap-1 rounded bg-emerald-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {runTests.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
                Run Tests
              </button>
            </div>
          </div>

          {generateTests.isSuccess && (
            <div className="mb-3 rounded border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400">
              Generated {generateTests.data.test_count} tests in {generateTests.data.files_generated} file(s)
              {generateTests.data.warnings.length > 0 && (
                <ul className="mt-1 list-inside list-disc text-amber-600 dark:text-amber-400">
                  {generateTests.data.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              )}
            </div>
          )}

          {generateTests.isError && (
            <p className="mb-3 text-xs text-red-600 dark:text-red-400">
              Test generation failed. Ensure the repository is accessible and has discoverable routes.
            </p>
          )}

          {runTests.isError && (
            <p className="mb-3 text-xs text-red-600 dark:text-red-400">
              Test run failed. Generate tests first, then try again.
            </p>
          )}

          {/* Test runs list */}
          {testRuns.length > 0 && (
            <div className="space-y-2">
              {testRuns.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between rounded border border-slate-200 px-3 py-2 text-sm dark:border-slate-700"
                >
                  <div>
                    <span className="font-medium text-slate-700 dark:text-slate-300">{run.suite_type}</span>
                    <span className="ml-2 text-xs text-slate-400">{new Date(run.run_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-emerald-600 dark:text-emerald-400">{run.passed} passed</span>
                    {run.failed > 0 && <span className="text-red-600 dark:text-red-400">{run.failed} failed</span>}
                    {run.skipped > 0 && <span className="text-slate-400">{run.skipped} skipped</span>}
                    {run.promoted_to_regression ? (
                      <span className="rounded bg-indigo-100 px-1.5 py-0.5 font-medium text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400">
                        Promoted
                      </span>
                    ) : (
                      <button
                        onClick={() => promoteRun.mutate(run.id)}
                        disabled={promoteRun.isPending}
                        className="flex items-center gap-0.5 text-indigo-600 hover:underline disabled:opacity-50 dark:text-indigo-400"
                        title="Promote to regression suite"
                      >
                        <ArrowUpRight className="h-3 w-3" />
                        Promote
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {testRuns.length === 0 && !runTests.isPending && (
            <p className="text-sm text-slate-400 dark:text-slate-500">
              No test runs yet. Generate tests from the branch diff, then run them.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
