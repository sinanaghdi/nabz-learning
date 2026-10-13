export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");

export type ApiErrorBody = { detail?: string | { msg?: string }[] };

export async function apiRequest<T>(
  path: string,
  token?: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", "Bearer " + token);
  }

  let response: Response;
  try {
    response = await fetch(API_BASE + path, { ...init, headers, cache: "no-store" });
  } catch {
    throw new Error("ارتباط با سرور برقرار نشد. وضعیت API و نشانی سرور را بررسی کنید.");
  }

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const body = payload as ApiErrorBody | null;
    let message = "درخواست انجام نشد. دوباره تلاش کنید.";
    if (typeof body?.detail === "string") message = body.detail;
    else if (Array.isArray(body?.detail)) {
      message = body.detail.map((item) => item.msg || "ورودی نامعتبر").join("، ");
    }
    throw new Error(message);
  }

  return payload as T;
}

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: "student" | "instructor" | "admin";
  is_active: boolean;
};

export type Course = {
  id: number;
  instructor_id: number;
  title: string;
  description: string | null;
  term: string | null;
  is_active: boolean;
  created_at: string;
  enrollment_code?: string;
};

export type Topic = {
  id: number;
  course_id: number;
  title: string;
  description: string | null;
  sort_order: number;
  created_at: string;
};

export type QuestionOption = {
  id: number;
  text: string;
  is_correct: boolean;
  position: number;
};

export type Question = {
  id: number;
  topic_id: number;
  prompt: string;
  explanation: string | null;
  difficulty: "easy" | "medium" | "hard";
  status: "draft" | "published" | "archived";
  options: QuestionOption[];
};

export type Assessment = {
  id: number;
  course_id: number;
  title: string;
  instructions: string | null;
  status: "draft" | "published" | "closed";
  duration_minutes: number | null;
  max_attempts: number;
  question_count: number;
  created_at: string;
  published_at: string | null;
};

export type StudentQuestion = {
  id: number;
  prompt: string;
  options: { id: number; text: string; position: number }[];
};

export type AssessmentDetail = Assessment & { questions: StudentQuestion[] };

export type Attempt = {
  id: number;
  assessment_id: number;
  student_id: number;
  attempt_number: number;
  status: "in_progress" | "submitted";
  question_count: number;
  correct_count: number | null;
  score_percent: number | null;
  started_at: string;
  submitted_at: string | null;
};

export type CourseAnalytics = {
  course_id: number;
  course_title: string;
  enrolled_students: number;
  published_assessments: number;
  submitted_attempts: number;
  students_with_submissions: number;
  average_score_percent: number | null;
  best_score_percent: number | null;
  lowest_score_percent: number | null;
};

export type TopicAnalytics = {
  topic_id: number;
  topic_title: string;
  question_presentations: number;
  correct_responses: number;
  accuracy_percent: number | null;
  needs_review: boolean;
};

export type StudentSummary = {
  student_id: number;
  full_name: string;
  email: string;
  submitted_attempts: number;
  average_score_percent: number | null;
  best_score_percent: number | null;
  last_submitted_at: string | null;
};

export type LeaderboardEntry = {
  rank: number | null;
  display_name: string;
  submitted_attempts: number;
  average_score_percent: number | null;
  best_score_percent: number | null;
  last_submitted_at: string | null;
  is_current_user: boolean;
};

export type CourseStudent = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  enrolled_at: string;
};

export type CreatedCourse = Course & { enrollment_code: string };
export type Enrollment = { id: number; course_id: number; student_id: number; enrolled_at: string };
export type AttemptDetail = Attempt & {
  answers: { question_id: number; selected_option_id: number }[];
};
