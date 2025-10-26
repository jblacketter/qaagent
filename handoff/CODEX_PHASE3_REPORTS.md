# Handoff to Codex: Sprint 3 Phase 3 - Reports & Export

**Date**: 2025-10-25
**From**: Claude + User
**To**: Codex
**Status**: Ready to implement
**Priority**: HIGH - Production feature

---

## Congratulations on Phase 2! 🎉

**Your Phase 1 & 2 work**: 9.5/10 - Outstanding!

Phase 2 is complete and tested. Now we're moving to a critical production feature: **Reports & Export**.

---

## Phase 3 Overview: Reports & Export

**Goal**: Allow users to export dashboard data and generate professional reports for sharing with stakeholders.

**Why this matters**:
- **Executive stakeholders** need one-page summaries (not full dashboards)
- **Engineers** need detailed technical reports
- **Data analysis** requires CSV/JSON exports
- **Compliance/audit** needs PDF documentation

**User story**:
> "As a QA Manager, I want to export a PDF report of our latest analysis so I can share it with leadership in our weekly meeting."

---

## What to Build

### 1. **Export Button UI** (All Pages)
Add export functionality to key pages

### 2. **CSV/JSON Exports** (Quick wins)
Export raw data for analysis in Excel/scripts

### 3. **PDF Reports** (Main feature)
Generate professional PDF reports with charts and data

### 4. **Report Templates**
- Executive Summary (1 page)
- Technical Report (detailed)

---

## Task 1: Export Buttons (S3-09)

**Goal**: Add export buttons to Dashboard, Runs, Risks, Trends, and CUJ pages

### Implementation

#### A. Create Export Menu Component

**New file**: `src/components/ui/ExportMenu.tsx`

```typescript
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
```

#### B. Add Export Buttons to Pages

**Example: Dashboard.tsx**

Add to header section (after title, before content):

```typescript
import { ExportMenu } from "../components/ui/ExportMenu";

// Inside DashboardPage component:
const handleExportPDF = () => {
  // Will implement in next task
  console.log("Export PDF");
};

const handleExportCSV = () => {
  exportDataAsCSV(runsQuery.data?.runs ?? [], "dashboard-runs");
};

const handleExportJSON = () => {
  exportDataAsJSON({
    runs: runsQuery.data?.runs,
    risks: risksQuery.data,
    coverage: coverageQuery.data,
  }, "dashboard-data");
};

// In JSX:
<div className="flex items-center justify-between">
  <h1>Dashboard</h1>
  <ExportMenu
    onExportPDF={handleExportPDF}
    onExportCSV={handleExportCSV}
    onExportJSON={handleExportJSON}
    disabled={runsQuery.isLoading}
  />
</div>
```

**Apply to all pages**:
- Dashboard
- Runs
- Risks
- Trends
- CUJ Coverage

---

## Task 2: CSV/JSON Export Utilities (S3-10)

**Goal**: Create utility functions to export data as CSV and JSON

### Implementation

**New file**: `src/utils/export.ts`

```typescript
/**
 * Export data as CSV file
 */
export function exportDataAsCSV<T extends Record<string, any>>(
  data: T[],
  filename: string
): void {
  if (!data.length) {
    alert("No data to export");
    return;
  }

  // Get all keys from first object
  const headers = Object.keys(data[0]);

  // Create CSV content
  const csvRows = [
    headers.join(","), // Header row
    ...data.map(row =>
      headers.map(header => {
        const value = row[header];
        // Escape commas and quotes
        const escaped = String(value ?? "").replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(",")
    )
  ];

  const csvContent = csvRows.join("\n");
  downloadFile(csvContent, `${filename}.csv`, "text/csv");
}

/**
 * Export data as JSON file
 */
export function exportDataAsJSON(data: any, filename: string): void {
  const jsonContent = JSON.stringify(data, null, 2);
  downloadFile(jsonContent, `${filename}.json`, "application/json");
}

/**
 * Helper to trigger file download
 */
function downloadFile(content: string, filename: string, type: string): void {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Flatten nested objects for CSV export
 */
export function flattenForCSV<T extends Record<string, any>>(
  data: T[]
): Record<string, any>[] {
  return data.map(item => {
    const flat: Record<string, any> = {};

    Object.keys(item).forEach(key => {
      const value = item[key];

      if (value && typeof value === "object" && !Array.isArray(value)) {
        // Flatten nested object
        Object.keys(value).forEach(subKey => {
          flat[`${key}_${subKey}`] = value[subKey];
        });
      } else if (Array.isArray(value)) {
        // Convert arrays to comma-separated strings
        flat[key] = value.join("; ");
      } else {
        flat[key] = value;
      }
    });

    return flat;
  });
}
```

