import { ReactNode } from "react";
import { clsx } from "clsx";

interface AlertProps {
  variant?: "info" | "warning" | "error";
  title?: string;
  children: ReactNode;
}

const variants: Record<NonNullable<AlertProps["variant"]>, { container: string; text: string; border: string; background: string }> = {
  info: {
    container: "border-sky-200 dark:border-sky-900/40",
    text: "text-sky-800 dark:text-sky-200",
    border: "border-sky-200 dark:border-sky-900/40",
    background: "bg-sky-50 dark:bg-sky-900/20",
  },
  warning: {
    container: "border-amber-200 dark:border-amber-900/40",
    text: "text-amber-800 dark:text-amber-200",
    border: "border-amber-200 dark:border-amber-900/40",
    background: "bg-amber-50 dark:bg-amber-900/20",
  },
  error: {
    container: "border-red-200 dark:border-red-900/40",
    text: "text-red-800 dark:text-red-200",
    border: "border-red-200 dark:border-red-900/40",
    background: "bg-red-50 dark:bg-red-900/20",
  },
};

export function Alert({ variant = "info", title, children }: AlertProps) {
  const styles = variants[variant];
  return (
    <div
      className={clsx(
        "rounded-lg border p-4 text-sm",
        styles.container,
        styles.background,
        styles.text,
      )}
      role={variant === "error" ? "alert" : undefined}
    >
      {title ? <p className="font-semibold">{title}</p> : null}
      <div className={title ? "mt-1" : undefined}>{children}</div>
    </div>
  );
}
