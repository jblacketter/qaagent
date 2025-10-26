import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { FolderOpen, Github, Loader2 } from "lucide-react";
import { apiClient } from "../services/api";

export function RepositorySetupPage() {
  const navigate = useNavigate();
  const [repoPath, setRepoPath] = useState("");
  const [repoType, setRepoType] = useState<"local" | "github">("local");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Analysis options
  const [options, setOptions] = useState({
    testCoverage: true,
    security: true,
    performance: true,
    codeQuality: true,
    testCases: false, // v2.0 feature
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!repoPath.trim()) {
      setError("Please enter a repository path or URL");
      return;
    }

    setIsAnalyzing(true);

    // Extract repository name from path
    const repoName = repoPath.split("/").pop() || "repository";

    try {

      // Create repository
      const repo = await apiClient.createRepository({
        name: repoName,
        path: repoPath,
        repo_type: repoType,
        analysis_options: options,
      });

      // Trigger analysis
      await apiClient.analyzeRepository(repo.id);

      // Navigate to repositories list
      navigate("/repositories");
    } catch (error) {
      console.error("Failed to start analysis:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to start analysis. Please try again.";

      // Check if it's a duplicate repository error
      if (errorMessage.includes("already exists")) {
        setError(`Repository "${repoName}" already exists. You can view it in your repositories list.`);
      } else {
        setError(errorMessage);
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const toggleOption = (key: keyof typeof options) => {
    setOptions(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto max-w-3xl px-4 py-12">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            Add Repository for Analysis
          </h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Configure your repository and select what to analyze
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-8">
          <div className="rounded-lg border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            {/* Repository Type Toggle */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Repository Type
              </label>
              <div className="mt-2 flex gap-4">
                <button
                  type="button"
                  onClick={() => setRepoType("local")}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-lg border-2 px-4 py-3 text-sm font-medium transition ${
                    repoType === "local"
                      ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-600 dark:bg-blue-900/20 dark:text-blue-300"
                      : "border-slate-200 text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-600"
                  }`}
                >
                  <FolderOpen size={18} />
                  Local Path
                </button>
                <button
                  type="button"
                  onClick={() => setRepoType("github")}
                  className={`flex flex-1 items-center justify-center gap-2 rounded-lg border-2 px-4 py-3 text-sm font-medium transition ${
                    repoType === "github"
                      ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-600 dark:bg-blue-900/20 dark:text-blue-300"
                      : "border-slate-200 text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:text-slate-300 dark:hover:border-slate-600"
                  }`}
                >
                  <Github size={18} />
                  GitHub URL
                </button>
              </div>
            </div>

            {/* Repository Path Input */}
            <div className="mb-6">
              <label htmlFor="repoPath" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                {repoType === "local" ? "Repository Path" : "GitHub Repository URL"}
              </label>
              <input
                type="text"
                id="repoPath"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                placeholder={
                  repoType === "local"
                    ? "/Users/you/projects/your-repo"
                    : "https://github.com/username/repository"
                }
                className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-4 py-3 text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder-slate-500"
                disabled={isAnalyzing}
              />
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-500">
                {repoType === "local"
                  ? "Enter the absolute path to your local repository"
                  : "Enter the full GitHub repository URL"}
              </p>
            </div>

            {/* Analysis Options */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                What to Analyze
              </label>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
                Select which analyses to run on your repository
              </p>

              <div className="mt-4 space-y-3">
                <CheckboxOption
                  id="testCoverage"
                  checked={options.testCoverage}
                  onChange={() => toggleOption("testCoverage")}
                  label="Test Coverage"
                  description="Analyze code coverage from your test suite"
                  disabled={isAnalyzing}
                />
                <CheckboxOption
                  id="security"
                  checked={options.security}
                  onChange={() => toggleOption("security")}
                  label="Security Vulnerabilities"
                  description="Scan for security issues and dependency vulnerabilities"
                  disabled={isAnalyzing}
                />
                <CheckboxOption
                  id="performance"
                  checked={options.performance}
                  onChange={() => toggleOption("performance")}
                  label="Performance Issues"
                  description="Identify potential performance bottlenecks"
                  disabled={isAnalyzing}
                />
                <CheckboxOption
                  id="codeQuality"
                  checked={options.codeQuality}
                  onChange={() => toggleOption("codeQuality")}
                  label="Code Quality"
                  description="Analyze code complexity, maintainability, and best practices"
                  disabled={isAnalyzing}
                />
                <CheckboxOption
                  id="testCases"
                  checked={options.testCases}
                  onChange={() => toggleOption("testCases")}
                  label="Test Cases (Coming in v2.0)"
                  description="Generate test case recommendations"
                  disabled={true}
                  comingSoon
                />
              </div>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900/50 dark:bg-red-900/20">
              <p className="text-sm text-red-800 dark:text-red-200 mb-2">{error}</p>
              {error.includes("already exists") && (
                <Link
                  to="/repositories"
                  className="inline-flex items-center gap-1 text-sm font-medium text-red-900 hover:text-red-700 dark:text-red-100 dark:hover:text-red-300"
                >
                  View My Repositories →
                </Link>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="mt-6 flex justify-end gap-4">
            <button
              type="button"
              onClick={() => navigate("/")}
              disabled={isAnalyzing}
              className="rounded-lg border border-slate-300 px-6 py-3 font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isAnalyzing || !repoPath.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Starting Analysis...
                </>
              ) : (
                "Start Analysis"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface CheckboxOptionProps {
  id: string;
  checked: boolean;
  onChange: () => void;
  label: string;
  description: string;
  disabled?: boolean;
  comingSoon?: boolean;
}

function CheckboxOption({ id, checked, onChange, label, description, disabled, comingSoon }: CheckboxOptionProps) {
  return (
    <div className="flex items-start gap-3">
      <input
        type="checkbox"
        id={id}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="mt-1 h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800"
      />
      <label htmlFor={id} className="flex-1 cursor-pointer">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
            {label}
          </span>
          {comingSoon && (
            <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              Coming Soon
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-500">
          {description}
        </p>
      </label>
    </div>
  );
}
