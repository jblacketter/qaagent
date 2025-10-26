import { useState } from "react";
import { Download, FileText, FileSpreadsheet } from "lucide-react";
import { clsx } from "clsx";

interface ExportMenuProps {
  onExportPDF?: () => void;
  onExportCSV?: () => void;
  onExportJSON?: () => void;
  disabled?: boolean;
}

export function ExportMenu({ onExportPDF, onExportCSV, onExportJSON, disabled }: ExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleExport = (exportFn?: () => void) => {
    if (exportFn) {
      exportFn();
    }
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={clsx(
          "inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition",
          disabled
            ? "cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400 dark:border-slate-800 dark:bg-slate-900"
            : "border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
        )}
      >
        <Download size={16} />
        Export
      </button>

      {isOpen && !disabled && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Menu */}
          <div className="absolute right-0 top-full z-20 mt-2 w-48 rounded-md border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-800">
            {onExportPDF && (
              <button
                onClick={() => handleExport(onExportPDF)}
                className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                <FileText size={16} />
                Export as PDF
              </button>
            )}
            {onExportCSV && (
              <button
                onClick={() => handleExport(onExportCSV)}
                className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                <FileSpreadsheet size={16} />
                Export as CSV
              </button>
            )}
            {onExportJSON && (
              <button
                onClick={() => handleExport(onExportJSON)}
                className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                <FileText size={16} />
                Export as JSON
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
