export function SettingsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Settings</h2>
      <p className="text-sm text-slate-600 dark:text-slate-300">
        Configure the dashboard by setting the <code>VITE_API_BASE_URL</code> environment variable before running
        <code>npm run dev</code>. Optional branding and theming controls will be added in later phases.
      </p>
    </div>
  );
}