---

## Task 3: PDF Report Generation (S3-11)

**Goal**: Generate professional PDF reports with charts and data

### Dependencies

Install PDF generation library:

```bash
npm install jspdf jspdf-autotable
npm install --save-dev @types/jspdf
```

### Implementation

**New file**: `src/utils/pdf-report.ts`

```typescript
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

interface ReportMetadata {
  title: string;
  runId: string;
  createdAt: string;
  targetName: string;
}

interface ReportData {
  metadata: ReportMetadata;
  summary: {
    totalRuns: number;
    highRisks: number;
    avgCoverage: number;
    safeComponents: number;
  };
  topRisks: Array<{
    component: string;
    score: number;
    band: string;
    title: string;
  }>;
  coverageGaps?: Array<{
    component: string;
    coverage: number;
  }>;
}

/**
 * Generate Executive Summary PDF (1 page)
 */
export function generateExecutiveSummary(data: ReportData): void {
  const doc = new jsPDF();

  // Title
  doc.setFontSize(20);
  doc.text("QA Agent - Executive Summary", 14, 20);

  // Metadata
  doc.setFontSize(10);
  doc.setTextColor(100);
  doc.text(`Run: ${data.metadata.runId}`, 14, 30);
  doc.text(`Target: ${data.metadata.targetName}`, 14, 35);
  doc.text(`Generated: ${new Date(data.metadata.createdAt).toLocaleDateString()}`, 14, 40);

  doc.setTextColor(0);

  // Summary Metrics
  doc.setFontSize(14);
  doc.text("Key Metrics", 14, 50);

  const metrics = [
    ["Total Runs", data.summary.totalRuns.toString()],
    ["High Risk Components", data.summary.highRisks.toString()],
    ["Average Coverage", `${data.summary.avgCoverage}%`],
    ["Safe Components", data.summary.safeComponents.toString()],
  ];

  autoTable(doc, {
    startY: 55,
    head: [["Metric", "Value"]],
    body: metrics,
    theme: "grid",
    headStyles: { fillColor: [71, 85, 105] }, // slate-600
  });

  // Top Risks
  const finalY = (doc as any).lastAutoTable.finalY || 100;
  doc.setFontSize(14);
  doc.text("Top Risks", 14, finalY + 10);

  const riskRows = data.topRisks.slice(0, 5).map(risk => [
    risk.component,
    risk.score.toFixed(1),
    risk.band,
    risk.title,
  ]);

  autoTable(doc, {
    startY: finalY + 15,
    head: [["Component", "Score", "Band", "Title"]],
    body: riskRows,
    theme: "grid",
    headStyles: { fillColor: [71, 85, 105] },
    columnStyles: {
      1: { cellWidth: 20 },
      2: { cellWidth: 15 },
    },
  });

  // Footer
  const pageCount = (doc.internal as any).getNumberOfPages();
  doc.setFontSize(8);
  doc.setTextColor(150);
  doc.text(
    `Generated by QA Agent - Page ${pageCount}`,
    14,
    doc.internal.pageSize.height - 10
  );

  // Download
  doc.save(`qa-agent-executive-summary-${data.metadata.runId}.pdf`);
}

/**
 * Generate Technical Report PDF (multi-page, detailed)
 */
export function generateTechnicalReport(data: ReportData): void {
  const doc = new jsPDF();

  // Title Page
  doc.setFontSize(24);
  doc.text("QA Agent", 14, 40);
  doc.setFontSize(18);
  doc.text("Technical Analysis Report", 14, 50);

  doc.setFontSize(12);
  doc.text(`Run ID: ${data.metadata.runId}`, 14, 70);
  doc.text(`Target: ${data.metadata.targetName}`, 14, 77);
  doc.text(`Date: ${new Date(data.metadata.createdAt).toLocaleDateString()}`, 14, 84);

  // Page 2: Summary Metrics
  doc.addPage();
  doc.setFontSize(16);
  doc.text("1. Summary Metrics", 14, 20);

  const summaryData = [
    ["Total Analysis Runs", data.summary.totalRuns.toString()],
    ["High Risk Components (P0/P1)", data.summary.highRisks.toString()],
    ["Average Test Coverage", `${data.summary.avgCoverage}%`],
    ["Safe Components (P2/P3)", data.summary.safeComponents.toString()],
  ];

  autoTable(doc, {
    startY: 30,
    head: [["Metric", "Value"]],
    body: summaryData,
    theme: "striped",
    headStyles: { fillColor: [71, 85, 105] },
  });

  // Page 3: Risk Analysis
  doc.addPage();
  doc.setFontSize(16);
  doc.text("2. Risk Analysis", 14, 20);

  doc.setFontSize(12);
  doc.text("All risks identified in this analysis:", 14, 30);

  const allRiskRows = data.topRisks.map(risk => [
    risk.component,
    risk.score.toFixed(1),
    risk.band,
    risk.severity || "N/A",
    risk.title,
  ]);

  autoTable(doc, {
    startY: 35,
    head: [["Component", "Score", "Band", "Severity", "Description"]],
    body: allRiskRows,
    theme: "striped",
    headStyles: { fillColor: [71, 85, 105] },
    columnStyles: {
      0: { cellWidth: 40 },
      1: { cellWidth: 20 },
      2: { cellWidth: 15 },
      3: { cellWidth: 20 },
    },
  });

  // Page 4: Coverage Gaps (if data available)
  if (data.coverageGaps && data.coverageGaps.length > 0) {
    doc.addPage();
    doc.setFontSize(16);
    doc.text("3. Coverage Gaps", 14, 20);

    doc.setFontSize(12);
    doc.text("Components with coverage below target (80%):", 14, 30);

    const coverageRows = data.coverageGaps.map(gap => [
      gap.component,
      `${Math.round(gap.coverage * 100)}%`,
      `${Math.round((0.8 - gap.coverage) * 100)}%`,
    ]);

    autoTable(doc, {
      startY: 35,
      head: [["Component", "Current Coverage", "Gap to Target"]],
      body: coverageRows,
      theme: "striped",
      headStyles: { fillColor: [71, 85, 105] },
    });
  }

  // Footer on all pages
  const pageCount = (doc.internal as any).getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150);
    doc.text(
      `QA Agent Technical Report - Page ${i} of ${pageCount}`,
      14,
      doc.internal.pageSize.height - 10
    );
  }

  // Download
  doc.save(`qa-agent-technical-report-${data.metadata.runId}.pdf`);
}

/**
 * Generate Trends Report PDF
 */
export function generateTrendsReport(trendsData: any[]): void {
  const doc = new jsPDF();

  // Title
  doc.setFontSize(20);
  doc.text("QA Agent - Trends Report", 14, 20);

  doc.setFontSize(10);
  doc.text(`Generated: ${new Date().toLocaleDateString()}`, 14, 30);

  // Trend summary table
  doc.setFontSize(14);
  doc.text("Quality Trends Over Time", 14, 40);

  const trendRows = trendsData.map(point => [
    point.run_id,
    new Date(point.created_at).toLocaleDateString(),
    point.average_coverage ? `${Math.round(point.average_coverage * 100)}%` : "N/A",
    point.high_risk_count?.toString() || "0",
    point.average_risk_score?.toFixed(1) || "N/A",
  ]);

  autoTable(doc, {
    startY: 45,
    head: [["Run ID", "Date", "Avg Coverage", "High Risks", "Avg Risk Score"]],
    body: trendRows,
    theme: "grid",
    headStyles: { fillColor: [71, 85, 105] },
  });

  doc.save(`qa-agent-trends-${new Date().toISOString().split('T')[0]}.pdf`);
}
```

