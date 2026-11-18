/**
 * Frontend TypeScript type definitions matching backend models & schemas.
 */

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface UserSettings {
  theme: string;
  default_language: string;
  notifications_enabled: boolean;
  llm_model_preference: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Repository {
  id: string;
  name: string;
  description?: string | null;
  source: 'github' | 'zip_upload';
  github_url?: string | null;
  primary_language?: string | null;
  total_files: number;
  total_loc: number;
  indexing_status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'partial';
  last_indexed_at?: string | null;
  created_at: string;
}

export interface RepositoryVersion {
  id: string;
  version_number: number;
  commit_sha?: string | null;
  upload_hash?: string | null;
  is_current: boolean;
  file_count: number;
  total_loc: number;
  language_stats?: string | null;
  created_at: string;
}

export interface SourceFile {
  id: string;
  file_path: string;
  file_name: string;
  language: string;
  content?: string | null;
  size_bytes: number;
  loc: number;
  is_parseable: boolean;
}

export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: Citation[];
  model_used?: string | null;
  latency_ms?: number | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  repository_id: string;
  title: string;
  message_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AnalysisFinding {
  id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  category: 'bug' | 'code_smell' | 'security' | 'performance' | 'style' | 'complexity' | 'duplication' | 'best_practice';
  rule_id?: string | null;
  title: string;
  description: string;
  suggested_fix?: string | null;
  code_snippet?: string | null;
  verification_status: 'verified_defect' | 'ai_recommendation' | 'false_positive' | 'acknowledged';
  confidence: number;
}

export interface AnalysisReport {
  id: string;
  repository_id: string;
  report_type: 'code_review' | 'security_scan' | 'quality_analysis' | 'full_analysis';
  status: string;
  summary?: string | null;
  total_issues: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  findings: AnalysisFinding[];
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface InterviewQuestion {
  id: string;
  question_number: number;
  difficulty: 'easy' | 'medium' | 'hard';
  category: string;
  question_text: string;
  context_code?: string | null;
  context_file_path?: string | null;
  is_follow_up: boolean;
  answer?: InterviewAnswerResponse | null;
}

export interface InterviewAnswerResponse {
  id: string;
  score: number;
  max_score: number;
  answer_text?: string;
  evaluation?: {
    correctness: number;
    depth: number;
    repo_understanding: number;
    feedback: string;
  };
  topics_demonstrated?: string[];
  topics_missed?: string[];
}

export interface InterviewSession {
  id: string;
  title: string;
  status: 'in_progress' | 'completed' | 'abandoned';
  current_difficulty: 'easy' | 'medium' | 'hard';
  total_questions: number;
  total_score: number;
  max_score: number;
  started_at: string;
  completed_at?: string | null;
  created_at: string;
}

export interface InterviewReport extends InterviewSession {
  topics_covered?: string[];
  strengths?: string[];
  weaknesses?: string[];
  final_report?: {
    overall_score: number;
    max_score: number;
    percentage: number;
    grade: string;
    topic_breakdown: Record<string, number>;
    strengths: string[];
    weaknesses: string[];
    revision_guides: string[];
  };
  questions: InterviewQuestion[];
}

export interface GeneratedDoc {
  id: string;
  repository_id: string;
  doc_type: 'readme' | 'architecture' | 'api_spec' | 'db_schema' | 'sequence_diagram' | 'component_doc' | 'full_docs';
  title: string;
  content_markdown: string;
  created_at: string;
}

export interface LanguageBreakdown {
  language: string;
  file_count: number;
  loc: number;
  percentage: number;
}

export interface ComplexityMetric {
  file_path: string;
  function_name?: string | null;
  cyclomatic_complexity: number;
}

export interface DependencyHealth {
  total_dependencies: number;
  internal_dependencies: number;
  external_dependencies: number;
  circular_dependencies: number;
  circular_dependency_groups?: string[][];
}

export interface AnalyticsDashboard {
  repository_id: string;
  total_files: number;
  total_loc: number;
  languages: LanguageBreakdown[];
  avg_complexity: number;
  max_complexity: number;
  complexity_details: ComplexityMetric[];
  dependency_health?: DependencyHealth | null;
  issue_counts: Record<string, number>;
  recent_analyses: AnalysisReport[];
}
