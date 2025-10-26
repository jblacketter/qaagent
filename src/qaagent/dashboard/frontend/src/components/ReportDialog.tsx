import { useState } from "react";
import { FileText, X } from "lucide-react";

interface ReportDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (type: "executive" | "technical") => void;
}

export function ReportDialog({ isOpen, onClose, onGenerate }: ReportDialogProps) {
  const [selectedType, setSelectedType] = useState<"executive" | "technical">("executive");

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start justify-between">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Generate PDF Report
          </h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X size={20} />
          </button>
        </div>

        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Choose the type of report to generate:
        </p>

        <div className="mt-4 space-y-3">
          {/* Executive Summary */}
          <button
            onClick={() => setSelectedType("executive")}
            className={`w-full rounded-lg border-2 p-4 text-left transition ${
              selectedType === "executive"
                ? "border-blue-500 bg-blue-50 dark:border-blue-600 dark:bg-blue-900/20"
                : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
            }`}
          >
            <div className="flex items-start gap-3">
              <FileText className="mt-1 text-blue-600 dark:text-blue-400" size={20} />
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                  Executive Summary
                </h3>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  One-page overview with key metrics and top risks. Perfect for leadership.
                </p>
              </div>
            </div>
          </button>

          {/* Technical Report */}
          <button
            onClick={() => setSelectedType("technical")}
            className={`w-full rounded-lg border-2 p-4 text-left transition ${
              selectedType === "technical"
                ? "border-blue-500 bg-blue-50 dark:border-blue-600 dark:bg-blue-900/20"
                : "border-slate-200 hover:border-slate-300 dark:border-slate-700 dark:hover:border-slate-600"
            }`}
          >
            <div className="flex items-start gap-3">
              <FileText className="mt-1 text-slate-600 dark:text-slate-400" size={20} />
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                  Technical Report
                </h3>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  Multi-page detailed analysis with all risks, coverage gaps, and recommendations.
                </p>
              </div>
            </div>
          </button>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onGenerate(selectedType);
              onClose();
            }}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            Generate Report
          </button>
        </div>
      </div>
    </>
  );
}
