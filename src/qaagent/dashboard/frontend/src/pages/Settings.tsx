import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "../services/api";

export function SettingsPage() {
  const queryClient = useQueryClient();

  const settingsQuery = useQuery({
    queryKey: ["settings"],
    queryFn: () => apiClient.getSettings(),
  });

  const settings = settingsQuery.data;

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Settings
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Application info, authentication, and maintenance.
        </p>
      </section>

      {/* App Info */}
      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
          App Info
        </h2>
        {settings ? (
          <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <InfoItem label="Version" value={settings.version} />
            <InfoItem label="Database" value={settings.db_path} mono />
            <InfoItem label="Repositories" value={String(settings.repos_count)} />
            <InfoItem label="Runs" value={String(settings.runs_count)} />
          </dl>
        ) : (
          <p className="text-sm text-slate-400">Loading...</p>
        )}
      </section>

      {/* Authentication */}
      <section className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
          Authentication
        </h2>
        {settings ? (
          settings.auth_enabled ? (
            <AuthSection username={settings.username!} />
          ) : (
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                No admin account configured.
              </p>
              <Link
                to="/setup-admin"
                className="mt-3 inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
              >
                Set Up Admin
              </Link>
            </div>
          )
        ) : (
          <p className="text-sm text-slate-400">Loading...</p>
        )}
      </section>

      {/* Danger Zone */}
      <DangerZone onClear={() => queryClient.invalidateQueries({ queryKey: ["settings"] })} />
    </div>
  );
}

function InfoItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</dt>
      <dd
        className={`mt-1 text-sm text-slate-900 dark:text-slate-100 ${
          mono ? "break-all font-mono text-xs" : ""
        }`}
      >
        {value}
      </dd>
    </div>
  );
}

function AuthSection({ username }: { username: string }) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const changeMutation = useMutation({
    mutationFn: () => apiClient.changePassword(oldPassword, newPassword),
    onSuccess: () => {
      setMessage({ type: "success", text: "Password changed successfully." });
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    },
    onError: (err: Error) => {
      setMessage({ type: "error", text: err.message });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    if (newPassword !== confirmPassword) {
      setMessage({ type: "error", text: "New passwords do not match." });
      return;
    }
    if (newPassword.length < 8) {
      setMessage({ type: "error", text: "New password must be at least 8 characters." });
      return;
    }
    changeMutation.mutate();
  };

  return (
    <div>
      <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
        Admin: <span className="font-medium">{username}</span>
      </p>

      <h3 className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">
        Change Password
      </h3>

      <form onSubmit={handleSubmit} className="max-w-sm space-y-3">
        <input
          type="password"
          placeholder="Current password"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          required
        />
        <input
          type="password"
          placeholder="New password (min 8 characters)"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          required
        />
        <input
          type="password"
          placeholder="Confirm new password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
          required
        />
        <button
          type="submit"
          disabled={changeMutation.isPending}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-slate-200"
        >
          {changeMutation.isPending ? "Changing..." : "Change Password"}
        </button>
      </form>

      {message && (
        <div
          className={`mt-3 rounded-md p-3 text-sm ${
            message.type === "success"
              ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300"
              : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

function DangerZone({ onClear }: { onClear: () => void }) {
  const [showConfirm, setShowConfirm] = useState(false);

  const clearMutation = useMutation({
    mutationFn: () => apiClient.clearDatabase(),
    onSuccess: () => {
      setShowConfirm(false);
      onClear();
    },
  });

  return (
    <section className="rounded-lg border border-red-200 bg-white p-6 dark:border-red-900 dark:bg-slate-900">
      <h2 className="mb-2 text-lg font-semibold text-red-600 dark:text-red-400">
        Danger Zone
      </h2>
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Irreversible actions. Proceed with caution.
      </p>

      {!showConfirm ? (
        <button
          onClick={() => setShowConfirm(true)}
          className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-900/20"
        >
          Clear Database
        </button>
      ) : (
        <div className="space-y-3">
          <p className="text-sm font-medium text-red-600 dark:text-red-400">
            This will delete all repositories, agent configurations, and usage data. Are you sure?
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => clearMutation.mutate()}
              disabled={clearMutation.isPending}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
            >
              {clearMutation.isPending ? "Clearing..." : "Yes, Clear Everything"}
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
