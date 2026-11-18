import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { api } from '../api/endpoints';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  BarChart3,
  Network,
  AlertCircle,
  FileCode2,
  TrendingUp,
  Cpu,
} from 'lucide-react';

const COLORS = ['#6366f1', '#a855f7', '#ec4899', '#3b82f6', '#10b981', '#f59e0b'];

export const AnalyticsPage: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['repoAnalytics', repoId],
    queryFn: async () => (await api.analytics.getDashboard(repoId!)).data,
    enabled: !!repoId,
  });

  if (isLoading) return <LoadingSpinner text="Computing repository metrics..." />;
  if (!analytics) return <div className="text-white">Analytics data not available</div>;

  const issueChartData = Object.entries(analytics.issue_counts).map(([sev, count]) => ({
    severity: sev.toUpperCase(),
    count,
  }));

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="pb-6 border-b border-dark-800">
        <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-brand-400" />
          Developer Analytics & Measured Metrics
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Objective AST measurements, cyclomatic complexity distributions, and dependency metrics.
        </p>
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <span className="text-xs font-semibold uppercase text-slate-500">Total Code Volume</span>
          <div className="text-3xl font-bold text-white mt-1">
            {analytics.total_loc.toLocaleString()} LOC
          </div>
          <span className="text-xs text-slate-500">Across {analytics.total_files} files</span>
        </div>

        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <span className="text-xs font-semibold uppercase text-slate-500">Average Complexity</span>
          <div className="text-3xl font-bold text-brand-400 mt-1">
            {analytics.avg_complexity}
          </div>
          <span className="text-xs text-slate-500">Cyclomatic score per function</span>
        </div>

        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <span className="text-xs font-semibold uppercase text-slate-500">Max Complexity</span>
          <div className="text-3xl font-bold text-amber-400 mt-1">
            {analytics.max_complexity}
          </div>
          <span className="text-xs text-slate-500">Highest branching function</span>
        </div>

        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <span className="text-xs font-semibold uppercase text-slate-500">Circular Dependencies</span>
          <div className={`text-3xl font-bold mt-1 ${
            (analytics.dependency_health?.circular_dependencies || 0) > 0 ? 'text-rose-400' : 'text-emerald-400'
          }`}>
            {analytics.dependency_health?.circular_dependencies || 0}
          </div>
          <span className="text-xs text-slate-500">Cycle graph detection</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Language Breakdown */}
        <div className="bg-dark-900 border border-dark-800 rounded-xl p-6">
          <h3 className="text-base font-semibold text-white mb-4">Language Composition</h3>
          <div className="h-64 flex items-center justify-center">
            {analytics.languages && analytics.languages.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={analytics.languages}
                    dataKey="loc"
                    nameKey="language"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={(entry) => `${entry.language} (${entry.percentage}%)`}
                  >
                    {analytics.languages.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0b0f19', borderColor: '#222f4c' }}
                    itemStyle={{ color: '#fff' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <span className="text-slate-500 text-sm">No language data available</span>
            )}
          </div>
        </div>

        {/* Issue Counts by Severity */}
        <div className="bg-dark-900 border border-dark-800 rounded-xl p-6">
          <h3 className="text-base font-semibold text-white mb-4">Issue Severity Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={issueChartData}>
                <XAxis dataKey="severity" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0b0f19', borderColor: '#222f4c' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* High Complexity Functions Table */}
      <div className="bg-dark-900 border border-dark-800 rounded-xl p-6 space-y-4">
        <h3 className="text-base font-semibold text-white">Top Complex Functions (Refactoring Targets)</h3>
        {analytics.complexity_details && analytics.complexity_details.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-dark-950 text-slate-400 uppercase border-b border-dark-800">
                <tr>
                  <th className="p-3">File Path</th>
                  <th className="p-3">Function Name</th>
                  <th className="p-3">Cyclomatic Complexity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-800 font-mono">
                {analytics.complexity_details.map((c, i) => (
                  <tr key={i} className="hover:bg-dark-800/40">
                    <td className="p-3 text-slate-300">{c.file_path}</td>
                    <td className="p-3 text-brand-400 font-semibold">{c.function_name}</td>
                    <td className="p-3">
                      <span className={`px-2 py-0.5 rounded font-semibold ${
                        c.cyclomatic_complexity >= 10 ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'
                      }`}>
                        {c.cyclomatic_complexity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-slate-500 text-xs">All functions have standard low complexity (&lt;5).</p>
        )}
      </div>
    </div>
  );
};
