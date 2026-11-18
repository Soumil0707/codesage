import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { api } from '../api/endpoints';
import { CodeViewer } from '../components/common/CodeViewer';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import {
  FolderGit2,
  FileCode,
  MessageSquareCode,
  GraduationCap,
  Search,
  RefreshCw,
} from 'lucide-react';

export const RepoDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const { data: repo, isLoading: isRepoLoading } = useQuery({
    queryKey: ['repo', id],
    queryFn: async () => (await api.repos.get(id!)).data,
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.indexing_status;
      return status === 'pending' || status === 'in_progress' ? 3000 : false;
    },
  });

  const reindexMutation = useMutation({
    mutationFn: () => api.repos.reindex(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repo', id] });
      toast.success('Indexing job scheduled! Processing in background.');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to trigger indexing');
    },
  });

  const { data: files, isLoading: isFilesLoading } = useQuery({
    queryKey: ['repoFiles', id],
    queryFn: async () => (await api.repos.listFiles(id!)).data,
    enabled: !!id,
  });

  const { data: activeFile, isLoading: isFileLoading } = useQuery({
    queryKey: ['repoFile', id, selectedFileId],
    queryFn: async () => (await api.repos.getFile(id!, selectedFileId!)).data,
    enabled: !!id && !!selectedFileId,
  });

  // Automatically select first file if none selected
  React.useEffect(() => {
    if (files && files.length > 0 && !selectedFileId) {
      setSelectedFileId(files[0].id);
    }
  }, [files, selectedFileId]);

  if (isRepoLoading || isFilesLoading) {
    return <LoadingSpinner text="Loading repository code files..." />;
  }

  if (!repo) {
    return <div className="text-white">Repository not found</div>;
  }

  const filteredFiles = files?.filter((f) =>
    f.file_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header with Quick Action Bar */}
      <div className="bg-dark-900 border border-dark-800 rounded-xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-dark-800">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-white tracking-tight">{repo.name}</h1>
              <Badge variant="brand">{repo.primary_language || 'Mixed'}</Badge>
              <Badge variant={repo.indexing_status === 'completed' ? 'default' : repo.indexing_status === 'failed' ? 'critical' : 'medium'}>
                {repo.indexing_status.toUpperCase()}
              </Badge>
            </div>
            <div className="flex items-center gap-3 mt-1">
              <p className="text-xs text-slate-400">
                {repo.total_files} files • {repo.total_loc.toLocaleString()} lines of code
              </p>
              {repo.indexing_status !== 'completed' && (
                <button
                  onClick={() => reindexMutation.mutate()}
                  disabled={reindexMutation.isPending}
                  className="text-xs text-brand-400 hover:text-brand-300 underline flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${reindexMutation.isPending ? 'animate-spin' : ''}`} />
                  {repo.indexing_status === 'pending' || repo.indexing_status === 'in_progress' ? 'Indexing...' : 'Trigger Indexing'}
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Link to={`/repos/${id}/chat`}>
              <Button size="sm" variant="outline">
                <MessageSquareCode className="w-3.5 h-3.5" />
                RAG Assistant
              </Button>
            </Link>
            <Link to={`/repos/${id}/interview`}>
              <Button size="sm" variant="outline">
                <GraduationCap className="w-3.5 h-3.5" />
                Interview Engine
              </Button>
            </Link>
          </div>
        </div>

        {/* File Browser Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 mt-6">
          {/* File Tree Left Sidebar */}
          <div className="md:col-span-4 border-r border-dark-800 pr-4 space-y-3">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Filter files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 bg-dark-950 border border-dark-700 rounded-md text-xs text-white focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="max-h-[600px] overflow-y-auto space-y-1">
              {filteredFiles?.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setSelectedFileId(f.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between font-mono transition-colors ${
                    selectedFileId === f.id
                      ? 'bg-brand-600 text-white font-medium shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-dark-800'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <FileCode className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                    <span className="truncate">{f.file_path}</span>
                  </div>
                  <span className="text-[10px] opacity-75 shrink-0 ml-2">{f.loc}L</span>
                </button>
              ))}
            </div>
          </div>

          {/* Code Viewer Panel */}
          <div className="md:col-span-8">
            {isFileLoading ? (
              <LoadingSpinner text="Fetching file content..." />
            ) : activeFile ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between bg-dark-950 px-4 py-2 rounded-lg border border-dark-800 text-xs">
                  <span className="font-mono text-slate-300">{activeFile.file_path}</span>
                  <div className="flex items-center gap-4 text-slate-500">
                    <span>{activeFile.language}</span>
                    <span>{activeFile.loc} lines</span>
                    <span>{(activeFile.size_bytes / 1024).toFixed(1)} KB</span>
                  </div>
                </div>

                <div className="h-[550px]">
                  <CodeViewer
                    code={activeFile.content || '// Empty file'}
                    language={activeFile.language}
                    className="h-full"
                  />
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-slate-500 text-sm">
                Select a file to inspect its source code
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
