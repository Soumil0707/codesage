import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/endpoints';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CodeViewer } from '../components/common/CodeViewer';
import {
  GraduationCap,
  Play,
  CheckCircle2,
  HelpCircle,
  Award,
  ChevronRight,
  TrendingUp,
  FileCode,
  Sparkles,
} from 'lucide-react';
import toast from 'react-hot-toast';

export const InterviewPage: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [candidateAnswer, setCandidateAnswer] = useState('');

  // List existing interview sessions
  const { data: sessions, isLoading: isSessionsLoading } = useQuery({
    queryKey: ['interviewSessions', repoId],
    queryFn: async () => (await api.interview.list(repoId)).data,
    enabled: !!repoId,
  });

  // Automatically select latest session
  React.useEffect(() => {
    if (sessions && sessions.length > 0 && !activeSessionId) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  // Fetch active session report/details
  const { data: sessionReport, isLoading: isReportLoading } = useQuery({
    queryKey: ['interviewReport', activeSessionId],
    queryFn: async () => (await api.interview.getReport(activeSessionId!)).data,
    enabled: !!activeSessionId,
  });

  // Sync selected question to latest question if none selected or invalid
  React.useEffect(() => {
    if (sessionReport?.questions && sessionReport.questions.length > 0) {
      if (!selectedQuestionId || !sessionReport.questions.some((q) => q.id === selectedQuestionId)) {
        setSelectedQuestionId(sessionReport.questions[sessionReport.questions.length - 1].id);
      }
    }
  }, [sessionReport, selectedQuestionId]);

  const startSessionMutation = useMutation({
    mutationFn: () =>
      api.interview.start({
        repository_id: repoId!,
        title: 'Repository Technical Interview',
        difficulty: 'medium',
      }),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['interviewSessions', repoId] });
      setActiveSessionId(res.data.id);
      setSelectedQuestionId(null);
      setCandidateAnswer('');
      toast.success('Interview session initiated!');
    },
  });

  const submitAnswerMutation = useMutation({
    mutationFn: async ({ questionId, answer }: { questionId: string; answer: string }) => {
      const evalRes = await api.interview.submitAnswer(activeSessionId!, questionId, answer);
      // Automatically advance to the next question
      const currentIndex = sessionReport?.questions?.findIndex((q) => q.id === questionId) ?? -1;
      let nextQId: string | null = null;
      let nextQNumber: number | null = null;

      if (sessionReport?.questions && currentIndex >= 0 && currentIndex < sessionReport.questions.length - 1) {
        nextQId = sessionReport.questions[currentIndex + 1].id;
        nextQNumber = sessionReport.questions[currentIndex + 1].question_number;
      } else {
        try {
          const nextQRes = await api.interview.nextQuestion(activeSessionId!);
          nextQId = nextQRes.data.id;
          nextQNumber = nextQRes.data.question_number;
        } catch {
          // Max questions reached or session finished
        }
      }
      return { eval: evalRes.data, nextQId, nextQNumber };
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['interviewReport', activeSessionId] });
      setCandidateAnswer('');
      if (data.nextQId) {
        setSelectedQuestionId(data.nextQId);
        toast.success(`Evaluated (${data.eval.score}/10)! Moved to Question #${data.nextQNumber || ''}`);
      } else {
        toast.success(`Evaluated! Score: ${data.eval.score}/10`);
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Answer submission failed');
    },
  });

  const nextQuestionMutation = useMutation({
    mutationFn: () => api.interview.nextQuestion(activeSessionId!),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['interviewReport', activeSessionId] });
      setSelectedQuestionId(res.data.id);
      setCandidateAnswer('');
      toast.success(`Generated Question #${res.data.question_number}`);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to generate next question');
    },
  });

  const handleSkipOrNext = () => {
    if (!sessionReport?.questions || sessionReport.questions.length === 0) return;
    const currentIndex = sessionReport.questions.findIndex((q) => q.id === selectedQuestion?.id);

    // If there is already a subsequent question in the list, navigate to it!
    if (currentIndex >= 0 && currentIndex < sessionReport.questions.length - 1) {
      setSelectedQuestionId(sessionReport.questions[currentIndex + 1].id);
      setCandidateAnswer('');
    } else {
      // Otherwise, generate the next question via LLM from backend
      nextQuestionMutation.mutate();
    }
  };

  const completeInterviewMutation = useMutation({
    mutationFn: () => api.interview.complete(activeSessionId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interviewReport', activeSessionId] });
      toast.success('Interview completed! Scorecard compiled.');
    },
  });

  const selectedQuestion =
    sessionReport?.questions?.find((q) => q.id === selectedQuestionId) ||
    sessionReport?.questions?.slice(-1)[0];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-dark-800 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <GraduationCap className="w-6 h-6 text-brand-400" />
            Repository-Grounded Interview Intelligence
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Practice technical questions derived directly from your codebase architecture, with AI rubric grading.
          </p>
        </div>

        <Button
          onClick={() => startSessionMutation.mutate()}
          isLoading={startSessionMutation.isPending}
          className="shadow-lg shadow-brand-500/20"
        >
          <Play className="w-4 h-4 mr-1" />
          Start New Interview
        </Button>
      </div>

      {/* Session Switcher */}
      {sessions && sessions.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-dark-800">
          <span className="text-xs text-slate-500 font-semibold uppercase shrink-0 mr-1">Sessions:</span>
          {sessions.map((s, idx) => (
            <button
              key={s.id}
              onClick={() => {
                setActiveSessionId(s.id);
                setSelectedQuestionId(null);
                setCandidateAnswer('');
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 flex items-center gap-2 border ${
                activeSessionId === s.id
                  ? 'bg-brand-600/20 text-brand-300 border-brand-500/40 font-semibold'
                  : 'bg-dark-900 text-slate-400 border-dark-800 hover:text-white hover:bg-dark-800'
              }`}
            >
              <span className="truncate max-w-[160px]">{s.title || `Session #${sessions.length - idx}`}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-bold uppercase ${
                  s.status === 'completed'
                    ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/30'
                    : 'bg-amber-950 text-amber-400 border border-amber-800/30'
                }`}
              >
                {s.status.replace('_', ' ')}
              </span>
            </button>
          ))}
        </div>
      )}

      {isSessionsLoading || isReportLoading ? (
        <LoadingSpinner text="Loading interview session..." />
      ) : sessionReport ? (
        <div className="space-y-6">
          {/* Header Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-slate-500">Status</span>
              <div className="text-lg font-bold text-white mt-1 uppercase">
                {sessionReport.status.replace('_', ' ')}
              </div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-slate-500">Difficulty</span>
              <div className="text-lg font-bold text-brand-400 mt-1 uppercase">
                {sessionReport.current_difficulty}
              </div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-slate-500">Questions Answered</span>
              <div className="text-lg font-bold text-white mt-1">
                {sessionReport.questions?.filter((q) => q.answer).length ?? 0} / {sessionReport.questions?.length ?? 0}
              </div>
            </div>
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-4">
              <span className="text-xs font-semibold uppercase text-slate-500">Cumulative Score</span>
              <div className="text-lg font-bold text-emerald-400 mt-1">
                {sessionReport.total_score} / {sessionReport.max_score}
              </div>
            </div>
          </div>

          {/* Question Navigator Tabs */}
          {sessionReport.questions && sessionReport.questions.length > 0 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1">
              <span className="text-xs text-slate-500 font-semibold uppercase shrink-0 mr-1">Questions:</span>
              {sessionReport.questions.map((q) => (
                <button
                  key={q.id}
                  onClick={() => setSelectedQuestionId(q.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors flex items-center gap-2 ${
                    selectedQuestion?.id === q.id
                      ? 'bg-brand-600/30 text-brand-200 border-brand-500 font-semibold'
                      : 'bg-dark-900 text-slate-400 border-dark-800 hover:text-white'
                  }`}
                >
                  <span>Q{q.question_number}</span>
                  {q.answer ? (
                    <span className="text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-800/40 px-1.5 py-0.5 rounded font-bold">
                      {q.answer.score}/10
                    </span>
                  ) : (
                    <span className="text-[10px] bg-amber-950 text-amber-400 border border-amber-800/40 px-1.5 py-0.5 rounded font-bold">
                      Pending
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Question & Evaluation Box */}
          {selectedQuestion && (
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-6 space-y-5">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <Badge variant="brand">Question #{selectedQuestion.question_number}</Badge>
                  <Badge variant="default">{selectedQuestion.difficulty}</Badge>
                  <Badge variant="default">{selectedQuestion.category}</Badge>
                </div>
                {sessionReport.status === 'in_progress' && (
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => completeInterviewMutation.mutate()}
                    isLoading={completeInterviewMutation.isPending}
                  >
                    End Session & Score
                  </Button>
                )}
              </div>

              <div>
                <h2 className="text-lg font-semibold text-white leading-relaxed">
                  {selectedQuestion.question_text}
                </h2>
              </div>

              {selectedQuestion.context_code && (
                <div className="space-y-1.5 bg-dark-950/60 p-3 rounded-lg border border-dark-800">
                  <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                    <FileCode className="w-3.5 h-3.5 text-brand-400" />
                    <span>File Context: {selectedQuestion.context_file_path}</span>
                  </div>
                  <div className="max-h-64 overflow-y-auto rounded-lg">
                    <CodeViewer code={selectedQuestion.context_code} />
                  </div>
                </div>
              )}

              {/* IF QUESTION IS ALREADY ANSWERED: Show Candidate Answer + LLM Evaluation */}
              {selectedQuestion.answer ? (
                <div className="space-y-4 pt-2">
                  {/* Candidate's submitted answer */}
                  {selectedQuestion.answer.answer_text && (
                    <div className="bg-dark-950 border border-dark-800 rounded-xl p-4 space-y-2">
                      <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
                        Your Submitted Answer:
                      </span>
                      <p className="text-sm text-slate-200 whitespace-pre-wrap leading-relaxed font-sans">
                        {selectedQuestion.answer.answer_text}
                      </p>
                    </div>
                  )}

                  {/* Rubric Evaluation Box */}
                  <div className="bg-dark-950/90 border border-brand-500/30 rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between pb-3 border-b border-dark-800 flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Award className="w-5 h-5 text-amber-400" />
                        <span className="font-semibold text-white text-base">LLM Rubric Evaluation</span>
                      </div>
                      <div className="flex items-center gap-1.5 bg-brand-500/10 border border-brand-500/30 px-3 py-1 rounded-lg">
                        <span className="text-xs text-slate-400 uppercase font-semibold">Awarded:</span>
                        <span className="text-lg font-bold text-brand-300">
                          {selectedQuestion.answer.score} / {selectedQuestion.answer.max_score}
                        </span>
                      </div>
                    </div>

                    {/* Rubric Breakdown Grid */}
                    {selectedQuestion.answer.evaluation && (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <div className="bg-dark-900 border border-dark-800 rounded-lg p-3">
                          <div className="text-xs text-slate-400">Correctness & Accuracy</div>
                          <div className="text-base font-bold text-white mt-1">
                            {selectedQuestion.answer.evaluation.correctness ?? 0}{' '}
                            <span className="text-xs text-slate-500 font-normal">/ 4.0</span>
                          </div>
                        </div>
                        <div className="bg-dark-900 border border-dark-800 rounded-lg p-3">
                          <div className="text-xs text-slate-400">Depth & Rigor</div>
                          <div className="text-base font-bold text-white mt-1">
                            {selectedQuestion.answer.evaluation.depth ?? 0}{' '}
                            <span className="text-xs text-slate-500 font-normal">/ 3.0</span>
                          </div>
                        </div>
                        <div className="bg-dark-900 border border-dark-800 rounded-lg p-3">
                          <div className="text-xs text-slate-400">Codebase Understanding</div>
                          <div className="text-base font-bold text-white mt-1">
                            {selectedQuestion.answer.evaluation.repo_understanding ?? 0}{' '}
                            <span className="text-xs text-slate-500 font-normal">/ 3.0</span>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Feedback Prose */}
                    {selectedQuestion.answer.evaluation?.feedback && (
                      <div className="bg-dark-900/60 border border-dark-800 rounded-lg p-4 space-y-1">
                        <span className="text-xs font-semibold uppercase text-slate-400 tracking-wider">
                          AI Evaluator Feedback
                        </span>
                        <p className="text-sm text-slate-300 leading-relaxed">
                          {selectedQuestion.answer.evaluation.feedback}
                        </p>
                      </div>
                    )}

                    {/* Topics Demonstrated & Missed */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                      {selectedQuestion.answer.topics_demonstrated &&
                        selectedQuestion.answer.topics_demonstrated.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-xs font-semibold uppercase text-emerald-400 flex items-center gap-1.5">
                              <CheckCircle2 className="w-4 h-4" /> Topics Demonstrated
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedQuestion.answer.topics_demonstrated.map((t, idx) => (
                                <span
                                  key={idx}
                                  className="bg-emerald-950/60 text-emerald-300 border border-emerald-800/40 text-xs px-2.5 py-1 rounded-md font-medium"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      {selectedQuestion.answer.topics_missed &&
                        selectedQuestion.answer.topics_missed.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-xs font-semibold uppercase text-amber-400 flex items-center gap-1.5">
                              <HelpCircle className="w-4 h-4" /> Areas for Improvement
                            </span>
                            <div className="flex flex-wrap gap-1.5">
                              {selectedQuestion.answer.topics_missed.map((t, idx) => (
                                <span
                                  key={idx}
                                  className="bg-amber-950/60 text-amber-300 border border-amber-800/40 text-xs px-2.5 py-1 rounded-md font-medium"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                    </div>

                    {/* Next Question Navigation if session is in progress */}
                    {sessionReport.status === 'in_progress' && (
                      <div className="flex justify-end items-center gap-3 pt-3 border-t border-dark-800">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => completeInterviewMutation.mutate()}
                          isLoading={completeInterviewMutation.isPending}
                        >
                          Finish Session
                        </Button>
                        <Button
                          onClick={handleSkipOrNext}
                          isLoading={nextQuestionMutation.isPending}
                        >
                          Next Question
                          <ChevronRight className="w-4 h-4 ml-1" />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                /* IF QUESTION NOT YET ANSWERED: Show Answer Submission Form */
                sessionReport.status === 'in_progress' && (
                  <div className="space-y-3 pt-2">
                    <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider">
                      Your Technical Explanation:
                    </label>
                    <textarea
                      rows={5}
                      value={candidateAnswer}
                      onChange={(e) => setCandidateAnswer(e.target.value)}
                      placeholder="Explain your approach, design patterns, refactoring steps, and trade-offs based on the codebase..."
                      className="w-full p-4 bg-dark-950 border border-dark-700 rounded-xl text-sm text-white focus:outline-none focus:border-brand-500 font-mono text-xs"
                    />
                    <div className="flex justify-between items-center flex-wrap gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleSkipOrNext}
                        isLoading={nextQuestionMutation.isPending}
                      >
                        Skip to Next Question
                      </Button>
                      <Button
                        onClick={() =>
                          submitAnswerMutation.mutate({
                            questionId: selectedQuestion.id,
                            answer: candidateAnswer,
                          })
                        }
                        disabled={!candidateAnswer.trim()}
                        isLoading={submitAnswerMutation.isPending}
                      >
                        Submit Answer for Rubric Evaluation
                      </Button>
                    </div>
                  </div>
                )
              )}
            </div>
          )}

          {/* Final Report Scorecard if completed */}
          {sessionReport.status === 'completed' && sessionReport.final_report && (
            <div className="bg-dark-900 border border-dark-800 rounded-xl p-8 space-y-6">
              <div className="flex items-center gap-3 pb-4 border-b border-dark-800">
                <Award className="w-8 h-8 text-amber-400" />
                <div>
                  <h2 className="text-xl font-bold text-white">Interview Scorecard & Diagnostics</h2>
                  <p className="text-xs text-slate-400">
                    Graded Level: <span className="text-brand-400 font-semibold">{sessionReport.final_report.grade}</span> ({sessionReport.final_report.percentage}%)
                  </p>
                </div>
              </div>

              {/* Topic Breakdown */}
              {sessionReport.final_report.topic_breakdown && (
                <div className="space-y-3">
                  <h3 className="text-sm font-semibold uppercase text-slate-400 tracking-wider">
                    Topic Proficiency Breakdown
                  </h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(sessionReport.final_report.topic_breakdown).map(([k, v]) => (
                      <div key={k} className="bg-dark-950 p-4 rounded-lg border border-dark-800">
                        <div className="text-xs text-slate-400">{k}</div>
                        <div className="text-xl font-bold text-white mt-1">{v}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Strengths & Weaknesses */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-emerald-950/20 border border-emerald-900/40 p-5 rounded-xl space-y-2">
                  <h4 className="text-sm font-semibold text-emerald-400">Demonstrated Strengths</h4>
                  <ul className="text-xs text-emerald-200 space-y-1 list-disc list-inside">
                    {sessionReport.strengths?.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div className="bg-rose-950/20 border border-rose-900/40 p-5 rounded-xl space-y-2">
                  <h4 className="text-sm font-semibold text-rose-400">Concept Gaps & Weaknesses</h4>
                  <ul className="text-xs text-rose-200 space-y-1 list-disc list-inside">
                    {sessionReport.weaknesses?.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              </div>

              {/* Revision Guides */}
              {sessionReport.final_report.revision_guides && sessionReport.final_report.revision_guides.length > 0 && (
                <div className="bg-dark-950 p-5 rounded-xl border border-dark-800 space-y-2">
                  <h4 className="text-sm font-semibold text-brand-300">Recommended Revision Guides & Topics</h4>
                  <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
                    {sessionReport.final_report.revision_guides.map((g, i) => (
                      <li key={i}>{g}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-20 bg-dark-900 border border-dark-800 rounded-xl">
          <GraduationCap className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No interview sessions</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-5">
            Start your first repository-grounded technical interview session.
          </p>
          <Button onClick={() => startSessionMutation.mutate()}>Start Interview</Button>
        </div>
      )}
    </div>
  );
};
