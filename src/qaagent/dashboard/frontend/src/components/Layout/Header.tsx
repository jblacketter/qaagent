import { Menu, LogOut } from "lucide-react";
import { Link } from "react-router-dom";
import { ThemeToggle } from "./ThemeToggle";

interface HeaderProps {
  onToggleMobileNav: () => void;
  isMobileNavOpen: boolean;
}

export function Header({ onToggleMobileNav, isMobileNavOpen }: HeaderProps) {
  const handleLogout = async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  };

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-3">
        <button
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={isMobileNavOpen}
          onClick={onToggleMobileNav}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-transparent text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-500 dark:text-slate-200 dark:hover:bg-slate-800 md:hidden"
        >
          <Menu size={20} />
        </button>
        <div>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">QA Agent Dashboard</h1>
          <p className="hidden text-sm text-slate-500 dark:text-slate-400 sm:block">
            Quality insights and risk prioritization at a glance
          </p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Link
          to="/settings"
          className="hidden rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-500 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800 md:inline-flex"
        >
          Settings
        </Link>
        <ThemeToggle />
        <button
          type="button"
          onClick={handleLogout}
          title="Log out"
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-transparent text-slate-500 transition hover:bg-slate-100 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-200"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
