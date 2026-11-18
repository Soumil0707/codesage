import React, { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Badge } from '../components/common/Badge';
import {
  MessageSquareCode,
  Send,
  Plus,
  Trash2,
  Bot,
  User as UserIcon,
  BookOpen,
  FileCode,
  Sparkles,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import toast from 'react-hot-toast';

export const ChatPage: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState('');
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [expandedCitations, setExpandedCitations] = useState<Record<string, boolean>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Fetch chat sessions
  const { data: sessions, isLoading: isSessionsLoading } = useQuery({
    queryKey: ['chatSessions', repoId],
    queryFn: async () => (await api.chat.listSessions(repoId)).data,
    enabled: !!repoId,
  });

  // Automatically select first session or auto-create one if none exist
  useEffect(() => {
    if (sessions && !isSessionsLoading) {
      if (sessions.length > 0) {
        if (!activeSessionId || !sessions.some((s) => s.id === activeSessionId)) {
          setActiveSessionId(sessions[0].id);
        }
      } else if (repoId && !createSessionMutation.isPending) {
        // Auto-create initial session
        createSessionMutation.mutate('Repository Overview Chat');
      }
    }
  }, [sessions, isSessionsLoading, activeSessionId, repoId]);

  // Fetch messages for active session
  const { data: messages, isLoading: isMessagesLoading } = useQuery({
    queryKey: ['chatMessages', activeSessionId],
    queryFn: async () => (await api.chat.getMessages(activeSessionId!)).data,
    enabled: !!activeSessionId,
    refetchInterval: 5000,
  });

  const createSessionMutation = useMutation({
    mutationFn: (title?: string) => api.chat.createSession(repoId!, title || 'New Chat'),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions', repoId] });
      setActiveSessionId(res.data.id);
      toast.success('Chat session ready');
    },
    onError: () => {
      toast.error('Failed to create chat session');
    },
  });

  const deleteSessionMutation = useMutation({
    mutationFn: (sessionId: string) => api.chat.deleteSession(sessionId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['chatSessions', repoId] });
      if (activeSessionId === deletedId) {
        setActiveSessionId(null);
      }
      toast.success('Chat session deleted');
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: async ({ sessionId, text }: { sessionId: string; text: string }) => {
      return (await api.chat.sendMessage(sessionId, text)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatMessages', activeSessionId] });
      queryClient.invalidateQueries({ queryKey: ['chatSessions', repoId] });
      setPendingMessage(null);
    },
    onError: (err: any) => {
      setPendingMessage(null);
      toast.error(err.response?.data?.detail || 'Failed to send message');
    },
  });

  const handleSendText = async (text: string) => {
    if (!text.trim() || !repoId) return;

    let targetSessionId = activeSessionId;
    if (!targetSessionId) {
      try {
        const newSession = await api.chat.createSession(repoId, 'Chat: ' + text.slice(0, 30));
        targetSessionId = newSession.data.id;
        setActiveSessionId(targetSessionId);
        queryClient.invalidateQueries({ queryKey: ['chatSessions', repoId] });
      } catch {
        toast.error('Failed to create chat session');
        return;
      }
    }

    setPendingMessage(text.trim());
    setInputMessage('');
    sendMessageMutation.mutate({ sessionId: targetSessionId, text: text.trim() });
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendText(inputMessage);
  };

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const toggleCitation = (msgId: string) => {
    setExpandedCitations((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, pendingMessage]);

  const starterQuestions = [
    'What does this repository do and how is it structured?',
    'Explain the main entry point and runtime workflow.',
    'What external packages, APIs, or models are integrated?',
    'Where is core state management and error handling implemented?',
  ];

  return (
    <div className="h-[calc(100vh-140px)] flex border border-dark-800 rounded-xl overflow-hidden bg-dark-900 animate-fade-in">
      {/* Sessions Left Sidebar */}
      <div className="w-72 border-r border-dark-800 bg-dark-950 flex flex-col justify-between shrink-0">
        <div className="p-4 border-b border-dark-800 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-semibold text-white">
            <MessageSquareCode className="w-4 h-4 text-brand-400" />
            Chat Sessions
          </div>
          <Button
            size="sm"
            onClick={() => createSessionMutation.mutate('New Chat')}
            isLoading={createSessionMutation.isPending}
          >
            <Plus className="w-3.5 h-3.5" />
            New
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {sessions && sessions.length > 0 ? (
            sessions.map((s) => (
              <div
                key={s.id}
                className={`group w-full px-3 py-2.5 rounded-lg text-xs transition-colors flex items-center justify-between gap-2 border ${
                  activeSessionId === s.id
                    ? 'bg-brand-600/20 text-brand-300 border-brand-500/40 font-medium'
                    : 'bg-dark-900/60 border-transparent text-slate-400 hover:text-white hover:bg-dark-900'
                }`}
              >
                <button
                  onClick={() => setActiveSessionId(s.id)}
                  className="flex-1 text-left truncate flex items-center gap-2"
                >
                  <span className="truncate">{s.title || 'Chat Session'}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-dark-800 text-slate-400 border border-dark-700 font-mono shrink-0">
                    {s.message_count}
                  </span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete this chat session?')) {
                      deleteSessionMutation.mutate(s.id);
                    }
                  }}
                  title="Delete session"
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-rose-400 text-slate-500 transition-opacity rounded"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-xs text-slate-500">
              No sessions yet.
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="flex-1 flex flex-col justify-between bg-dark-900 min-w-0">
        {/* Messages Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isMessagesLoading ? (
            <LoadingSpinner text="Retrieving conversation..." />
          ) : (messages && messages.length > 0) || pendingMessage ? (
            <>
              {messages?.map((m) => (
                <div
                  key={m.id}
                  className={`flex gap-4 max-w-3xl ${
                    m.role === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                  }`}
                >
                  <div
                    className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center ${
                      m.role === 'user'
                        ? 'bg-brand-600 text-white'
                        : 'bg-dark-800 text-brand-400 border border-dark-700'
                    }`}
                  >
                    {m.role === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className="space-y-2 min-w-0 flex-1">
                    <div
                      className={`rounded-2xl px-5 py-4 text-sm relative group ${
                        m.role === 'user'
                          ? 'bg-brand-600 text-white shadow-md'
                          : 'bg-dark-950 border border-dark-800 text-slate-200'
                      }`}
                    >
                      {m.role === 'assistant' && (
                        <button
                          onClick={() => handleCopy(m.content, m.id)}
                          title="Copy answer"
                          className="absolute top-3 right-3 p-1.5 rounded-lg bg-dark-900 border border-dark-800 text-slate-400 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          {copiedId === m.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}

                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        className="prose prose-invert prose-sm max-w-none leading-relaxed"
                      >
                        {m.content}
                      </ReactMarkdown>

                      {m.role === 'assistant' && (m.model_used || m.latency_ms) && (
                        <div className="flex items-center gap-3 mt-3 pt-2 border-t border-dark-800/80 text-[11px] text-slate-500 font-mono">
                          {m.model_used && <span>Model: {m.model_used}</span>}
                          {m.latency_ms && (
                            <span>Latency: {(m.latency_ms / 1000).toFixed(2)}s</span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Grounded Citations Display */}
                    {m.citations && m.citations.length > 0 && (
                      <div className="p-3 bg-dark-950/80 border border-dark-800 rounded-xl space-y-2">
                        <button
                          onClick={() => toggleCitation(m.id)}
                          className="w-full flex items-center justify-between text-xs font-semibold text-slate-400 hover:text-brand-300 transition-colors"
                        >
                          <div className="flex items-center gap-1.5">
                            <BookOpen className="w-3.5 h-3.5 text-brand-400" />
                            <span>Verified Code Citations ({m.citations.length})</span>
                          </div>
                          {expandedCitations[m.id] ? (
                            <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                          )}
                        </button>

                        {(expandedCitations[m.id] ?? true) && (
                          <div className="space-y-1.5 pt-1">
                            {m.citations.map((c, idx) => (
                              <div
                                key={idx}
                                className="text-xs bg-dark-900 border border-dark-800 p-2.5 rounded-lg font-mono text-slate-300"
                              >
                                <div className="text-brand-400 font-semibold mb-1 flex items-center gap-1.5">
                                  <FileCode className="w-3.5 h-3.5" />
                                  <span>
                                    {c.file_path}:L{c.start_line}-L{c.end_line}
                                  </span>
                                </div>
                                {c.snippet && (
                                  <pre className="text-[11px] text-slate-400 overflow-x-auto whitespace-pre-wrap max-h-32 bg-dark-950 p-2 rounded border border-dark-800/60 font-mono">
                                    {c.snippet}
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Optimistic Pending Message */}
              {pendingMessage && (
                <>
                  <div className="flex gap-4 max-w-3xl ml-auto flex-row-reverse">
                    <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center bg-brand-600 text-white">
                      <UserIcon className="w-4 h-4" />
                    </div>
                    <div className="rounded-2xl px-5 py-3 text-sm bg-brand-600 text-white">
                      {pendingMessage}
                    </div>
                  </div>

                  <div className="flex gap-4 max-w-3xl mr-auto">
                    <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center bg-dark-800 text-brand-400 border border-dark-700">
                      <Bot className="w-4 h-4 animate-spin" />
                    </div>
                    <div className="bg-dark-950 border border-brand-500/30 rounded-2xl px-5 py-3 text-sm text-brand-300 flex items-center gap-2 shadow-lg shadow-brand-500/10">
                      <Sparkles className="w-4 h-4 text-brand-400 animate-pulse" />
                      <span>Synthesizing repository codebase & verifying citations...</span>
                    </div>
                  </div>
                </>
              )}
            </>
          ) : (
            /* Empty State with Quick Starter Question Chips */
            <div className="text-center py-12 max-w-xl mx-auto space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-brand-600/15 border border-brand-500/30 flex items-center justify-center mx-auto text-brand-400">
                <Bot className="w-7 h-7" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-lg font-bold text-white tracking-tight">Codebase RAG Assistant</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Ask deep technical questions about this repository. Responses are strictly grounded in your indexed source files, architecture, and syntax trees.
                </p>
              </div>

              <div className="space-y-2 pt-2 text-left">
                <span className="text-[11px] font-semibold uppercase text-slate-500 tracking-wider">
                  Suggested Prompts:
                </span>
                <div className="grid grid-cols-1 gap-2">
                  {starterQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendText(q)}
                      className="p-3 text-xs text-slate-300 bg-dark-950 border border-dark-800 hover:border-brand-500/50 hover:text-white hover:bg-dark-800/80 rounded-xl text-left transition-all flex items-center justify-between group"
                    >
                      <span>{q}</span>
                      <Sparkles className="w-3.5 h-3.5 text-brand-400 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="p-4 border-t border-dark-800 bg-dark-950 flex gap-3">
          <input
            type="text"
            placeholder="Ask anything about this repository (e.g. How does agent routing work?)..."
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            disabled={sendMessageMutation.isPending}
            className="flex-1 px-4 py-2.5 bg-dark-900 border border-dark-700 rounded-xl text-sm text-white focus:outline-none focus:border-brand-500 placeholder-slate-500"
          />
          <Button
            type="submit"
            disabled={!inputMessage.trim() || sendMessageMutation.isPending}
            isLoading={sendMessageMutation.isPending}
          >
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
};
