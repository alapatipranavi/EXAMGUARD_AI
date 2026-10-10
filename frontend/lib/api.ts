export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'STUDENT' | 'EXAMINER' | 'ADMIN';
  is_active: boolean;
  college_id?: string | null;
  college_name?: string | null;
  college_code?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  department_code?: string | null;
  year_of_study?: number | null;
  section_id?: string | null;
  section_name?: string | null;
  section_code?: string | null;
  is_face_registered?: boolean;
  face_registered_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface UserRegisterInput {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: 'STUDENT' | 'EXAMINER';
  college_id?: string;
  department_id?: string;
  year_of_study?: number;
  section_id?: string;
}

export interface UserLoginInput {
  email: string;
  password: string;
}

export interface LoginResponse {
  user: User;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const isFormData = options.body instanceof FormData;
  const headers = { ...options.headers };
  if (!isFormData) {
    Object.assign(headers, defaultHeaders);
  }

  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers,
  });

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail
            .map((err: { loc?: string[]; msg?: string }) => {
              const field = Array.isArray(err.loc) && err.loc.length > 0 ? err.loc[err.loc.length - 1] : 'field';
              return `${field}: ${err.msg || 'invalid input'}`;
            })
            .join(', ');
        } else if (typeof errorData.detail === 'object' && errorData.detail !== null) {
          const detailObj = errorData.detail as { code?: string; message?: string };
          errorMessage = detailObj.message || detailObj.code || JSON.stringify(errorData.detail);
        } else {
          errorMessage = 'Please complete the required fields correctly.';
        }
      }
    } catch {
      // Failed to parse JSON
    }
    throw new Error(errorMessage);
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as unknown as T;
  }

  const text = await response.text();
  if (!text || text.trim() === '') {
    return undefined as unknown as T;
  }

  try {
    return JSON.parse(text) as T;
  } catch {
    return undefined as unknown as T;
  }
}

