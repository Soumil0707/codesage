import { apiClient } from './client';
import {
  User,
  TokenResponse,
  Repository,
  SourceFile,
  ChatSession,
  ChatMessage,
  AnalysisReport,
  AnalysisFinding,
  InterviewSession,
  InterviewQuestion,
  InterviewAnswerResponse,
  InterviewReport,
  GeneratedDoc,
  AnalyticsDashboard,
} from '../types';

export const api = {
  auth: {
    register: (data: any) => apiClient.post<TokenResponse>('/auth/register', data),
    login: (data: any) => apiClient.post<TokenResponse>('/auth/login', data),
    getMe: () => apiClient.get<User>('/auth/me'),
  },

  repos: {
    list: () => apiClient.get<Repository[]>('/repositories'),
    get: (id: string) => apiClient.get<Repository>(`/repositories/${id}`),
    createGithub: (data: { github_url: string; name?: string; branch?: string; github_token?: string }) =>
      apiClient.post<Repository>('/repositories/github', data),
    uploadZip: (formData: FormData) =>
      apiClient.post<Repository>('/repositories/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    delete: (id: string) => apiClient.delete(`/repositories/${id}`),
    listFiles: (repoId: string, versionId?: string, language?: string) =>
      apiClient.get<SourceFile[]>(`/repositories/${repoId}/files`, { params: { version_id: versionId, language } }),
    getFile: (repoId: string, fileId: string) =>
      apiClient.get<SourceFile>(`/repositories/${repoId}/files/${fileId}`),
    reindex: (repoId: string) =>
      apiClient.post<{ status: string; job_id: string }>(`/repositories/${repoId}/reindex`),
  },

  chat: {
    createSession: (repository_id: string, title?: string) =>
      apiClient.post<ChatSession>('/chat', { repository_id, title }),
    listSessions: (repository_id?: string) =>
      apiClient.get<ChatSession[]>('/chat', { params: { repository_id } }),
    getSession: (sessionId: string) =>
      apiClient.get<ChatSession>(`/chat/${sessionId}`),
    deleteSession: (sessionId: string) =>
      apiClient.delete(`/chat/${sessionId}`),
    getMessages: (sessionId: string) =>
      apiClient.get<ChatMessage[]>(`/chat/${sessionId}/messages`),
    sendMessage: (sessionId: string, content: string) =>
      apiClient.post<ChatMessage>(`/chat/${sessionId}/messages`, { content }),
  },

  review: {
    startReview: (data: { repository_id: string; version_id?: string; review_type?: string; file_paths?: string[] }) =>
      apiClient.post<AnalysisReport>('/review', data),
    listReports: (repository_id: string) =>
      apiClient.get<AnalysisReport[]>('/review/reports', { params: { repository_id } }),
    getReport: (reportId: string) =>
      apiClient.get<AnalysisReport>(`/review/${reportId}`),
    updateFindingStatus: (findingId: string, status: string) =>
      apiClient.patch<AnalysisFinding>(`/review/findings/${findingId}`, null, { params: { status } }),
  },

  interview: {
    start: (data: { repository_id: string; title?: string; difficulty?: string }) =>
      apiClient.post<InterviewSession>('/interview', data),
    list: (repository_id?: string) =>
      apiClient.get<InterviewSession[]>('/interview', { params: { repository_id } }),
    getSession: (sessionId: string) =>
      apiClient.get<InterviewSession>(`/interview/${sessionId}`),
    nextQuestion: (sessionId: string) =>
      apiClient.post<InterviewQuestion>(`/interview/${sessionId}/next`),
    submitAnswer: (sessionId: string, questionId: string, answer_text: string) =>
      apiClient.post<InterviewAnswerResponse>(`/interview/${sessionId}/questions/${questionId}/answer`, { answer_text }),
    complete: (sessionId: string) =>
      apiClient.post<InterviewReport>(`/interview/${sessionId}/complete`),
    getReport: (sessionId: string) =>
      apiClient.get<InterviewReport>(`/interview/${sessionId}/report`),
  },

  docs: {
    generate: (data: { repository_id: string; version_id?: string; doc_type?: string }) =>
      apiClient.post<GeneratedDoc>('/docs-gen/generate', data),
    list: (repoId: string) =>
      apiClient.get<GeneratedDoc[]>(`/docs-gen/${repoId}`),
    get: (repoId: string, docId: string) =>
      apiClient.get<GeneratedDoc>(`/docs-gen/${repoId}/${docId}`),
  },

  analytics: {
    getDashboard: (repoId: string) =>
      apiClient.get<AnalyticsDashboard>(`/analytics/${repoId}/dashboard`),
    getGraph: (repoId: string) =>
      apiClient.get<any>(`/analytics/${repoId}/graph`),
  },
};
