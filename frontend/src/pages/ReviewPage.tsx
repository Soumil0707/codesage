import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  ShieldAlert,
  Play,
  CheckCircle,
  AlertTriangle,
  Info,
  Bug,
  FileCode,
  Shield,
  Layers,
} from 'lucide-react';
import toast from 'react-hot-toast';

export const ReviewPage: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  // List existing review reports
  const { data: reports, isLoading: isReportsLoading } = useQuery({
    queryKey: ['reviewReports', repoId],
    queryFn: async () => (await api.review.listReports(repoId!)).data,
    enabled: !!repoId,
  });

  // Automatically select latest report
  React.useEffect(() => {
    if (reports && reports.length > 0 && !selectedReportId) {
      setSelectedReportId(reports[0].id);
    }
  }, [reports, selectedReportId]);

  // Fetch active report details
  const { data: activeReport, isLoading: isReportLoading } = useQuery({
    queryKey: ['reviewReport', selectedReportId],
    queryFn: async () => (await api.review.getReport(selectedReportId!)).data,
    enabled: !!selectedReportId,
  });

  const startReviewMutation = useMutation({
    mutationFn: () =>
      api.review.startReview({
        repository_id: repoId!,
        review_type: 'full_analysis',
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['reviewReports', repoId] });
      setSelectedReportId(res.data.id);
      toast.success('Code review analysis completed!');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Review execution failed');
    },
  });

  const updateFindingMutation = useMutation({
    mutationFn: ({ findingId, status }: { findingId: string; status: string }) =>
      api.review.updateFindingStatus(findingId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewReport', selectedReportId] });
      toast.success('Finding status updated');
    },
  });

  const getSeverityBadge = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return <Badge variant="critical">Critical</Badge>;
      case 'high':
        return <Badge variant="high">High</Badge>;
      case 'medium':
        return <Badge variant="medium">Medium</Badge>;
      case 'low':
        return <Badge variant="low">Low</Badge>;
      default:
        return <Badge variant="default">Info</Badge>;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-dark-800 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-brand-400" />
            AI Code Review & Security Diagnostics
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic AST static analysis + security smell heuristics & verification.
          </p>
        </div>

        <Button
          onClick={() => startReviewMutation.mutate()}
          isLoading={startReviewMutation.isPending}
          className="shadow-lg shadow-brand-500/20"
        >
          <Play className="w-4 h-4 mr-1" />
          Run Full Review
        </Button>
      </div>

      {/* Reports Switcher */}
      {reports && reports.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-dark-800">
          <span className="text-xs text-slate-500 font-semibold uppercase shrink-0 mr-1">Reports:</span>
          {reports.map((r, idx) => (
            <button
              key={r.id}
              onClick={() => setSelectedReportId(r.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 flex items-center gap-2 border ${
                selectedReportId === r.id
                  ? 'bg-brand-600/20 text-brand-300 border-brand-500/40 font-semibold'
                  : 'bg-dark-900 text-slate-400 border-dark-800 hover:text-white hover:bg-dark-800'
              }`}
            >
              <span>Report #{reports.length - idx}</span>
              <span className="text-[10px] text-slate-500">
                {new Date(r.created_at).toLocaleDateString()}
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded font-bold uppercase bg-dark-950 text-slate-300 border border-dark-800">
                {r.total_issues} issues
              </span>
            </button>
          ))}
        </div>
      )}

      {isReportsLoading ? (
        <LoadingSpinner text="Loading code review diagnostics..." />
      ) : activeReport ? (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-slate-500">Total Findings</span>
              <div className="text-2xl font-bold text-white mt-1">{activeReport.total_issues}</div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-rose-400">Critical / High</span>
              <div className="text-2xl font-bold text-rose-400 mt-1">{activeReport.critical_count}</div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-amber-400">Warnings</span>
              <div className="text-2xl font-bold text-amber-400 mt-1">{activeReport.warning_count}</div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-blue-400">Informational</span>
              <div className="text-2xl font-bold text-blue-400 mt-1">{activeReport.info_count}</div>
            </div>
          </div>

          {/* Findings List */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-white">Diagnostic Findings</h2>

            {activeReport.findings && activeReport.findings.length > 0 ? (
              activeReport.findings.map((f) => (
                <div
                  key={f.id}
                  className="bg-dark-900 border border-dark-800 rounded-xl p-5 space-y-3 hover:border-dark-700 transition-colors"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      {getSeverityBadge(f.severity)}
                      <span className="text-xs font-mono font-medium text-slate-400 bg-dark-950 px-2.5 py-1 rounded border border-dark-800">
                        {f.file_path}:L{f.start_line}-L{f.end_line}
                      </span>
                      <span className="text-xs font-mono text-slate-500 uppercase">
                        [{f.rule_id || f.category}]
                      </span>
                    </div>

                    {/* Verification Status Switcher */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500">Status:</span>
                      <select
                        value={f.verification_status}
                        onChange={(e) =>
                          updateFindingMutation.mutate({
                            findingId: f.id,
                            status: e.target.value,
                          })
                        }
                        className="bg-dark-950 border border-dark-700 text-xs text-slate-300 rounded px-2 py-1 focus:outline-none focus:border-brand-500"
                      >
                        <option value="verified_defect">Verified Defect</option>
                        <option value="ai_recommendation">AI Recommendation</option>
                        <option value="false_positive">False Positive</option>
                        <option value="acknowledged">Acknowledged</option>
                      </select>
                    </div>
                  </div>

                  <h3 className="text-base font-semibold text-white">{f.title}</h3>
                  <p className="text-sm text-slate-400">{f.description}</p>

                  {f.code_snippet && (
                    <div className="bg-dark-950 p-3 rounded-lg border border-dark-800">
                      <pre className="font-mono text-xs text-slate-300 whitespace-pre-wrap">
                        {f.code_snippet}
                      </pre>
                    </div>
                  )}

                  {f.suggested_fix && (
                    <div className="bg-emerald-950/20 border border-emerald-900/40 p-3 rounded-lg">
                      <div className="text-xs font-semibold text-emerald-400 mb-1">Suggested Fix:</div>
                      <p className="text-xs text-emerald-200">{f.suggested_fix}</p>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-center py-16 bg-dark-900 border border-dark-800 rounded-xl text-slate-500">
                <CheckCircle className="w-12 h-12 text-emerald-500/50 mx-auto mb-2" />
                <p className="text-sm">No code defects detected in this review snapshot!</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="text-center py-20 bg-dark-900 border border-dark-800 rounded-xl">
          <ShieldAlert className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No review reports executed yet</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
            Run an automated review to detect secrets, complexity bottlenecks, and code smells.
          </p>
          <Button onClick={() => startReviewMutation.mutate()}>Run Code Review</Button>
        </div>
      )}
    </div>
  );
};
