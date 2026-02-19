import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Shield,
  Target,
  Activity,
  CheckCircle,
  AlertTriangle,
  TrendingUp,
  ArrowRight,
  FolderOpen,
  BookOpen,
  FileCode,
  GitBranch,
} from "lucide-react";
import { apiClient } from "../services/api";

export function LandingPage() {
  const repositoriesQuery = useQuery({
    queryKey: ["repositories"],
    queryFn: () => apiClient.getRepositories(),
  });

  const hasRepositories = (repositoriesQuery.data?.repositories?.length ?? 0) > 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="mx-auto max-w-6xl px-4 py-12">
        {/* Hero Section */}
        <div className="text-center">
          <h1 className="text-5xl font-bold text-slate-900 dark:text-slate-100">
            QA Agent
          </h1>
          <p className="mt-4 text-xl text-slate-600 dark:text-slate-400">
            QA Strategy & Risk Analysis
          </p>
          <p className="mt-2 text-base text-slate-500 dark:text-slate-500">
            Analyze your repository to identify risks, coverage gaps, and quality issues
          </p>
        </div>

        {/* Feature Cards */}
        <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <FeatureCard
            icon={<Target className="h-8 w-8" />}
            title="Test Coverage Analysis"
            description="Identify untested code paths and coverage gaps across your entire codebase with detailed component-level metrics."
            color="blue"
          />
          <FeatureCard
            icon={<Shield className="h-8 w-8" />}
            title="Security Vulnerability Scanning"
            description="Detect security issues, dependency vulnerabilities, and potential threats with automated security analysis."
            color="red"
          />
          <FeatureCard
            icon={<Activity className="h-8 w-8" />}
            title="Code Quality Metrics"
            description="Track code complexity, maintainability, and technical debt to prioritize refactoring efforts."
            color="green"
          />
          <FeatureCard
            icon={<AlertTriangle className="h-8 w-8" />}
            title="Risk Prioritization"
            description="Intelligent risk scoring based on coverage, complexity, churn, and security findings to focus on what matters."
            color="orange"
          />
          <FeatureCard
            icon={<CheckCircle className="h-8 w-8" />}
            title="Critical User Journey Coverage Tracking"
            description="Monitor test coverage across Critical User Journeys to ensure end-to-end quality for key workflows."
            color="purple"
          />
          <FeatureCard
            icon={<TrendingUp className="h-8 w-8" />}
            title="Quality Trends"
            description="Track how quality metrics evolve over time with historical analysis and trend visualization."
            color="teal"
          />
          <FeatureCard
            icon={<BookOpen className="h-8 w-8" />}
            title="Product Documentation"
            description="Auto-generate comprehensive product documentation including feature areas, integrations, architecture diagrams, and user journeys."
            color="indigo"
          />
          <FeatureCard
            icon={<FileCode className="h-8 w-8" />}
            title="Automated Test Generation"
            description="Generate unit tests for discovered routes and endpoints, with customizable base URLs and output directories."
            color="amber"
          />
          <FeatureCard
            icon={<GitBranch className="h-8 w-8" />}
            title="Branch Board"
            description="Track branches from creation to release with auto-generated test checklists, automated test execution, and a kanban-style board view."
            color="cyan"
          />
        </div>

        {/* CTA Section */}
        <div className="mt-16 text-center">
          <div className="rounded-lg border border-slate-200 bg-white p-8 shadow-lg dark:border-slate-800 dark:bg-slate-900">
            <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
              {hasRepositories ? "Continue your analysis" : "Ready to analyze your repository?"}
            </h2>
            <p className="mt-2 text-slate-600 dark:text-slate-400">
              {hasRepositories
                ? `You have ${repositoriesQuery.data?.repositories?.length} ${repositoriesQuery.data?.repositories?.length === 1 ? 'repository' : 'repositories'} configured`
                : "Get started by adding your first repository for analysis"}
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              {hasRepositories && (
                <Link
                  to="/repositories"
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-lg font-medium text-white transition hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
                >
                  <FolderOpen size={20} />
                  View My Repositories
                </Link>
              )}
              <Link
                to="/setup"
                className={`inline-flex items-center gap-2 rounded-lg px-6 py-3 text-lg font-medium transition ${
                  hasRepositories
                    ? "border-2 border-blue-600 text-blue-600 hover:bg-blue-50 dark:border-blue-500 dark:text-blue-400 dark:hover:bg-blue-900/20"
                    : "bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
                }`}
              >
                {hasRepositories ? "Add Another Repository" : "Get Started"}
                <ArrowRight size={20} />
              </Link>
            </div>
          </div>
        </div>

        {/* Value Proposition */}
        <div className="mt-12 rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            QA Agent automates the initial repository analysis phase of creating a comprehensive QA strategy document.
            Instead of manually reviewing code, dependencies, and test coverage, QA Agent provides instant insights into:
          </p>
          <ul className="mt-4 space-y-2 text-sm text-slate-600 dark:text-slate-400">
            <li className="flex items-start gap-2">
              <CheckCircle size={16} className="mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
              <span>What areas of the codebase are high-risk and need immediate attention</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle size={16} className="mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
              <span>Where test coverage is lacking and which components are untested</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle size={16} className="mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
              <span>Security vulnerabilities and dependency issues that need resolution</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle size={16} className="mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
              <span>How quality metrics are trending over time as you make improvements</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle size={16} className="mt-0.5 flex-shrink-0 text-green-600 dark:text-green-400" />
              <span>Branch lifecycle tracking with auto-generated test checklists and automated test execution</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  color: "blue" | "red" | "green" | "orange" | "purple" | "teal" | "indigo" | "amber" | "cyan";
}

function FeatureCard({ icon, title, description, color }: FeatureCardProps) {
  const colorClasses = {
    blue: "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20",
    red: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20",
    green: "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20",
    orange: "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20",
    purple: "text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/20",
    teal: "text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20",
    indigo: "text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20",
    amber: "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20",
    cyan: "text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-900/20",
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
      <div className={`inline-flex rounded-lg p-3 ${colorClasses[color]}`}>
        {icon}
      </div>
      <h3 className="mt-4 text-lg font-semibold text-slate-900 dark:text-slate-100">
        {title}
      </h3>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        {description}
      </p>
    </div>
  );
}
