export function AboutPage() {
  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">About QA Agent</h1>
        <p className="mt-2 text-slate-600 dark:text-slate-400">
          Version 1.0.0
        </p>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          What is QA Agent?
        </h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          QA Agent scans your repository to analyze fix risks.
        </p>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Key Features
        </h2>
        <ul className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-400">
          <li>" Test Coverage Analysis - Identify untested code paths</li>
          <li>" Security Vulnerability Scanning - Detect security issues and dependency vulnerabilities</li>
          <li>" Code Quality Metrics - Track complexity, maintainability, and technical debt</li>
          <li>" Risk Prioritization - Intelligent scoring based on multiple factors</li>
          <li>" CUJ Coverage Tracking - Monitor coverage across Critical User Journeys</li>
          <li>" Quality Trends - Track metrics over time</li>
        </ul>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Support
        </h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          For documentation, issues, or feature requests, please visit the project repository.
        </p>
      </section>
    </div>
  );
}
