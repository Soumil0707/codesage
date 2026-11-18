import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  FileText,
  Download,
  Sparkles,
  BookOpen,
  Layout,
  Database,
  Code2,
} from 'lucide-react';
import toast from 'react-hot-toast';

export const DocsPage: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [selectedDocType, setSelectedDocType] = useState('readme');
  const [activeDocId, setActiveDocId] = useState<string | null>(null);

  const { data: docs, isLoading: isDocsLoading } = useQuery({
    queryKey: ['generatedDocs', repoId],
    queryFn: async () => (await api.docs.list(repoId!)).data,
    enabled: !!repoId,
  });

  // Automatically select first doc
  React.useEffect(() => {
    if (docs && docs.length > 0 && !activeDocId) {
      setActiveDocId(docs[0].id);
    }
  }, [docs, activeDocId]);

  const { data: activeDoc, isLoading: isDocLoading } = useQuery({
    queryKey: ['generatedDoc', repoId, activeDocId],
    queryFn: async () => (await api.docs.get(repoId!, activeDocId!)).data,
    enabled: !!repoId && !!activeDocId,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      api.docs.generate({
        repository_id: repoId!,
        doc_type: selectedDocType,
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['generatedDocs', repoId] });
      setActiveDocId(res.data.id);
      toast.success('Documentation synthesized successfully!');
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to generate documentation');
    },
  });

  const handleExport = () => {
    if (!activeDoc) return;
    const blob = new Blob([activeDoc.content_markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${activeDoc.doc_type}_${repoId?.slice(0, 8)}.md`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success('Document downloaded');
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Top Controls */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-dark-800 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <FileText className="w-6 h-6 text-brand-400" />
            Documentation & Architecture Generator
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Produce accurate README, Architecture, API specs, and DB schema summaries from actual code evidence.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedDocType}
            onChange={(e) => setSelectedDocType(e.target.value)}
            className="bg-dark-900 border border-dark-700 text-sm text-white rounded-lg px-3 py-2 focus:outline-none focus:border-brand-500"
          >
            <option value="readme">Project README</option>
            <option value="architecture">Architecture Topology</option>
            <option value="api_spec">REST API Specs</option>
            <option value="db_schema">Database Schema & ER</option>
            <option value="full_docs">Comprehensive Documentation</option>
          </select>

          <Button
            onClick={() => generateMutation.mutate()}
            isLoading={generateMutation.isPending}
            className="shadow-lg shadow-brand-500/20"
          >
            <Sparkles className="w-4 h-4 mr-1" />
            Generate Doc
          </Button>
        </div>
      </div>

      {isDocsLoading ? (
        <LoadingSpinner text="Retrieving generated documentation..." />
      ) : activeDoc ? (
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Docs list sidebar */}
          <div className="md:col-span-3 space-y-2">
            <h3 className="text-xs font-semibold uppercase text-slate-500 tracking-wider mb-2">
              Available Documents
            </h3>
            {docs?.map((d) => (
              <button
                key={d.id}
                onClick={() => setActiveDocId(d.id)}
                className={`w-full text-left p-3 rounded-lg text-xs transition-colors border ${
                  activeDocId === d.id
                    ? 'bg-brand-600/15 text-brand-300 border-brand-500/40 font-semibold'
                    : 'bg-dark-900 text-slate-400 border-dark-800 hover:text-white hover:bg-dark-800'
                }`}
              >
                <div className="truncate">{d.title}</div>
                <div className="text-[10px] text-slate-500 mt-1 uppercase">{d.doc_type}</div>
              </button>
            ))}
          </div>

          {/* Doc Content Viewer */}
          <div className="md:col-span-9 bg-dark-900 border border-dark-800 rounded-xl p-8 space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-dark-800">
              <span className="text-xs font-mono uppercase bg-dark-950 px-2.5 py-1 rounded text-brand-400 border border-dark-800">
                {activeDoc.doc_type}
              </span>
              <Button size="sm" variant="outline" onClick={handleExport}>
                <Download className="w-3.5 h-3.5 mr-1" />
                Export Markdown
              </Button>
            </div>

            <div className="prose prose-invert prose-brand max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeDoc.content_markdown}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-20 bg-dark-900 border border-dark-800 rounded-xl">
          <BookOpen className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No documentation generated yet</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
            Select a document type above and click "Generate Doc" to produce Markdown documentation from code.
          </p>
          <Button onClick={() => generateMutation.mutate()}>Generate Project README</Button>
        </div>
      )}
    </div>
  );
};
