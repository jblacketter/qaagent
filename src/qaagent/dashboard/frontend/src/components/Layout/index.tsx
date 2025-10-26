import { ReactNode, useEffect, useState } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (mobileNavOpen) {
      const { style } = document.body;
      const previousOverflow = style.overflow;
      style.overflow = "hidden";
      return () => {
        style.overflow = previousOverflow;
      };
    }
    return undefined;
  }, [mobileNavOpen]);

  const toggleMobileNav = () => setMobileNavOpen((prev) => !prev);
  const closeMobileNav = () => setMobileNavOpen(false);

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-slate-950 dark:text-slate-100">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header onToggleMobileNav={toggleMobileNav} isMobileNavOpen={mobileNavOpen} />
        <main className="flex-1 overflow-y-auto bg-slate-50 p-4 dark:bg-slate-950">
          {children}
        </main>
      </div>
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden" role="dialog" aria-modal="true">
          <Sidebar variant="mobile" onLinkClick={closeMobileNav} />
          <button
            type="button"
            aria-label="Close navigation"
            onClick={closeMobileNav}
            className="flex-1 bg-black/50"
          />
        </div>
      )}
    </div>
  );
}
