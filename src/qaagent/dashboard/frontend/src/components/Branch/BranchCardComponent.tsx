import { clsx } from "clsx";
import { GitBranch, ExternalLink, FileText, GitCommit } from "lucide-react";
import type { BranchCard } from "../../types";

interface BranchCardComponentProps {
  card: BranchCard;
  onClick: () => void;
  isSelected: boolean;
}

export function BranchCardComponent({ card, onClick, isSelected }: BranchCardComponentProps) {
  // Truncate long branch names
  const displayName = card.branch_name.length > 30
    ? "..." + card.branch_name.slice(-27)
    : card.branch_name;

  return (
    <button
      onClick={onClick}
      className={clsx(
        "w-full rounded-lg border p-3 text-left transition hover:shadow-md",
        isSelected
          ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500 dark:border-blue-400 dark:bg-blue-950/30 dark:ring-blue-400"
          : "border-slate-200 bg-white hover:border-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-slate-600",
      )}
    >
      {/* Branch name */}
      <div className="flex items-center gap-1.5">
        <GitBranch className="h-3.5 w-3.5 shrink-0 text-slate-400" />
        <span className="truncate text-sm font-medium text-slate-900 dark:text-slate-100" title={card.branch_name}>
          {displayName}
        </span>
      </div>

      {/* Story link */}
      {card.story_id && (
        <div className="mt-1.5 flex items-center gap-1">
          {card.story_url ? (
            <a
              href={card.story_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-1 text-xs text-blue-600 hover:underline dark:text-blue-400"
            >
              {card.story_id}
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <span className="text-xs text-slate-500 dark:text-slate-400">{card.story_id}</span>
          )}
        </div>
      )}

      {/* Stats */}
      <div className="mt-2 flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
        {card.commit_count > 0 && (
          <span className="flex items-center gap-1">
            <GitCommit className="h-3 w-3" />
            {card.commit_count}
          </span>
        )}
        {card.files_changed > 0 && (
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            {card.files_changed} files
          </span>
        )}
      </div>

      {/* Change summary (first line) */}
      {card.change_summary && (
        <p className="mt-1.5 truncate text-xs text-slate-500 dark:text-slate-400">
          {card.change_summary.split("\n")[0]}
        </p>
      )}
    </button>
  );
}