### Usage in Components

**Dashboard.tsx**:

```typescript
import { generateExecutiveSummary, generateTechnicalReport } from "../utils/pdf-report";

const handleExportPDF = () => {
  const reportData = {
    metadata: {
      title: "Dashboard Summary",
      runId: latest?.run_id || "N/A",
      createdAt: latest?.created_at || new Date().toISOString(),
      targetName: latest?.target?.name || "Unknown",
    },
    summary: {
      totalRuns: runsQuery.data?.total ?? 0,
      highRisks: highRiskCount,
      avgCoverage: avgCoverage ?? 0,
      safeComponents: (risksQuery.data?.length ?? 0) - highRiskCount,
    },
    topRisks: topRisks,
    coverageGaps: coverageGaps.map(gap => ({
      component: gap.component,
      coverage: gap.value,
    })),
  };

  // Ask user which report type
  const reportType = window.confirm(
    "Click OK for Executive Summary (1 page)\nClick Cancel for Technical Report (detailed)"
  );

  if (reportType) {
    generateExecutiveSummary(reportData);
  } else {
    generateTechnicalReport(reportData);
  }
};
```

---

## Task 4: Report Selection Dialog (S3-12)

**Goal**: Better UX for choosing report type

### Implementation

**New file**: `src/components/ReportDialog.tsx`

