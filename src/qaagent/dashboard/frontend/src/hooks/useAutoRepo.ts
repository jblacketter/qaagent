import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiClient } from "../services/api";

/**
 * Shared hook for pages that depend on a `?repo=` query param.
 *
 * - If `repo` is already in the URL, returns it immediately.
 * - If not, fetches `/api/repositories` and, when exactly one repo exists,
 *   auto-sets `?repo=<id>` in the URL.
 * - Returns `{ repoId, isRedirecting }` so pages can show a loading state.
 */
export function useAutoRepo() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isRedirecting, setIsRedirecting] = useState(false);

  const repoId = searchParams.get("repo") ?? undefined;

  useEffect(() => {
    if (repoId) return; // already selected

    let cancelled = false;
    setIsRedirecting(true);

    apiClient
      .getRepositories()
      .then(({ repositories }) => {
        if (cancelled) return;
        if (repositories.length === 1) {
          setSearchParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              next.set("repo", repositories[0].id);
              return next;
            },
            { replace: true },
          );
        }
        setIsRedirecting(false);
      })
      .catch(() => {
        if (!cancelled) setIsRedirecting(false);
      });

    return () => {
      cancelled = true;
    };
  }, [repoId, setSearchParams]);

  return { repoId, isRedirecting };
}
