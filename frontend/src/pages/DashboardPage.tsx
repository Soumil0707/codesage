import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../api/endpoints';
import { useAuthStore } from '../stores/authStore';
import { Button } from '../components/common/Button';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  FolderGit2,
  FileCode2,
  ShieldCheck,
  GraduationCap,
  Sparkles,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const { data: repos, isLoading } = useQuery({
    queryKey: ['repos'],
    queryFn: async () => {
      try {
        const res = await api.repos.list();
        return Array.isArray(res.data) ? res.data : [];
      } catch {
        return [];
      }
    },
  });

  const repoList = Array.isArray(repos) ? repos : [];
  const totalFiles = repoList.reduce((acc, r) => acc + (r.total_files || 0), 0);
  const totalLoc = repoList.reduce((acc, r) => acc + (r.total_loc || 0), 0);

  if (isLoading) return <LoadingSpinner text="Loading your dashboard..." />;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome Hero */}
      <div className="bg-gradient-to-r from-brand-900/40 via-dark-900 to-dark-900 border border-dark-800 rounded-2xl p-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 text-brand-400 text-sm font-semibold uppercase tracking-wider mb-2">
            <Sparkles className="w-4 h-4" />
            Software Intelligence Engine
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Welcome, {user?.full_name || user?.username}
          </h1>
          <p className="text-slate-400 mt-1 max-w-xl text-sm">
            Explore repository files, chat with codebase RAG, and practice technical interview questions grounded in your source code.
          </p>
        </div>
        <Link to="/repos">
          <Button size="lg" className="shadow-lg shadow-brand-500/20 whitespace-nowrap">
            <FolderGit2 className="w-4 h-4" />
            Manage Repositories
          </Button>
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Repositories</span>
            <FolderGit2 className="w-5 h-5 text-brand-400" />
          </div>
          <div className="text-3xl font-bold text-white">{repoList.length}</div>
          <p className="text-xs text-slate-500 mt-1">Indexed project codebases</p>
        </div>

        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Files</span>
            <FileCode2 className="w-5 h-5 text-indigo-400" />
          </div>
          <div className="text-3xl font-bold text-white">{totalFiles.toLocaleString()}</div>
          <p className="text-xs text-slate-500 mt-1">Parsed code documents</p>
        </div>

        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Lines of Code</span>
            <TrendingUp className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white">{totalLoc.toLocaleString()}</div>
          <p className="text-xs text-slate-500 mt-1">Syntax-analyzed LOC</p>
        </div>

        <div className="bg-dark-900 border border-dark-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Modules</span>
            <ShieldCheck className="w-5 h-5 text-purple-400" />
          </div>
          <div className="text-3xl font-bold text-white">3 Modules</div>
          <p className="text-xs text-slate-500 mt-1">Explorer, RAG Chat, Interview</p>
        </div>
      </div>

      {/* Recent Repositories Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white tracking-tight">Your Repositories</h2>
          <Link to="/repos" className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1">
            View All <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {repoList.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {repoList.slice(0, 6).map((repo) => (
              <Link
                key={repo.id}
                to={`/repos/${repo.id}`}
                className="group bg-dark-900 border border-dark-800 hover:border-brand-500/50 rounded-xl p-5 transition-all duration-200 hover:shadow-lg hover:shadow-brand-500/5 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-brand-500/10 text-brand-300 border border-brand-500/20">
                      {repo.primary_language || 'Codebase'}
                    </span>
                    <span className="text-xs text-slate-500 uppercase">{repo.source.replace('_', ' ')}</span>
                  </div>
                  <h3 className="font-semibold text-white text-base group-hover:text-brand-400 transition-colors">
                    {repo.name}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1.5 line-clamp-2">
                    {repo.description || 'Repository indexed into MySQL with syntax-aware code embeddings.'}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-dark-800/80 flex items-center justify-between text-xs text-slate-400">
                  <span>{repo.total_files} files</span>
                  <span>{repo.total_loc.toLocaleString()} LOC</span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-16 bg-dark-900 border border-dark-800 rounded-xl">
            <FolderGit2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-slate-200">No repositories yet</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
              Import a GitHub repository or safely upload a ZIP to begin analyzing your codebase.
            </p>
            <Link to="/repos">
              <Button>Add Repository</Button>
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};