```typescript
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
```

**Usage**:

```typescript
const [reportDialogOpen, setReportDialogOpen] = useState(false);

const handleGenerateReport = (type: "executive" | "technical") => {
  if (type === "executive") {
    generateExecutiveSummary(reportData);
  } else {
    generateTechnicalReport(reportData);
  }
};

// In JSX:
<ExportMenu
  onExportPDF={() => setReportDialogOpen(true)}
  ...
/>

<ReportDialog
  isOpen={reportDialogOpen}
  onClose={() => setReportDialogOpen(false)}
  onGenerate={handleGenerateReport}
/>
```

---

## Testing Checklist

Before marking complete:

### CSV/JSON Exports
- [ ] Export risks as CSV from Risks page
- [ ] Export runs as JSON from Runs page
- [ ] Open CSV in Excel - columns should align
- [ ] Open JSON in text editor - should be valid JSON

### PDF Reports
- [ ] Generate Executive Summary from Dashboard
- [ ] Verify PDF has title, metadata, metrics table
- [ ] Verify top risks table in PDF
- [ ] Generate Technical Report
- [ ] Verify multi-page PDF with all sections
- [ ] Check footer on all pages
- [ ] Test dark mode (should not affect PDF output)

### Report Dialog
- [ ] Dialog opens when clicking "Export PDF"
- [ ] Can select between Executive and Technical
- [ ] Cancel button closes dialog
- [ ] Generate button creates correct report type
- [ ] Dialog closes after generation

### Browser Compatibility
- [ ] Test in Chrome (primary)
- [ ] Test in Safari (if on Mac)
- [ ] Test in Firefox (if available)

---

## Implementation Order

1. **ExportMenu component** (30 min)
2. **CSV/JSON utilities** (30 min)
3. **Apply ExportMenu to all pages** (1 hour)
4. **Install jsPDF and autotable** (5 min)
5. **PDF utilities** (2 hours)
6. **ReportDialog** (1 hour)
7. **Testing** (1 hour)

**Total estimated**: 6-7 hours

---

## Expected Files

**New files**:
- `src/components/ui/ExportMenu.tsx`
- `src/components/ReportDialog.tsx`
- `src/utils/export.ts`
- `src/utils/pdf-report.ts`

**Modified files**:
- `src/pages/Dashboard.tsx`
- `src/pages/Runs.tsx`
- `src/pages/Risks.tsx`
- `src/pages/Trends.tsx`
- `src/pages/CujCoverage.tsx`
- `package.json` (add jspdf dependencies)

---

## Quality Standards

Maintain your 9.5/10 quality:

- ✅ TypeScript types for all functions
- ✅ Dark mode support for UI components
- ✅ Loading states during PDF generation
- ✅ Error handling (try/catch for file operations)
- ✅ Accessibility (ARIA labels, keyboard nav)
- ✅ Consistent styling with existing components

---

## After Phase 3

Once reports are working, we'll move to **Phase 4: AI Summaries**:
- Integrate Ollama for local LLM
- Generate AI-powered risk summaries
- Smart recommendations with evidence citations
- Privacy-preserving (all runs locally)

---

## Questions?

If anything is unclear:

1. **PDF formatting**: jsPDF docs at https://github.com/parallax/jsPDF
2. **Table styling**: jspdf-autotable docs at https://github.com/simonbengtsson/jsPDF-AutoTable
3. **CSV format**: Standard RFC 4180 format
4. **Report content**: Focus on clarity for non-technical stakeholders in Executive Summary

---

Good luck! Your work has been excellent so far. Reports are a critical production feature - users will love being able to share PDFs with leadership. 📄🚀
