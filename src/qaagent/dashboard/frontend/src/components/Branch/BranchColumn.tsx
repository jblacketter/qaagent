import { clsx } from "clsx";
import { BranchCardComponent } from "./BranchCardComponent";
import type { BranchCard } from "../../types";

const STAGE_STYLES: Record<string, { bg: string; dot: string; label: string }> = {
  created:   { bg: "bg-slate-50 dark:bg-slate-900/50",  dot: "bg-slate-400",   label: "Created" },
  active:    { bg: "bg-blue-50/50 dark:bg-blue-950/20", dot: "bg-blue-500",    label: "Active" },
  in_review: { bg: "bg-amber-50/50 dark:bg-amber-950/20", dot: "bg-amber-500", label: "In Review" },
  merged:    { bg: "bg-indigo-50/50 dark:bg-indigo-950/20", dot: "bg-indigo-500", label: "Merged" },
  qa:        { bg: "bg-orange-50/50 dark:bg-orange-950/20", dot: "bg-orange-500", label: "QA" },
  released:  { bg: "bg-emerald-50/50 dark:bg-emerald-950/20", dot: "bg-emerald-500", label: "Released" },
};

interface BranchColumnProps {
  stage: string;
  cards: BranchCard[];
  selectedId: number | null;
  onSelect: (card: BranchCard) => void;
}

export function BranchColumn({ stage, cards, selectedId, onSelect }: BranchColumnProps) {
  const style = STAGE_STYLES[stage] || STAGE_STYLES.created;

  return (
    <div className={clsx("flex min-w-[220px] max-w-[280px] flex-1 flex-col rounded-lg border border-slate-200 dark:border-slate-700", style.bg)}>
      {/* Column header */}
      <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2.5 dark:border-slate-700">
        <span className={clsx("h-2.5 w-2.5 rounded-full", style.dot)} />
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">{style.label}</h3>
        <span className="ml-auto rounded-full bg-slate-200 px-1.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-700 dark:text-slate-400">
          {cards.length}
        </span>
      </div>

      {/* Cards */}
      <div className="flex flex-col gap-2 overflow-y-auto p-2" style={{ maxHeight: "calc(100vh - 320px)" }}>
        {cards.length === 0 && (
          <p className="py-4 text-center text-xs text-slate-400 dark:text-slate-500">No branches</p>
        )}
        {cards.map((card) => (
          <BranchCardComponent
            key={card.id}
            card={card}
            onClick={() => onSelect(card)}
            isSelected={selectedId === card.id}
          />
        ))}
      </div>
    </div>
  );
}