export const authAPI = {
  register: (data: UserRegisterInput): Promise<User> => {
    return fetchAPI<User>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  login: (data: UserLoginInput): Promise<LoginResponse> => {
    return fetchAPI<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  logout: (): Promise<{ message: string }> => {
    return fetchAPI<{ message: string }>('/api/auth/logout', {
      method: 'POST',
    });
  },

  getMe: (): Promise<User> => {
    return fetchAPI<User>('/api/auth/me', {
      method: 'GET',
    });
  },
};

export type QuestionType = 'MCQ' | 'MULTI_SELECT' | 'SHORT_ANSWER' | 'LONG_ANSWER' | 'HANDWRITTEN';
export type DifficultyLevel = 'EASY' | 'MEDIUM' | 'HARD';
export type QuestionSource = 'MANUAL' | 'AI_GENERATED' | 'CSV_IMPORT' | 'PDF_IMPORT';

export interface QuestionOptionInput {
  option_text: string;
  option_order: number;
  is_correct: boolean;
}

export interface QuestionOption {
  id: string;
  question_id: string;
  option_text: string;
  option_order: number;
  is_correct: boolean;
  created_at: string;
  updated_at: string;
}

export interface Question {
  id: string;
  question_text: string;
  question_type: QuestionType;
  subject: string;
  topic?: string | null;
  difficulty: DifficultyLevel;
  source: QuestionSource;
  marks: number;
  negative_marks: number;
  model_answer?: string | null;
  explanation?: string | null;
  created_by?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  options: QuestionOption[];
}

export interface QuestionCreateInput {
  question_text: string;
  subject: string;
  topic?: string;
  question_type: QuestionType;
  difficulty?: DifficultyLevel;
  source?: QuestionSource;
  marks: number;
  negative_marks?: number;
  model_answer?: string;
  explanation?: string;
  options?: QuestionOptionInput[];
}

export interface QuestionUpdateInput {
  question_text?: string;
  subject?: string;
  topic?: string;
  question_type?: QuestionType;
  difficulty?: DifficultyLevel;
  source?: QuestionSource;
  marks?: number;
  negative_marks?: number;
  model_answer?: string;
  explanation?: string;
  options?: QuestionOptionInput[];
}

export interface PaginatedQuestionResponse {
  items: Question[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ListQuestionsParams {
  search?: string;
  subject?: string;
  topic?: string;
  question_type?: QuestionType;
  difficulty?: DifficultyLevel;
  source?: QuestionSource;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}

export const questionsAPI = {
  list: (params: ListQuestionsParams = {}): Promise<PaginatedQuestionResponse> => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.subject) queryParams.append('subject', params.subject);
    if (params.topic) queryParams.append('topic', params.topic);
    if (params.question_type) queryParams.append('question_type', params.question_type);
    if (params.difficulty) queryParams.append('difficulty', params.difficulty);
    if (params.source) queryParams.append('source', params.source);
    if (params.is_active !== undefined) queryParams.append('is_active', String(params.is_active));
    if (params.page) queryParams.append('page', String(params.page));
    if (params.page_size) queryParams.append('page_size', String(params.page_size));

    const queryString = queryParams.toString();
    const endpoint = `/api/questions${queryString ? `?${queryString}` : ''}`;
    return fetchAPI<PaginatedQuestionResponse>(endpoint, { method: 'GET' });
  },

  get: (id: string): Promise<Question> => {
    return fetchAPI<Question>(`/api/questions/${id}`, { method: 'GET' });
  },

  create: (data: QuestionCreateInput): Promise<Question> => {
    return fetchAPI<Question>('/api/questions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: (id: string, data: QuestionUpdateInput): Promise<Question> => {
    return fetchAPI<Question>(`/api/questions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  archive: (id: string): Promise<Question> => {
    return fetchAPI<Question>(`/api/questions/${id}`, {
      method: 'DELETE',
    });
  },
};

// ==========================================
// DASHBOARD & SUMMARY TYPES & API
// ==========================================

export interface DashboardSummary {
  role: 'STUDENT' | 'EXAMINER' | 'ADMIN';
  user_name: string;
  user_email: string;
  stats: Record<string, any>;
  recent_activity: any[];
}

export interface StudentDashboardSummary {
  upcoming_exams: number;
  in_progress_exams: number;
  completed_exams: number;
  results_available: number;
}

export interface StudentAcademicProfile {
  college_id?: string | null;
  college_name?: string | null;
  college_code?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  department_code?: string | null;
  year_of_study?: number | null;
  section_id?: string | null;
  section_name?: string | null;
  section_code?: string | null;
}

export interface UpcomingExamDashboardItem {
  id: string;
  title: string;
  subject: string;
  description?: string | null;
  duration_minutes: number;
  start_at?: string | null;
  end_at?: string | null;
  question_count: number;
  total_marks: number;
  status: string;
  active_session_id?: string | null;
}

export interface InProgressExamSessionInfo {
  session_id: string;
  exam_id: string;
  exam_title: string;
  exam_subject: string;
  duration_minutes: number;
  start_time: string;
  end_time?: string | null;
  remaining_seconds: number;
  total_questions: number;
  answered_count: number;
  marked_for_review_count: number;
}

export interface RecentResultDashboardItem {
  evaluation_id: string;
  session_id: string;
  exam_id: string;
  exam_title: string;
  exam_subject: string;
  total_score: number;
  maximum_marks: number;
  percentage: number;
  pass_fail_status: string;
  status: string;
  submitted_at: string;
}

export interface StudentDashboardData {
  greeting_name: string;
  summary: StudentDashboardSummary;
  academic_profile: StudentAcademicProfile;
  in_progress_exam?: InProgressExamSessionInfo | null;
  upcoming_exams: UpcomingExamDashboardItem[];
  recent_results: RecentResultDashboardItem[];
}

export interface ExaminerDashboardSummary {
  total_exams: number;
  published_exams: number;
  active_sessions: number;
  pending_reviews: number;
}

export interface ExaminerAcademicScope {
  college_id?: string | null;
  college_name?: string | null;
  college_code?: string | null;
}

export interface ExaminerExamItem {
  id: string;
  title: string;
  subject: string;
  status: string;
  duration_minutes: number;
  total_marks: number;
  question_count: number;
  start_at?: string | null;
  end_at?: string | null;
  target_type?: string | null;
  target_summary?: string | null;
  eligible_student_count: number;
  attempt_count: number;
  created_at: string;
}

export interface ExaminerPendingReviewItem {
  session_id: string;
  exam_id: string;
  exam_title: string;
  student_id: string;
  student_name: string;
  student_email: string;
  pending_question_count: number;
  status: string;
  submitted_at?: string | null;
}

export interface ExaminerRecentActivityItem {
  id: string;
  event_type: string;
  description: string;
  student_name?: string | null;
  exam_title: string;
  timestamp: string;
  session_id?: string | null;
  exam_id?: string | null;
}

export interface ExaminerDashboardData {
  greeting_name: string;
  summary: ExaminerDashboardSummary;
  academic_scope: ExaminerAcademicScope;
  exams: ExaminerExamItem[];
  pending_reviews: ExaminerPendingReviewItem[];
  recent_activity: ExaminerRecentActivityItem[];
}

export interface AdminDashboardSummary {
  total_students: number;
  total_examiners: number;
  total_exams: number;
  active_sessions: number;
  completed_exams: number;
  pending_reviews: number;
  total_colleges: number;
  total_departments: number;
}

export interface AdminUserMetrics {
  total_students: number;
  total_examiners: number;
  active_students: number;
  active_examiners: number;
  inactive_users: number;
}

export interface AdminAcademicMetrics {
  total_colleges: number;
  total_departments: number;
  total_sections: number;
  students_with_academic_profiles: number;
}

export interface AdminExamBreakdown {
  draft: number;
  published: number;
  scheduled: number;
  active: number;
  completed: number;
  archived: number;
}

export interface AdminActivityItem {
  id: string;
  event_type: string;
  description: string;
  timestamp: string;
  user_name?: string | null;
  target_name?: string | null;
}

export interface AdminSystemStatus {
  backend: string;
  database: string;
  version: string;
}

export interface AdminDashboardData {
  greeting_name: string;
  summary: AdminDashboardSummary;
  users: AdminUserMetrics;
  academic: AdminAcademicMetrics;
  examinations: AdminExamBreakdown;
  recent_activity: AdminActivityItem[];
  system_status: AdminSystemStatus;
}

export const dashboardAPI = {
  getSummary: (): Promise<DashboardSummary> => {
    return fetchAPI<DashboardSummary>('/api/dashboard/summary', { method: 'GET' });
  },
  getStudentDashboard: (): Promise<StudentDashboardData> => {
    return fetchAPI<StudentDashboardData>('/api/student/dashboard', { method: 'GET' });
  },
  getExaminerDashboard: (): Promise<ExaminerDashboardData> => {
    return fetchAPI<ExaminerDashboardData>('/api/examiner/dashboard', { method: 'GET' });
  },
  getAdminDashboard: (): Promise<AdminDashboardData> => {
    return fetchAPI<AdminDashboardData>('/api/admin/dashboard', { method: 'GET' });
  },
};

// ==========================================
// AI QUESTION GENERATOR & ASSISTANT TYPES & API
// ==========================================

export interface AIGenerateInput {
  subject: string;
  topic: string;
  question_types: QuestionType[];
  difficulty: DifficultyLevel;
  count: number;
  marks: number;
  learning_objective?: string;
  additional_instructions?: string;
}

export interface AIGeneratedDraft {
  draft_id: string;
  question_text: string;
  subject: string;
  topic?: string | null;
  question_type: QuestionType;
  difficulty: DifficultyLevel;
  marks: number;
  negative_marks: number;
  model_answer?: string | null;
  explanation?: string | null;
  options: QuestionOptionInput[];
  source: QuestionSource;
}

export interface AIGeneratedDraftsResponse {
  subject: string;
  topic: string;
  drafts: AIGeneratedDraft[];
}

export interface AIAssistInput {
  action: string;
  question_text: string;
  subject?: string;
  topic?: string;
  question_type: QuestionType;
  current_options?: QuestionOptionInput[];
  current_model_answer?: string;
}

export interface AIAssistResponse {
  action: string;
  improved_question_text?: string;
  suggested_options?: QuestionOptionInput[];
  suggested_explanation?: string;
  suggested_model_answer?: string;
}

export const aiQuestionsAPI = {
  generate: (data: AIGenerateInput): Promise<AIGeneratedDraftsResponse> => {
    return fetchAPI<AIGeneratedDraftsResponse>('/api/questions/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  assist: (data: AIAssistInput): Promise<AIAssistResponse> => {
    return fetchAPI<AIAssistResponse>('/api/questions/assist', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// ==========================================
// CSV & PDF IMPORT TYPES & API
// ==========================================

export interface CSVImportRowValidation {
  row_number: number;
  is_valid: boolean;
  error_message?: string;
  question?: QuestionCreateInput;
  raw_data: Record<string, any>;
  needs_review: boolean;
}

export interface CSVImportParseResponse {
  total_rows: number;
  valid_rows_count: number;
  invalid_rows_count: number;
  rows: CSVImportRowValidation[];
}

export interface PDFExtractedQuestion {
  item_number: number;
  extracted_text: string;
  detected_type: QuestionType;
  detected_subject: string;
  detected_topic?: string;
  detected_difficulty: DifficultyLevel;
  detected_marks: number;
  detected_options: QuestionOptionInput[];
  detected_answer?: string;
  confidence_score: number;
  needs_review: boolean;
  is_valid: boolean;
  validation_error?: string;
}

export interface PDFImportParseResponse {
  total_extracted: number;
  items: PDFExtractedQuestion[];
}

export interface ConfirmImportInput {
  source: 'CSV_IMPORT' | 'PDF_IMPORT';
  questions: QuestionCreateInput[];
}

export const questionImportAPI = {
  parseCSV: (file: File): Promise<CSVImportParseResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchAPI<CSVImportParseResponse>('/api/questions/import/csv/parse', {
      method: 'POST',
      body: formData,
    });
  },

  parsePDF: (file: File): Promise<PDFImportParseResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchAPI<PDFImportParseResponse>('/api/questions/import/pdf/parse', {
      method: 'POST',
      body: formData,
    });
  },

  confirmImport: (data: ConfirmImportInput): Promise<Question[]> => {
    return fetchAPI<Question[]>('/api/questions/import/confirm', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// ==========================================
// EXAM MANAGEMENT TYPES & API
// ==========================================

export type ExamStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';

export interface ExamQuestionInput {
  question_id: string;
  question_order: number;
  marks_override?: number;
}

export interface ExamQuestion {
  id: string;
  exam_id: string;
  question_id: string;
  question_order: number;
  marks_override?: number | null;
  question: Question;
}

export type ExamTargetType = 'COLLEGE' | 'DEPARTMENT' | 'YEAR' | 'SECTION' | 'SPECIFIC_STUDENTS';

export interface Exam {
  id: string;
  title: string;
  description?: string | null;
  subject: string;
  instructions?: string | null;
  created_by: string;
  duration_minutes: number;
  start_at?: string | null;
  end_at?: string | null;
  total_marks: number;
  passing_marks: number;
  negative_marking_enabled: boolean;
  randomize_questions: boolean;
  randomize_options: boolean;
  proctoring_enabled: boolean;
  max_tab_switches: number;
  status: ExamStatus;
  target_type?: ExamTargetType | null;
  target_department_id?: string | null;
  target_year_of_study?: number | null;
  target_section_id?: string | null;
  target_student_ids?: string[];
  eligible_students_count?: number | null;
  created_at: string;
  updated_at: string;
  questions: ExamQuestion[];
}

export interface ExamCreateInput {
  title: string;
  description?: string;
  subject: string;
  instructions?: string;
  duration_minutes: number;
  start_at?: string;
  end_at?: string;
  passing_marks?: number;
  negative_marking_enabled?: boolean;
  randomize_questions?: boolean;
  randomize_options?: boolean;
  proctoring_enabled?: boolean;
  max_tab_switches?: number;
  target_type?: ExamTargetType | null;
  target_department_id?: string | null;
  target_year_of_study?: number | null;
  target_section_id?: string | null;
  target_student_ids?: string[];
  questions?: ExamQuestionInput[];
}

export interface ExamUpdateInput {
  title?: string;
  description?: string;
  subject?: string;
  instructions?: string;
  duration_minutes?: number;
  start_at?: string;
  end_at?: string;
  passing_marks?: number;
  negative_marking_enabled?: boolean;
  randomize_questions?: boolean;
  randomize_options?: boolean;
  proctoring_enabled?: boolean;
  max_tab_switches?: number;
  target_type?: ExamTargetType | null;
  target_department_id?: string | null;
  target_year_of_study?: number | null;
  target_section_id?: string | null;
  target_student_ids?: string[];
  questions?: ExamQuestionInput[];
}

export interface PaginatedExamResponse {
  items: Exam[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ListExamsParams {
  search?: string;
  subject?: string;
  status?: ExamStatus;
  page?: number;
  page_size?: number;
}

export const examsAPI = {
  list: (params: ListExamsParams = {}): Promise<PaginatedExamResponse> => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.subject) queryParams.append('subject', params.subject);
    if (params.status) queryParams.append('status', params.status);
    if (params.page) queryParams.append('page', String(params.page));
    if (params.page_size) queryParams.append('page_size', String(params.page_size));

    const queryString = queryParams.toString();
    const endpoint = `/api/exams${queryString ? `?${queryString}` : ''}`;
    return fetchAPI<PaginatedExamResponse>(endpoint, { method: 'GET' });
  },

  get: (id: string): Promise<Exam> => {
    return fetchAPI<Exam>(`/api/exams/${id}`, { method: 'GET' });
  },

  create: (data: ExamCreateInput): Promise<Exam> => {
    return fetchAPI<Exam>('/api/exams', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: (id: string, data: ExamUpdateInput): Promise<Exam> => {
    return fetchAPI<Exam>(`/api/exams/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  publish: (id: string): Promise<Exam> => {
    return fetchAPI<Exam>(`/api/exams/${id}/publish`, {
      method: 'POST',
    });
  },

  archive: (id: string): Promise<Exam> => {
    return fetchAPI<Exam>(`/api/exams/${id}/archive`, {
      method: 'POST',
    });
  },

  unarchive: (id: string): Promise<Exam> => {
    return fetchAPI<Exam>(`/api/exams/${id}/unarchive`, {
      method: 'POST',
    });
  },

  delete: (id: string): Promise<void> => {
    return fetchAPI<void>(`/api/exams/${id}`, {
      method: 'DELETE',
    });
  },
};

export interface StudentExamItem {
  id: string;
  title: string;
  description?: string;
  subject: string;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  question_count: number;
  start_at?: string;
  end_at?: string;
  status: ExamStatus;
  student_session_status: 'AVAILABLE' | 'IN_PROGRESS' | 'COMPLETED';
  active_session_id?: string;
  identity_verification_status?: string | null;
}

export interface PaginatedStudentExams {
  items: StudentExamItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface StudentExamDetail {
  id: string;
  title: string;
  description?: string;
  subject: string;
  instructions?: string;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  question_count: number;
  start_at?: string;
  end_at?: string;
  negative_marking_enabled: boolean;
  randomize_questions: boolean;
  randomize_options: boolean;
  proctoring_enabled: boolean;
  max_tab_switches: number;
  status: ExamStatus;
  student_session_status: 'AVAILABLE' | 'IN_PROGRESS' | 'COMPLETED';
  active_session_id?: string;
  identity_verification_status?: string | null;
}

export interface StudentQuestionOption {
  id: string;
  option_text: string;
  option_order: number;
}

export interface StudentQuestion {
  id: string;
  question_text: string;
  question_type: QuestionType;
  difficulty: DifficultyLevel;
  marks: number;
  question_order: number;
  options: StudentQuestionOption[];
}

export interface StudentAnswerSaveInput {
  selected_option_ids?: string[];
  text_answer?: string;
}

export interface StudentAnswerResponse {
  question_id: string;
  selected_option_ids: string[];
  text_answer?: string;
  answer_image_url?: string | null;
  ocr_status?: string | null;
  ocr_confidence?: number | null;
  ocr_processed_at?: string | null;
  updated_at: string;
}

export interface HandwrittenAnswerProcessResponse {
  question_id: string;
  answer_image_url: string;
  ocr_status: string;
  ocr_confidence?: number | null;
  extracted_text: string;
  evaluation_status: string;
  message: string;
}

export interface ExamSessionResponse {
  id: string;
  exam_id: string;
  exam_title: string;
  exam_subject: string;
  duration_minutes: number;
  status: 'CREATED' | 'IN_PROGRESS' | 'SUBMITTED' | 'AUTO_SUBMITTED' | 'EXPIRED' | 'TERMINATED';
  started_at?: string;
  submitted_at?: string;
  expires_at?: string;
  remaining_seconds: number;
  max_tab_switches: number;
  tab_switch_count: number;
  is_flagged: boolean;
  flag_reason?: string | null;
  identity_verification_status?: string | null;
  marked_for_review_question_ids?: string[];
  questions: StudentQuestion[];
  answers: StudentAnswerResponse[];
}

export const studentExamsAPI = {
  listExams: (params: { search?: string; subject?: string; page?: number; page_size?: number } = {}): Promise<PaginatedStudentExams> => {
    const queryParams = new URLSearchParams();
    if (params.search) queryParams.append('search', params.search);
    if (params.subject) queryParams.append('subject', params.subject);
    if (params.page) queryParams.append('page', String(params.page));
    if (params.page_size) queryParams.append('page_size', String(params.page_size));

    const queryString = queryParams.toString();
    return fetchAPI<PaginatedStudentExams>(`/api/student/exams${queryString ? `?${queryString}` : ''}`, { method: 'GET' });
  },

  getExamDetail: (id: string): Promise<StudentExamDetail> => {
    return fetchAPI<StudentExamDetail>(`/api/student/exams/${id}`, { method: 'GET' });
  },

  startSession: (examId: string): Promise<ExamSessionResponse> => {
    return fetchAPI<ExamSessionResponse>(`/api/student/exams/${examId}/start`, { method: 'POST' });
  },

  getSession: (sessionId: string): Promise<ExamSessionResponse> => {
    return fetchAPI<ExamSessionResponse>(`/api/student/sessions/${sessionId}`, { method: 'GET' });
  },

  saveAnswer: (sessionId: string, questionId: string, payload: StudentAnswerSaveInput): Promise<StudentAnswerResponse> => {
    return fetchAPI<StudentAnswerResponse>(`/api/student/sessions/${sessionId}/answers/${questionId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  toggleReview: (sessionId: string, questionId: string, marked: boolean): Promise<ExamSessionResponse> => {
    return fetchAPI<ExamSessionResponse>(`/api/student/sessions/${sessionId}/questions/${questionId}/review`, {
      method: 'PUT',
      body: JSON.stringify({ marked }),
    });
  },

  submitHandwrittenAnswer: (
    sessionId: string,
    questionId: string,
    imageData: string
  ): Promise<HandwrittenAnswerProcessResponse> => {
    return fetchAPI<HandwrittenAnswerProcessResponse>(
      `/api/student/sessions/${sessionId}/answers/${questionId}/handwritten`,
      {
        method: 'POST',
        body: JSON.stringify({ image_data: imageData }),
      }
    );
  },

  submitSession: (sessionId: string): Promise<ExamSessionResponse> => {
    return fetchAPI<ExamSessionResponse>(`/api/student/sessions/${sessionId}/submit`, { method: 'POST' });
  },
};

export const submitHandwrittenAnswer = (
  sessionId: string,
  questionId: string,
  imageData: string
): Promise<HandwrittenAnswerProcessResponse> => {
  return studentExamsAPI.submitHandwrittenAnswer(sessionId, questionId, imageData);
};

export type ProctoringEventType =
  | 'CAMERA_PERMISSION_DENIED'
  | 'CAMERA_READY'
  | 'CAMERA_DISCONNECTED'
  | 'MICROPHONE_PERMISSION_DENIED'
  | 'MICROPHONE_READY'
  | 'MICROPHONE_DISCONNECTED'
  | 'FACE_NOT_DETECTED'
  | 'FACE_DETECTED'
  | 'MULTIPLE_FACES_DETECTED'
  | 'TAB_HIDDEN'
  | 'TAB_VISIBLE'
  | 'FULLSCREEN_ENTERED'
  | 'FULLSCREEN_EXITED'
  | 'TAB_SWITCH_LIMIT_EXCEEDED'
  | 'PHONE_DETECTED'
  | 'LAPTOP_DETECTED'
  | 'BOOK_DETECTED'
  | 'ADDITIONAL_PERSON_DETECTED'
  | 'OBJECT_DETECTION_STARTED'
  | 'OBJECT_DETECTION_UNAVAILABLE'
  | 'PRE_EXAM_CHECK_STARTED'
  | 'PRE_EXAM_CHECK_COMPLETED'
  | 'QUESTION_VIEWED'
  | 'ANSWER_CREATED'
  | 'ANSWER_CHANGED'
  | 'ANSWER_CLEARED'
  | 'QUESTION_NAVIGATION'
  | 'RAPID_ANSWER_CHANGES'
  | 'UNUSUAL_TIMING'
  | 'NAVIGATION_ANOMALY'
  | 'BEHAVIOURAL_ANOMALY'
  | 'IDENTITY_VERIFIED'
  | 'IDENTITY_VERIFICATION_FAILED'
  | 'IDENTITY_MISMATCH_STARTED'
  | 'IDENTITY_VERIFICATION_RESTORED'
  | 'IDENTITY_MISMATCH_CONFIRMED';

export interface ProctoringEventCreate {
  event_type: ProctoringEventType;
  metadata_json?: Record<string, any>;
}

export interface ProctoringEventResponse {
  id: string;
  session_id: string;
  event_type: ProctoringEventType;
  timestamp: string;
  metadata_json?: Record<string, any>;
  auto_submitted?: boolean;
  is_flagged?: boolean;
  flag_reason?: string | null;
  tab_switch_count?: number;
  max_tab_switches?: number;
}

export interface ExamProctoringSummary {
  total_events: number;
  monitored_students: number;
  flagged_sessions: number;
  auto_submitted_sessions: number;
}

export interface ExaminerProctoringEventItem {
  id: string;
  session_id: string;
  student_id: string;
  student_email: string;
  student_name: string;
  event_type: ProctoringEventType;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  occurred_at: string;
  duration_seconds?: number | null;
  event_metadata?: Record<string, any>;
  tab_switch_count: number;
  max_tab_switches: number;
  session_status: string;
  is_flagged: boolean;
  flag_reason?: string | null;
}

export interface PaginatedExaminerProctoringEvents {
  items: ExaminerProctoringEventItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: ExamProctoringSummary;
}

export const proctoringAPI = {
  recordEvent: (sessionId: string, payload: ProctoringEventCreate): Promise<ProctoringEventResponse> => {
    return fetchAPI<ProctoringEventResponse>(`/api/student/sessions/${sessionId}/proctoring-events`, {
      method: 'POST',
      body: JSON.stringify(payload),
      keepalive: payload.event_type === 'TAB_HIDDEN',
    });
  },

  getExamEvents: (
    examId: string,
    params: {
      page?: number;
      page_size?: number;
      event_type?: ProctoringEventType;
      student_id?: string;
      severity?: string;
      session_status?: string;
    } = {}
  ): Promise<PaginatedExaminerProctoringEvents> => {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append('page', String(params.page));
    if (params.page_size) queryParams.append('page_size', String(params.page_size));
    if (params.event_type) queryParams.append('event_type', params.event_type);
    if (params.student_id) queryParams.append('student_id', params.student_id);
    if (params.severity) queryParams.append('severity', params.severity);
    if (params.session_status) queryParams.append('session_status', params.session_status);

    const queryString = queryParams.toString();
    return fetchAPI<PaginatedExaminerProctoringEvents>(`/api/exams/${examId}/proctoring-events${queryString ? `?${queryString}` : ''}`, {
      method: 'GET',
    });
  },
};

export interface QuestionEvaluationDetail {
  answer_id?: string | null;
  question_id: string;
  question_text: string;
  question_type: string;
  marks: number;
  earned_score: number;
  suggested_score?: number | null;
  is_answered: boolean;
  is_correct?: boolean | null;
  justification?: string | null;
  examiner_comment?: string | null;
  text_answer?: string | null;
  answer_image_url?: string | null;
  ocr_status?: string | null;
  ocr_confidence?: number | null;
  ocr_processed_at?: string | null;
  model_answer?: string | null;
  explanation?: string | null;
  selected_option_ids?: string[] | null;
  matched_concepts?: any | null;
  missed_concepts?: any | null;
  evaluator_type?: string | null;
  status?: string | null;
  reviewed_by?: string | null;
  reviewer_name?: string | null;
  reviewed_at?: string | null;
}

export interface StudentResultResponse {
  id: string;
  session_id: string;
  exam_id: string;
  exam_title: string;
  exam_subject: string;
  student_id: string;
  student_name: string;
  student_email: string;
  submitted_at?: string | null;
  total_questions: number;
  answered_questions: number;
  unanswered_questions: number;
  correct_answers: number;
  incorrect_answers: number;
  objective_marks: number;
  subjective_marks?: number;
  negative_marks: number;
  total_score: number;
  maximum_marks: number;
  percentage: number;
  passing_marks: number;
  pass_fail_status: 'PASSED' | 'FAILED';
  status: 'COMPLETED' | 'PENDING_REVIEW' | 'FAILED' | 'AI_EVALUATED' | 'MANUAL_REVIEW' | 'FINALIZED';
  question_evaluations?: QuestionEvaluationDetail[] | null;
}

export interface PaginatedStudentResultResponse {
  items: StudentResultResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const resultsAPI = {
  getStudentResults: (
    params: { page?: number; page_size?: number; search?: string } = {}
  ): Promise<PaginatedStudentResultResponse> => {
    const qp = new URLSearchParams();
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));
    if (params.search) qp.append('search', params.search);

    const qstr = qp.toString();
    return fetchAPI<PaginatedStudentResultResponse>(`/api/student/results${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },

  getStudentResultDetail: (sessionId: string): Promise<StudentResultResponse> => {
    return fetchAPI<StudentResultResponse>(`/api/student/results/${sessionId}`, {
      method: 'GET',
    });
  },

  getExamResults: (
    examId: string,
    params: { page?: number; page_size?: number; search?: string } = {}
  ): Promise<PaginatedStudentResultResponse> => {
    const qp = new URLSearchParams();
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));
    if (params.search) qp.append('search', params.search);

    const qstr = qp.toString();
    return fetchAPI<PaginatedStudentResultResponse>(`/api/exams/${examId}/results${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },

  getExaminerResultDetail: (examId: string, sessionId: string): Promise<StudentResultResponse> => {
    return fetchAPI<StudentResultResponse>(`/api/exams/${examId}/results/${sessionId}`, {
      method: 'GET',
    });
  },

  reviewSubjectiveAnswer: (
    examId: string,
    sessionId: string,
    answerId: string,
    payload: { final_score: number; comment?: string; is_finalized?: boolean }
  ): Promise<StudentResultResponse> => {
    return fetchAPI<StudentResultResponse>(
      `/api/exams/${examId}/results/${sessionId}/answers/${answerId}/review`,
      {
        method: 'PATCH',
        body: JSON.stringify(payload),
      }
    );
  },

  finalizeSubjectiveAnswer: (
    examId: string,
    sessionId: string,
    answerId: string,
    payload: { final_score: number; comment?: string }
  ): Promise<StudentResultResponse> => {
    return fetchAPI<StudentResultResponse>(
      `/api/exams/${examId}/results/${sessionId}/answers/${answerId}/finalize`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  getAllResults: (
    params: { page?: number; page_size?: number; search?: string } = {}
  ): Promise<PaginatedStudentResultResponse> => {
    const qp = new URLSearchParams();
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));
    if (params.search) qp.append('search', params.search);

    const qstr = qp.toString();
    return fetchAPI<PaginatedStudentResultResponse>(`/api/results${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },
};

export interface ExamBasicInfo {
  id: string;
  title: string;
  subject: string;
  status: string;
  total_marks: number;
  passing_marks: number;
}

export interface AnalyticsSummary {
  total_sessions: number;
  evaluated_sessions: number;
  pending_reviews: number;
  finalized_evaluations: number;
  average_score: number;
  average_percentage: number;
  pass_count: number;
  fail_count: number;
  pass_rate: number;
}

export interface ScorePerformance {
  average_percentage: number;
  highest_percentage: number;
  lowest_percentage: number;
  median_percentage: number;
}

export interface ScoreDistribution {
  bucket_0_20: number;
  bucket_21_40: number;
  bucket_41_60: number;
  bucket_61_80: number;
  bucket_81_100: number;
}

export interface PassFailDistribution {
  passed: number;
  failed: number;
  pending_review: number;
}

export interface FinalizedPerformance {
  finalized_sessions: number;
  average_finalized_score: number;
  average_finalized_percentage: number;
  finalized_pass_count: number;
  finalized_fail_count: number;
  finalized_pass_rate: number;
}

export interface QuestionPerformanceItem {
  question_id: string;
  question_order: number;
  question_text: string;
  question_type: string;
  marks: number;
  topic?: string | null;
  difficulty: string;
  attempted_count: number;
  unanswered_count: number;
  correct_count?: number | null;
  incorrect_count?: number | null;
  accuracy_percentage?: number | null;
  evaluated_count?: number | null;
  pending_review_count?: number | null;
  average_score: number;
  average_percentage: number;
}

export interface DifficultyPerformanceItem {
  difficulty: string;
  question_count: number;
  average_percentage: number;
}

export interface TopicPerformanceItem {
  topic: string;
  question_count: number;
  average_percentage: number;
}

export interface PendingReviewItem {
  session_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  pending_question_count: number;
  current_score: number;
  maximum_marks: number;
  submitted_at?: string | null;
  status: string;
}

export interface ExamAnalyticsResponse {
  exam_info: ExamBasicInfo;
  summary: AnalyticsSummary;
  score_performance: ScorePerformance;
  score_distribution: ScoreDistribution;
  pass_fail_distribution: PassFailDistribution;
  finalized_performance: FinalizedPerformance;
  question_performance: QuestionPerformanceItem[];
  difficulty_performance: DifficultyPerformanceItem[];
  topic_performance: TopicPerformanceItem[];
  pending_reviews: PendingReviewItem[];
  student_performance: PaginatedStudentResultResponse;
}

export const analyticsAPI = {
  getExamAnalytics: (
    examId: string,
    params: { page?: number; page_size?: number; search?: string; pass_fail?: string; session_status?: string } = {}
  ): Promise<ExamAnalyticsResponse> => {
    const qp = new URLSearchParams();
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));
    if (params.search) qp.append('search', params.search);
    if (params.pass_fail) qp.append('pass_fail', params.pass_fail);
    if (params.session_status) qp.append('session_status', params.session_status);

    const qstr = qp.toString();
    return fetchAPI<ExamAnalyticsResponse>(`/api/exams/${examId}/analytics${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },
};

export interface IntegrityEvidenceItem {
  signal_type: string;
  title: string;
  count: number;
  severity: string;
  observation: string;
  score_deduction: number;
}

export interface IntegrityTimelineItem {
  timestamp?: string | null;
  event_type: string;
  label: string;
  details?: string | null;
  severity: string;
}

export interface IntegritySignalsSummary {
  tab_switches: number;
  face_alerts: number;
  fullscreen_events: number;
  hardware_alerts: number;
  total_signals: number;
}

export interface SessionIntegrityDetailResponse {
  id: string;
  session_id: string;
  exam_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  session_status: string;
  integrity_score: number;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH';
  analysis_status: string;
  summary: string;
  recommendation: string;
  evidence: IntegrityEvidenceItem[];
  timeline: IntegrityTimelineItem[];
  signals_summary: IntegritySignalsSummary;
  behavioural_summary?: Record<string, any> | null;
  identity_summary?: Record<string, any> | null;
  generated_at: string;
  reviewed_at?: string | null;
}

export interface ExamIntegritySummaryItem {
  session_id: string;
  student_id: string;
  student_name: string;
  student_email: string;
  session_status: string;
  integrity_score: number;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH';
  analysis_status: string;
  total_signals: number;
  tab_switches: number;
  face_alerts: number;
  is_flagged: boolean;
  submitted_at?: string | null;
}

export interface PaginatedExamIntegrityResponse {
  exam_id: string;
  exam_title: string;
  exam_subject: string;
  total_sessions: number;
  average_integrity_score: number;
  high_risk_count: number;
  moderate_risk_count: number;
  low_risk_count: number;
  items: ExamIntegritySummaryItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const integrityAPI = {
  getExamIntegrity: (
    examId: string,
    params: { page?: number; page_size?: number; search?: string; risk_level?: string } = {}
  ): Promise<PaginatedExamIntegrityResponse> => {
    const qp = new URLSearchParams();
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));
    if (params.search) qp.append('search', params.search);
    if (params.risk_level) qp.append('risk_level', params.risk_level);

    const qstr = qp.toString();
    return fetchAPI<PaginatedExamIntegrityResponse>(`/api/exams/${examId}/integrity${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },

  getSessionIntegrity: (examId: string, sessionId: string): Promise<SessionIntegrityDetailResponse> => {
    return fetchAPI<SessionIntegrityDetailResponse>(`/api/exams/${examId}/sessions/${sessionId}/integrity`, {
      method: 'GET',
    });
  },

  getStudentIntegrity: (): Promise<StudentIntegrityOverviewResponse> => {
    return fetchAPI<StudentIntegrityOverviewResponse>('/api/student/integrity', {
      method: 'GET',
    });
  },

  getStudentSessionIntegrity: (sessionId: string): Promise<StudentSessionIntegrityDetailResponse> => {
    return fetchAPI<StudentSessionIntegrityDetailResponse>(`/api/student/integrity/${sessionId}`, {
      method: 'GET',
    });
  },
};

export interface StudentIntegritySummary {
  exams_monitored: number;
  exams_completed: number;
  average_integrity_score: number;
  high_risk_count: number;
  moderate_risk_count: number;
  low_risk_count: number;
}

export interface StudentExamIntegrityItem {
  exam_id: string;
  exam_title: string;
  session_id: string;
  started_at?: string | null;
  submitted_at?: string | null;
  integrity_score: number;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH';
  event_count: number;
  status: string;
}

export interface StudentIntegrityOverviewResponse {
  summary: StudentIntegritySummary;
  exams: StudentExamIntegrityItem[];
}

export interface StudentProctoringEventItem {
  event_type: string;
  title: string;
  occurred_at?: string | null;
  description: string;
  severity: string;
}

export interface StudentBehaviouralMetrics {
  metrics_available: boolean;
  questions_visited?: number | null;
  questions_answered?: number | null;
  answer_changes?: number | null;
  answers_cleared?: number | null;
  navigation_count?: number | null;
  backtracking_count?: number | null;
  avg_question_time?: number | null;
  median_question_time?: number | null;
  rapid_change_clusters?: number | null;
}

export interface StudentEnvironmentMonitoring {
  phone_detected_count: number;
  laptop_detected_count: number;
  book_detected_count: number;
  additional_person_count: number;
  status: string;
  explanation: string;
}

export interface StudentSessionIntegrityDetailResponse {
  exam_id: string;
  exam_title: string;
  exam_subject?: string | null;
  session_id: string;
  session_status: string;
  started_at?: string | null;
  submitted_at?: string | null;
  integrity_score: number;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH';
  status_explanation: string;
  event_count: number;
  event_summary: Record<string, number>;
  events: StudentProctoringEventItem[];
  behavioural_metrics: StudentBehaviouralMetrics;
  environment_monitoring: StudentEnvironmentMonitoring;
}

export const studentIntegrityAPI = {
  getOverview: (): Promise<StudentIntegrityOverviewResponse> => {
    return fetchAPI<StudentIntegrityOverviewResponse>('/api/student/integrity', {
      method: 'GET',
    });
  },
  getSessionDetail: (sessionId: string): Promise<StudentSessionIntegrityDetailResponse> => {
    return fetchAPI<StudentSessionIntegrityDetailResponse>(`/api/student/integrity/${sessionId}`, {
      method: 'GET',
    });
  },
};


export interface IdentityStatusResponse {
  is_face_registered: boolean;
  face_registered_at?: string | null;
  descriptor_version?: number | null;
  requires_re_enrollment?: boolean;
  current_system_version?: number;
}

export interface FaceRegistrationResponse {
  is_face_registered: boolean;
  face_registered_at: string;
  message: string;
  descriptor_version: number;
}

export interface IdentityVerificationResponse {
  verified: boolean;
  status: string;
  message: string;
  mismatch_duration_seconds?: number;
  similarity?: number;
  descriptor_version?: number;
}

export const identityAPI = {
  getStatus: (): Promise<IdentityStatusResponse> => {
    return fetchAPI<IdentityStatusResponse>('/api/student/identity/status', {
      method: 'GET',
    });
  },

  registerFace: (payload: { face_embedding: number[]; consent_given: boolean; descriptor_version?: number }): Promise<FaceRegistrationResponse> => {
    return fetchAPI<FaceRegistrationResponse>('/api/student/identity/register-face', {
      method: 'POST',
      body: JSON.stringify({ ...payload, descriptor_version: payload.descriptor_version || 2 }),
    });
  },

  clearFace: (): Promise<{ message: string }> => {
    return fetchAPI<{ message: string }>('/api/student/identity/face', {
      method: 'DELETE',
    });
  },

  verifySessionIdentity: (
    sessionId: string,
    payload: { face_embedding: number[]; descriptor_version?: number }
  ): Promise<IdentityVerificationResponse> => {
    return fetchAPI<IdentityVerificationResponse>(
      `/api/student/sessions/${sessionId}/verify-identity`,
      {
        method: 'POST',
        body: JSON.stringify({ ...payload, descriptor_version: payload.descriptor_version || 2 }),
      }
    );
  },
};

export interface CrossStudentWrongAnswerItem {
  question_id: string;
  question_number: number;
  question_text: string;
  student_a_option: string;
  student_b_option: string;
  correct_option: string;
}

export interface CrossStudentTextMatchItem {
  question_id: string;
  question_number: number;
  question_text: string;
  student_a_text: string;
  student_b_text: string;
  similarity_score: number;
}

export interface CrossStudentPairSummaryItem {
  id: string;
  exam_id: string;
  source_session_id: string;
  target_session_id: string;
  source_student_id: string;
  source_student_name: string;
  source_student_email: string;
  target_student_id: string;
  target_student_name: string;
  target_student_email: string;
  similarity_score: number;
  answer_similarity: number;
  wrong_answer_similarity: number;
  timing_similarity?: number | null;
  answer_change_similarity?: number | null;
  navigation_similarity?: number | null;
  same_incorrect_answers_count: number;
  same_correct_answers_count: number;
  category: 'LOW_SIMILARITY' | 'MODERATE_SIMILARITY' | 'HIGH_SIMILARITY';
  cluster_id?: string | null;
}

export interface CrossStudentClusterStudentItem {
  student_id: string;
  student_name: string;
  student_email: string;
  session_id: string;
}

export interface CrossStudentClusterItem {
  cluster_id: string;
  student_count: number;
  average_similarity: number;
  students: CrossStudentClusterStudentItem[];
  key_evidence: string[];
}

export interface CrossStudentPairDetailResponse {
  id: string;
  exam_id: string;
  exam_title: string;
  source_session_id: string;
  target_session_id: string;
  source_student_id: string;
  source_student_name: string;
  source_student_email: string;
  target_student_id: string;
  target_student_name: string;
  target_student_email: string;
  similarity_score: number;
  category: 'LOW_SIMILARITY' | 'MODERATE_SIMILARITY' | 'HIGH_SIMILARITY';
  answer_similarity: number;
  wrong_answer_similarity: number;
  timing_similarity?: number | null;
  answer_change_similarity?: number | null;
  navigation_similarity?: number | null;
  same_incorrect_answers_count: number;
  same_correct_answers_count: number;
  total_comparable_questions: number;
  evidence_items: string[];
  common_wrong_answers: CrossStudentWrongAnswerItem[];
  text_matches: CrossStudentTextMatchItem[];
  per_question_timing: Record<string, any>[];
  answer_change_sequences: Record<string, any>[];
  navigation_sequences: Record<string, any>[];
  generated_at: string;
}

export interface PaginatedCrossStudentAnalysisResponse {
  exam_id: string;
  exam_title: string;
  analyzed_students_count: number;
  total_pairs_count: number;
  high_similarity_pairs_count: number;
  moderate_similarity_pairs_count: number;
  low_similarity_pairs_count: number;
  last_analyzed_at?: string | null;
  clusters: CrossStudentClusterItem[];
  items: CrossStudentPairSummaryItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const crossStudentAPI = {
  runAnalysis: (examId: string): Promise<{ message: string; analyzed_students_count: number; total_pairs_count: number }> => {
    return fetchAPI<{ message: string; analyzed_students_count: number; total_pairs_count: number }>(
      `/api/exams/${examId}/cross-student-analysis/run`,
      { method: 'POST' }
    );
  },

  getSummary: (
    examId: string,
    params: { page?: number; page_size?: number; min_similarity?: number; cluster_id?: string } = {}
  ): Promise<PaginatedCrossStudentAnalysisResponse> => {
    const qp = new URLSearchParams();
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));
    if (params.min_similarity !== undefined) qp.append('min_similarity', String(params.min_similarity));
    if (params.cluster_id) qp.append('cluster_id', params.cluster_id);

    const qstr = qp.toString();
    return fetchAPI<PaginatedCrossStudentAnalysisResponse>(
      `/api/exams/${examId}/cross-student-analysis${qstr ? `?${qstr}` : ''}`,
      { method: 'GET' }
    );
  },

  getPairDetail: (examId: string, analysisId: string): Promise<CrossStudentPairDetailResponse> => {
    return fetchAPI<CrossStudentPairDetailResponse>(
      `/api/exams/${examId}/cross-student-analysis/${analysisId}`,
      { method: 'GET' }
    );
  },
};

export interface AdminUserCreateInput {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: 'STUDENT' | 'EXAMINER';
}

export interface AdminUserStatusUpdateInput {
  is_active: boolean;
}

export interface AdminUserRoleUpdateInput {
  role: 'STUDENT' | 'EXAMINER';
}

export interface PaginatedUsersResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const adminAPI = {
  getUsers: (params: { page?: number; page_size?: number; search?: string; role?: string; is_active?: boolean } = {}): Promise<PaginatedUsersResponse> => {
    const qp = new URLSearchParams();
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));
    if (params.search) qp.append('search', params.search);
    if (params.role) qp.append('role', params.role);
    if (params.is_active !== undefined) qp.append('is_active', String(params.is_active));

    const qstr = qp.toString();
    return fetchAPI<PaginatedUsersResponse>(`/api/admin/users${qstr ? `?${qstr}` : ''}`, { method: 'GET' });
  },

  createUser: (data: AdminUserCreateInput): Promise<User> => {
    return fetchAPI<User>('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updateUserStatus: (userId: string, is_active: boolean): Promise<User> => {
    return fetchAPI<User>(`/api/admin/users/${userId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ is_active }),
    });
  },

  updateUserRole: (userId: string, role: 'STUDENT' | 'EXAMINER'): Promise<User> => {
    return fetchAPI<User>(`/api/admin/users/${userId}/role`, {
      method: 'PUT',
      body: JSON.stringify({ role }),
    });
  },
};

// ==========================================
// ADMIN STUDENT MANAGEMENT TYPES & API
// ==========================================

export interface AdminStudentListItem {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'STUDENT';
  is_active: boolean;
  college_id?: string | null;
  college_name?: string | null;
  college_code?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  department_code?: string | null;
  year_of_study?: number | null;
  section_id?: string | null;
  section_name?: string | null;
  section_code?: string | null;
  is_face_registered: boolean;
  face_registered_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminStudentSummaryMetrics {
  total_students: number;
  active_students: number;
  inactive_students: number;
  unassigned_academic_profiles: number;
}

export interface PaginatedAdminStudentResponse {
  items: AdminStudentListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: AdminStudentSummaryMetrics;
}

export interface AdminStudentRecentSessionItem {
  session_id: string;
  exam_id: string;
  exam_title: string;
  exam_subject: string;
  status: string;
  started_at?: string | null;
  submitted_at?: string | null;
  percentage?: number | null;
  pass_fail_status?: string | null;
}

export interface AdminStudentDetailResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'STUDENT';
  is_active: boolean;
  college_id?: string | null;
  college_name?: string | null;
  college_code?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  department_code?: string | null;
  year_of_study?: number | null;
  section_id?: string | null;
  section_name?: string | null;
  section_code?: string | null;
  is_face_registered: boolean;
  face_registered_at?: string | null;
  created_at: string;
  updated_at: string;
  exams_assigned_count: number;
  exams_attempted_count: number;
  exams_completed_count: number;
  recent_sessions: AdminStudentRecentSessionItem[];
}

export const adminStudentsAPI = {
  list: (params: {
    search?: string;
    college_id?: string;
    department_id?: string;
    year_of_study?: number;
    section_id?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedAdminStudentResponse> => {
    const qp = new URLSearchParams();
    if (params.search) qp.append('search', params.search);
    if (params.college_id) qp.append('college_id', params.college_id);
    if (params.department_id) qp.append('department_id', params.department_id);
    if (params.year_of_study) qp.append('year_of_study', String(params.year_of_study));
    if (params.section_id) qp.append('section_id', params.section_id);
    if (params.is_active !== undefined) qp.append('is_active', String(params.is_active));
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));

    const qstr = qp.toString();
    return fetchAPI<PaginatedAdminStudentResponse>(`/api/admin/students${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },

  getDetail: (studentId: string): Promise<AdminStudentDetailResponse> => {
    return fetchAPI<AdminStudentDetailResponse>(`/api/admin/students/${studentId}`, {
      method: 'GET',
    });
  },
};

// ==========================================
// ADMIN EXAMINER MANAGEMENT TYPES & API
// ==========================================

export interface AdminExaminerListItem {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'EXAMINER';
  is_active: boolean;
  college_id?: string | null;
  college_name?: string | null;
  college_code?: string | null;
  total_exams_count: number;
  published_exams_count: number;
  created_at: string;
  updated_at: string;
}

export interface AdminExaminerSummaryMetrics {
  total_examiners: number;
  active_examiners: number;
  inactive_examiners: number;
  unassigned_college: number;
}

export interface PaginatedAdminExaminerResponse {
  items: AdminExaminerListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: AdminExaminerSummaryMetrics;
}

export interface AdminExaminerRecentExamItem {
  id: string;
  title: string;
  subject: string;
  status: string;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  target_type?: string | null;
  created_at: string;
  start_at?: string | null;
  end_at?: string | null;
}

export interface AdminExaminerDetailResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'EXAMINER';
  is_active: boolean;
  college_id?: string | null;
  college_name?: string | null;
  college_code?: string | null;
  created_at: string;
  updated_at: string;
  total_exams_created: number;
  published_exams_count: number;
  draft_exams_count: number;
  completed_exams_count: number;
  recent_exams: AdminExaminerRecentExamItem[];
}

export const adminExaminersAPI = {
  list: (params: {
    search?: string;
    college_id?: string;
    is_active?: boolean;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedAdminExaminerResponse> => {
    const qp = new URLSearchParams();
    if (params.search) qp.append('search', params.search);
    if (params.college_id) qp.append('college_id', params.college_id);
    if (params.is_active !== undefined) qp.append('is_active', String(params.is_active));
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));

    const qstr = qp.toString();
    return fetchAPI<PaginatedAdminExaminerResponse>(`/api/admin/examiners${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },

  getDetail: (examinerId: string): Promise<AdminExaminerDetailResponse> => {
    return fetchAPI<AdminExaminerDetailResponse>(`/api/admin/examiners/${examinerId}`, {
      method: 'GET',
    });
  },
};

// ==========================================
// ADMIN EXAMS MANAGEMENT TYPES & API
// ==========================================

export interface AdminExamListItem {
  id: string;
  title: string;
  subject: string;
  status: ExamStatus;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  question_count: number;
  created_by: string;
  examiner_name: string;
  examiner_email: string;
  examiner_college_name?: string | null;
  examiner_college_code?: string | null;
  target_type?: ExamTargetType | null;
  target_description: string;
  eligible_students_count: number;
  sessions_count: number;
  completed_sessions_count: number;
  created_at: string;
  start_at?: string | null;
  end_at?: string | null;
}

export interface AdminExamSummaryMetrics {
  total_exams: number;
  published_active_exams: number;
  completed_exams: number;
  draft_exams: number;
}

export interface PaginatedAdminExamResponse {
  items: AdminExamListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary: AdminExamSummaryMetrics;
}

export interface AdminExamDetailResponse {
  id: string;
  title: string;
  subject: string;
  description?: string | null;
  instructions?: string | null;
  status: ExamStatus;
  duration_minutes: number;
  total_marks: number;
  passing_marks: number;
  negative_marking_enabled: boolean;
  randomize_questions: boolean;
  randomize_options: boolean;
  proctoring_enabled: boolean;
  max_tab_switches: number;
  created_at: string;
  updated_at: string;
  start_at?: string | null;
  end_at?: string | null;

  created_by: string;
  examiner_name: string;
  examiner_email: string;
  examiner_college_name?: string | null;
  examiner_college_code?: string | null;

  target_type?: ExamTargetType | null;
  target_description: string;
  target_college_name?: string | null;
  target_department_name?: string | null;
  target_year_of_study?: number | null;
  target_section_name?: string | null;
  target_specific_students_count: number;
  eligible_students_count: number;

  total_sessions_count: number;
  completed_sessions_count: number;
  in_progress_sessions_count: number;
  other_sessions_count: number;

  question_count: number;
  mcq_count: number;
  multi_select_count: number;
  short_answer_count: number;
  long_answer_count: number;
  handwritten_count: number;
}

export const adminExamsAPI = {
  list: (params: {
    search?: string;
    subject?: string;
    examiner_id?: string;
    college_id?: string;
    status?: string;
    target_type?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<PaginatedAdminExamResponse> => {
    const qp = new URLSearchParams();
    if (params.search) qp.append('search', params.search);
    if (params.subject) qp.append('subject', params.subject);
    if (params.examiner_id) qp.append('examiner_id', params.examiner_id);
    if (params.college_id) qp.append('college_id', params.college_id);
    if (params.status) qp.append('status', params.status);
    if (params.target_type) qp.append('target_type', params.target_type);
    if (params.page) qp.append('page', String(params.page));
    if (params.page_size) qp.append('page_size', String(params.page_size));

    const qstr = qp.toString();
    return fetchAPI<PaginatedAdminExamResponse>(`/api/admin/exams${qstr ? `?${qstr}` : ''}`, {
      method: 'GET',
    });
  },

  getDetail: (examId: string): Promise<AdminExamDetailResponse> => {
    return fetchAPI<AdminExamDetailResponse>(`/api/admin/exams/${examId}`, {
      method: 'GET',
    });
  },
};




// ==========================================
// ACADEMIC & INSTITUTION TYPES & API
// ==========================================

export interface College {
  id: string;
  name: string;
  code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: string;
  college_id: string;
  name: string;
  code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Section {
  id: string;
  department_id: string;
  year_of_study: number;
  name: string;
  code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CollegeCreateInput {
  name: string;
  code: string;
}

export interface DepartmentCreateInput {
  college_id: string;
  name: string;
  code: string;
}

export interface SectionCreateInput {
  department_id: string;
  year_of_study: number;
  name: string;
  code: string;
}

export interface StudentAcademicProfileInput {
  college_id?: string | null;
  department_id?: string | null;
  year_of_study?: number | null;
  section_id?: string | null;
}

export const academicAPI = {
  // Public / Examiner Lookups
  getPublicColleges: (): Promise<College[]> => {
    return fetchAPI<College[]>('/api/academic/colleges', { method: 'GET' });
  },
  getPublicDepartments: (collegeId?: string): Promise<Department[]> => {
    const qp = collegeId ? `?college_id=${collegeId}` : '';
    return fetchAPI<Department[]>(`/api/academic/departments${qp}`, { method: 'GET' });
  },
  getPublicSections: (departmentId?: string, yearOfStudy?: number): Promise<Section[]> => {
    const qp = new URLSearchParams();
    if (departmentId) qp.append('department_id', departmentId);
    if (yearOfStudy) qp.append('year_of_study', String(yearOfStudy));
    const qstr = qp.toString();
    return fetchAPI<Section[]>(`/api/academic/sections${qstr ? `?${qstr}` : ''}`, { method: 'GET' });
  },
  getCollegeStudents: (params: { search?: string; department_id?: string; year_of_study?: number; section_id?: string } = {}): Promise<User[]> => {
    const qp = new URLSearchParams();
    if (params.search) qp.append('search', params.search);
    if (params.department_id) qp.append('department_id', params.department_id);
    if (params.year_of_study) qp.append('year_of_study', String(params.year_of_study));
    if (params.section_id) qp.append('section_id', params.section_id);
    const qstr = qp.toString();
    return fetchAPI<User[]>(`/api/academic/students${qstr ? `?${qstr}` : ''}`, { method: 'GET' });
  },

  // Admin College Management
  listCollegesAdmin: (isActive?: boolean): Promise<College[]> => {
    const qp = isActive !== undefined ? `?is_active=${isActive}` : '';
    return fetchAPI<College[]>(`/api/admin/colleges${qp}`, { method: 'GET' });
  },
  createCollege: (data: CollegeCreateInput): Promise<College> => {
    return fetchAPI<College>('/api/admin/colleges', { method: 'POST', body: JSON.stringify(data) });
  },
  updateCollege: (id: string, data: Partial<CollegeCreateInput & { is_active: boolean }>): Promise<College> => {
    return fetchAPI<College>(`/api/admin/colleges/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  },

  // Admin Department Management
  listDepartmentsAdmin: (collegeId?: string, isActive?: boolean): Promise<Department[]> => {
    const qp = new URLSearchParams();
    if (collegeId) qp.append('college_id', collegeId);
    if (isActive !== undefined) qp.append('is_active', String(isActive));
    const qstr = qp.toString();
    return fetchAPI<Department[]>(`/api/admin/departments${qstr ? `?${qstr}` : ''}`, { method: 'GET' });
  },
  createDepartment: (data: DepartmentCreateInput): Promise<Department> => {
    return fetchAPI<Department>('/api/admin/departments', { method: 'POST', body: JSON.stringify(data) });
  },
  updateDepartment: (id: string, data: Partial<{ name: string; code: string; is_active: boolean }>): Promise<Department> => {
    return fetchAPI<Department>(`/api/admin/departments/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  },

  // Admin Section Management
  listSectionsAdmin: (departmentId?: string, yearOfStudy?: number, isActive?: boolean): Promise<Section[]> => {
    const qp = new URLSearchParams();
    if (departmentId) qp.append('department_id', departmentId);
    if (yearOfStudy) qp.append('year_of_study', String(yearOfStudy));
    if (isActive !== undefined) qp.append('is_active', String(isActive));
    const qstr = qp.toString();
    return fetchAPI<Section[]>(`/api/admin/sections${qstr ? `?${qstr}` : ''}`, { method: 'GET' });
  },
  createSection: (data: SectionCreateInput): Promise<Section> => {
    return fetchAPI<Section>('/api/admin/sections', { method: 'POST', body: JSON.stringify(data) });
  },
  updateSection: (id: string, data: Partial<{ name: string; code: string; is_active: boolean }>): Promise<Section> => {
    return fetchAPI<Section>(`/api/admin/sections/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  },

  // Admin Student / Examiner Assignment
  updateStudentAcademicProfile: (studentId: string, data: StudentAcademicProfileInput): Promise<User> => {
    return fetchAPI<User>(`/api/admin/students/${studentId}/academic-profile`, { method: 'PUT', body: JSON.stringify(data) });
  },
  updateUserCollege: (userId: string, collegeId: string | null): Promise<User> => {
    return fetchAPI<User>(`/api/admin/users/${userId}/college`, { method: 'PUT', body: JSON.stringify({ college_id: collegeId }) });
  },
};

export interface UserProfileUpdateInput {
  first_name: string;
  last_name?: string;
}

export interface UserPasswordChangeInput {
  current_password: string;
  new_password: string;
}

export interface NotificationSettings {
  exam_reminders: boolean;
  result_notifications: boolean;
  integrity_alerts: boolean;
  system_updates: boolean;
}

export const userAPI = {
  getProfile: (): Promise<User> => {
    return fetchAPI<User>('/api/users/me/profile', { method: 'GET' });
  },
  updateProfile: (data: UserProfileUpdateInput): Promise<User> => {
    return fetchAPI<User>('/api/users/me/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
  changePassword: (data: UserPasswordChangeInput): Promise<{ message: string }> => {
    return fetchAPI<{ message: string }>('/api/users/me/password', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
  getSettings: (): Promise<NotificationSettings> => {
    return fetchAPI<NotificationSettings>('/api/users/me/settings', { method: 'GET' });
  },
  updateSettings: (data: NotificationSettings): Promise<NotificationSettings> => {
    return fetchAPI<NotificationSettings>('/api/users/me/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
};




