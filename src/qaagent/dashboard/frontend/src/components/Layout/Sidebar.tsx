import { NavLink, useLocation, useSearchParams } from "react-router-dom";
import { clsx } from "clsx";
import {
  Home,
  FolderOpen,
  Info,
  LayoutDashboard,
  ListChecks,
  Activity,
  Settings,
  TrendingUp,
  Target,
  BookOpen,
  Bot,
  GitBranch,
} from "lucide-react";

const mainLinks = [
  { to: "/", label: "Home", icon: Home },
  { to: "/repositories", label: "Repositories", icon: FolderOpen },
  { to: "/branch-board", label: "Branch Board", icon: GitBranch },
  { to: "/about", label: "About", icon: Info },
];

const repoLinks = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/runs", label: "Runs", icon: ListChecks },
  { to: "/risks", label: "Risks", icon: Activity },
  { to: "/cuj", label: "CUJ Coverage", icon: Target },
  { to: "/trends", label: "Trends", icon: TrendingUp },
  { to: "/doc", label: "App Docs", icon: BookOpen },
  { to: "/agent", label: "AI Analysis", icon: Bot },
  { to: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  variant?: "desktop" | "mobile";
  onLinkClick?: () => void;
}

export function Sidebar({ variant = "desktop", onLinkClick }: SidebarProps = {}) {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const containerClass =
    variant === "desktop"
      ? "hidden h-full w-56 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 md:flex md:flex-col"
      : "flex h-full w-64 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900";

  // Determine if we're on a repository-specific page
  const repoPages = ["/dashboard", "/runs", "/risks", "/cuj", "/trends", "/doc", "/agent", "/settings"];
  const isRepoPage = repoPages.some(page => location.pathname.startsWith(page));

  // Extract repo context from current URL for doc links
  const repoId = searchParams.get("repo");

  const linksToShow = isRepoPage ? repoLinks : mainLinks;

  return (
    <aside className={containerClass}>
      <nav className="flex flex-1 flex-col gap-1 p-4">
        {isRepoPage && (
          <div className="mb-4 border-b border-slate-200 pb-4 dark:border-slate-800">
            <NavLink
              to="/repositories"
              className="flex items-center gap-2 text-sm font-medium text-slate-600 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
            >
              ← Back to Repositories
            </NavLink>
          </div>
        )}
        {linksToShow.map(({ to, label, icon: Icon }) => {
          // Append ?repo= to doc and agent links
          const linkTo = (to.startsWith("/doc") || to === "/agent") && repoId
            ? `${to}?repo=${encodeURIComponent(repoId)}`
            : to;

          return (
            <NavLink
              key={to}
              to={linkTo}
              end={to === "/"}
              onClick={onLinkClick}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition",
                  isActive
                    ? "bg-slate-900 text-slate-100 dark:bg-slate-100 dark:text-slate-900"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          );
        })}
      </nav>
    </aside>
  );
}
