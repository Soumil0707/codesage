import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  FolderGit2,
  Plus,
  Github,
  Upload,
  Trash2,
  ExternalLink,
  CheckCircle2,
  Clock,
  AlertCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';

export const ReposListPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [importTab, setImportTab] = useState<'github' | 'upload'>('github');

  // Form states
  const [githubUrl, setGithubUrl] = useState('');
  const [repoName, setRepoName] = useState('');
  const [branch, setBranch] = useState('main');
  const [githubToken, setGithubToken] = useState('');
  const [zipFile, setZipFile] = useState<File | null>(null);

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

  const createGithubMutation = useMutation({
    mutationFn: api.repos.createGithub,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos'] });
      setIsModalOpen(false);
      setGithubUrl('');
      toast.success('GitHub repository import queued!');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to import from GitHub');
    },
  });

  const uploadZipMutation = useMutation({
    mutationFn: api.repos.uploadZip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos'] });
      setIsModalOpen(false);
      setZipFile(null);
      setRepoName('');
      toast.success('ZIP repository safely uploaded and indexed!');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Upload failed');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: api.repos.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos'] });
      toast.success('Repository deleted');
    },
    onError: () => toast.error('Failed to delete repository'),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (importTab === 'github') {
      createGithubMutation.mutate({
        github_url: githubUrl,
        name: repoName || undefined,
        branch,
        github_token: githubToken || undefined,
      });
    } else {
      if (!zipFile) {
        toast.error('Please choose a ZIP file');
        return;
      }
      const fd = new FormData();
      fd.append('file', zipFile);
      fd.append('name', repoName || zipFile.name.replace('.zip', ''));
      uploadZipMutation.mutate(fd);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success"><CheckCircle2 className="w-3 h-3 mr-1" /> Indexed</Badge>;
      case 'in_progress':
        return <Badge variant="brand"><Clock className="w-3 h-3 mr-1 animate-spin" /> Ingesting</Badge>;
      case 'failed':
        return <Badge variant="critical"><AlertCircle className="w-3 h-3 mr-1" /> Failed</Badge>;
      default:
        return <Badge variant="default"><Clock className="w-3 h-3 mr-1" /> Queued</Badge>;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between pb-6 border-b border-dark-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Repositories</h1>
          <p className="text-sm text-slate-400 mt-1">Manage, ingest, and browse indexed software repositories</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)}>
          <Plus className="w-4 h-4" />
          Add Repository
        </Button>
      </div>

      {isLoading ? (
        <LoadingSpinner text="Loading repositories..." />
      ) : repoList.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {repoList.map((repo) => (
            <div
              key={repo.id}
              className="bg-dark-900 border border-dark-800 rounded-xl p-5 flex flex-col justify-between hover:border-brand-500/40 transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  {getStatusBadge(repo.indexing_status)}
                  <button
                    onClick={() => {
                      if (confirm(`Are you sure you want to delete ${repo.name}?`)) {
                        deleteMutation.mutate(repo.id);
                      }
                    }}
                    className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-dark-800 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <Link to={`/repos/${repo.id}`} className="group block">
                  <h3 className="font-semibold text-lg text-white group-hover:text-brand-400 transition-colors">
                    {repo.name}
                  </h3>
                </Link>

                <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                  {repo.description || 'Repository with full-text AST parsing and semantic vectors.'}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-dark-800 flex items-center justify-between text-xs text-slate-400">
                <span className="font-mono">{repo.primary_language || 'Mixed'}</span>
                <span>{repo.total_files} files</span>
                <span>{repo.total_loc.toLocaleString()} LOC</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-20 bg-dark-900 border border-dark-800 rounded-xl">
          <FolderGit2 className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No repositories found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
            Add your first repository to start codebase intelligence analysis.
          </p>
          <Button onClick={() => setIsModalOpen(true)}>Add Repository</Button>
        </div>
      )}

      {/* Add Repository Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Import Repository"
        maxWidth="max-w-lg"
      >
        <div className="flex border-b border-dark-800 mb-6">
          <button
            onClick={() => setImportTab('github')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              importTab === 'github'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <Github className="w-4 h-4" />
            GitHub URL
          </button>
          <button
            onClick={() => setImportTab('upload')}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              importTab === 'upload'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-white'
            }`}
          >
            <Upload className="w-4 h-4" />
            Upload ZIP Archive
          </button>
        </div>

        <form onSubmit={handleCreate} className="space-y-4">
          {importTab === 'github' ? (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1">
                  GitHub Repository URL *
                </label>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/owner/repository"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-950 border border-dark-700 rounded-lg text-sm text-white focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1">
                    Branch
                  </label>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main"
                    className="w-full px-3 py-2 bg-dark-950 border border-dark-700 rounded-lg text-sm text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1">
                    Custom Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={repoName}
                    onChange={(e) => setRepoName(e.target.value)}
                    placeholder="auto-derived"
                    className="w-full px-3 py-2 bg-dark-950 border border-dark-700 rounded-lg text-sm text-white focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1">
                  Personal Access Token (for private repos)
                </label>
                <input
                  type="password"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_••••••••••••"
                  className="w-full px-3 py-2 bg-dark-950 border border-dark-700 rounded-lg text-sm text-white focus:outline-none focus:border-brand-500"
                />
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1">
                  Repository Name *
                </label>
                <input
                  type="text"
                  required
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  placeholder="my-project"
                  className="w-full px-3 py-2 bg-dark-950 border border-dark-700 rounded-lg text-sm text-white focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1">
                  ZIP File (Max 100MB) *
                </label>
                <input
                  type="file"
                  required
                  accept=".zip"
                  onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                  className="w-full px-3 py-2 bg-dark-950 border border-dark-700 rounded-lg text-sm text-white file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-brand-600 file:text-white hover:file:bg-brand-500 cursor-pointer"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Safe ingestion with Zip-Slip path traversal defense and decompression bomb protection.
                </p>
              </div>
            </>
          )}

          <div className="pt-4 flex justify-end gap-3">
            <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={createGithubMutation.isPending || uploadZipMutation.isPending}
            >
              Start Ingestion
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
