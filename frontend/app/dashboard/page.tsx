"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { FormEvent, ReactNode } from "react";

import {
  apiRequest,
  type Assessment,
  type AssessmentDetail,
  type Attempt,
  type Course,
  type CourseAnalytics,
  type CourseStudent,
  type CreatedCourse,
  type Question,
  type StudentSummary,
  type Topic,
  type TopicAnalytics,
  type User,
} from "../../lib/api";

type NavKey = "overview" | "courses" | "topics" | "questions" | "assessments" | "analytics" | "students";
type Flash = { kind: "success" | "error" | "info"; text: string };
type ExamSession = {
  assessment: AssessmentDetail;
  attempt: Attempt;
  answers: Record<string, number>;
};
type ResultNotice = { title: string; score: number; correct: number; total: number } | null;

const teacherNav: { key: NavKey; title: string; icon: string }[] = [
  { key: "overview", title: "نمای کلی", icon: "◫" },
  { key: "courses", title: "درس‌های من", icon: "▤" },
  { key: "topics", title: "مباحث درس", icon: "◉" },
  { key: "questions", title: "بانک سؤال", icon: "▦" },
  { key: "assessments", title: "آزمون‌ها", icon: "☷" },
  { key: "analytics", title: "تحلیل یادگیری", icon: "⌁" },
  { key: "students", title: "دانشجویان", icon: "♙" },
];
const studentNav: { key: NavKey; title: string; icon: string }[] = [
  { key: "overview", title: "نمای کلی", icon: "◫" },
  { key: "courses", title: "درس‌های من", icon: "▤" },
  { key: "assessments", title: "آزمون‌ها", icon: "☷" },
];

function dateText(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("fa-IR", { year: "numeric", month: "short", day: "numeric" }).format(date);
}

function scoreText(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 }).format(value) + "٪";
}

function countText(value: number | null | undefined): string {
  return new Intl.NumberFormat("fa-IR").format(value || 0);
}

function statusText(status: string): string {
  const values: Record<string, string> = {
    draft: "پیش‌نویس",
    published: "منتشرشده",
    closed: "بسته‌شده",
    submitted: "ارسال‌شده",
    in_progress: "در حال انجام",
    easy: "آسان",
    medium: "متوسط",
    hard: "دشوار",
  };
  return values[status] || status;
}

function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-symbol" aria-hidden="true">◌</span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

function MetricCard({
  label,
  value,
  note,
  icon,
  tone = "jade",
}: {
  label: string;
  value: string;
  note: string;
  icon: string;
  tone?: "jade" | "gold" | "blue" | "plum";
}) {
  return (
    <article className="metric-card">
      <div className={"metric-icon metric-icon-" + tone} aria-hidden="true">{icon}</div>
      <div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>
    </article>
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [contentLoading, setContentLoading] = useState(false);
  const [courses, setCourses] = useState<Course[]>([]);
  const [courseId, setCourseId] = useState<number | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [overview, setOverview] = useState<CourseAnalytics | null>(null);
  const [topicAnalytics, setTopicAnalytics] = useState<TopicAnalytics[]>([]);
  const [studentSummaries, setStudentSummaries] = useState<StudentSummary[]>([]);
  const [roster, setRoster] = useState<CourseStudent[]>([]);
  const [activeNav, setActiveNav] = useState<NavKey>("overview");
  const [flash, setFlash] = useState<Flash | null>(null);
  const [modal, setModal] = useState<"course" | "join" | "topic" | "question" | "assessment" | null>(null);
  const [courseTitle, setCourseTitle] = useState("");
  const [courseTerm, setCourseTerm] = useState("");
  const [courseDescription, setCourseDescription] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [topicTitle, setTopicTitle] = useState("");
  const [topicDescription, setTopicDescription] = useState("");
  const [questionPrompt, setQuestionPrompt] = useState("");
  const [questionTopicId, setQuestionTopicId] = useState("");
  const [questionExplanation, setQuestionExplanation] = useState("");
  const [optionOne, setOptionOne] = useState("");
  const [optionTwo, setOptionTwo] = useState("");
  const [correctOption, setCorrectOption] = useState("0");
  const [questionDifficulty, setQuestionDifficulty] = useState("medium");
  const [assessmentTitle, setAssessmentTitle] = useState("");
  const [assessmentInstructions, setAssessmentInstructions] = useState("");
  const [assessmentDuration, setAssessmentDuration] = useState("");
  const [assessmentAttempts, setAssessmentAttempts] = useState("1");
  const [assessmentQuestionIds, setAssessmentQuestionIds] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [busyAction, setBusyAction] = useState(false);
  const [exam, setExam] = useState<ExamSession | null>(null);
  const [lastResult, setLastResult] = useState<ResultNotice>(null);

  const canManage = user?.role === "instructor" || user?.role === "admin";
  const selectedCourse = courses.find((course) => course.id === courseId) || null;
  const navItems = canManage ? teacherNav : studentNav;
  const currentNav = navItems.find((item) => item.key === activeNav) || navItems[0];
  const filteredQuestions = useMemo(() => {
    const query = searchTerm.trim().toLocaleLowerCase();
    if (!query) return questions;
    return questions.filter((question) => question.prompt.toLocaleLowerCase().includes(query));
  }, [questions, searchTerm]);
  const publishedQuestions = questions.filter((question) => question.status === "published");

  useEffect(() => {
    const savedToken = window.localStorage.getItem("nabz_access_token");
    if (!savedToken) {
      router.replace("/login");
      return;
    }
    apiRequest<User>("/auth/me", savedToken)
      .then((profile) => {
        setToken(savedToken);
        setUser(profile);
        window.localStorage.setItem("nabz_user", JSON.stringify(profile));
      })
      .catch(() => {
        window.localStorage.removeItem("nabz_access_token");
        window.localStorage.removeItem("nabz_user");
        router.replace("/login");
      })
      .finally(() => setAuthLoading(false));
  }, [router]);

  const loadCourses = useCallback(async (accessToken: string) => {
    const result = await apiRequest<Course[]>("/courses", accessToken);
    setCourses(result);
    setCourseId((current) => {
      if (current !== null && result.some((course) => course.id === current)) return current;
      return result.length ? result[0].id : null;
    });
    return result;
  }, []);

  useEffect(() => {
    if (!token || !user) return;
    let ignore = false;
    Promise.resolve()
      .then(() => {
        if (!ignore) setWorkspaceLoading(true);
        return apiRequest<Course[]>("/courses", token);
      })
      .then((result) => {
        if (ignore) return;
        setCourses(result);
        setCourseId((current) => {
          if (current !== null && result.some((course) => course.id === current)) return current;
          return result.length ? result[0].id : null;
        });
      })
      .catch((caught: unknown) => {
        if (!ignore) setFlash({ kind: "error", text: caught instanceof Error ? caught.message : "دریافت درس‌ها ناموفق بود." });
      })
      .finally(() => {
        if (!ignore) setWorkspaceLoading(false);
      });
    return () => { ignore = true; };
  }, [token, user]);

  useEffect(() => {
    if (!token || !user || !courseId) return;
    let ignore = false;
    const base = "/courses/" + courseId;
    const coreRequests = [
      apiRequest<Topic[]>(base + "/topics", token),
      apiRequest<Assessment[]>(base + "/assessments", token),
    ];
    const additionalRequests = canManage
      ? [
          apiRequest<Question[]>(base + "/questions", token),
          apiRequest<CourseStudent[]>(base + "/students", token),
          apiRequest<CourseAnalytics>(base + "/analytics/overview", token),
          apiRequest<TopicAnalytics[]>(base + "/analytics/topics", token),
          apiRequest<StudentSummary[]>(base + "/analytics/students", token),
        ]
      : [];
    Promise.resolve()
      .then(() => {
        if (!ignore) setContentLoading(true);
        return Promise.all([...coreRequests, ...additionalRequests]);
      })
      .then((data) => {
        if (ignore) return;
        setTopics(data[0] as Topic[]);
        setAssessments(data[1] as Assessment[]);
        if (canManage) {
          setQuestions(data[2] as Question[]);
          setRoster(data[3] as CourseStudent[]);
          setOverview(data[4] as CourseAnalytics);
          setTopicAnalytics(data[5] as TopicAnalytics[]);
          setStudentSummaries(data[6] as StudentSummary[]);
        } else {
          setQuestions([]);
          setRoster([]);
          setOverview(null);
          setTopicAnalytics([]);
          setStudentSummaries([]);
        }
      })
      .catch((caught: unknown) => {
        if (!ignore) {
          setFlash({ kind: "error", text: caught instanceof Error ? caught.message : "دریافت اطلاعات درس ناموفق بود." });
        }
      })
      .finally(() => {
        if (!ignore) setContentLoading(false);
      });
    return () => { ignore = true; };
  }, [token, user, courseId, canManage]);

  function notify(kind: Flash["kind"], text: string) {
    setFlash({ kind, text });
  }

  function signOut() {
    localStorage.removeItem("nabz_access_token");
    localStorage.removeItem("nabz_user");
    router.replace("/login");
  }

  async function createCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusyAction(true);
    try {
      const created = await apiRequest<CreatedCourse>("/courses", token, {
        method: "POST",
        body: JSON.stringify({
          title: courseTitle,
          description: courseDescription || null,
          term: courseTerm || null,
        }),
      });
      setCourses((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setCourseId(created.id);
      setCourseTitle("");
      setCourseTerm("");
      setCourseDescription("");
      setModal(null);
      setActiveNav("overview");
      notify("success", "درس ساخته شد. کد عضویت: " + created.enrollment_code);
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "ساخت درس ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  async function joinCourse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setBusyAction(true);
    try {
      await apiRequest("/courses/enroll", token, {
        method: "POST",
        body: JSON.stringify({ enrollment_code: joinCode.trim().toUpperCase() }),
      });
      const updated = await loadCourses(token);
      setJoinCode("");
      setModal(null);
      setActiveNav("overview");
      notify("success", "با موفقیت به درس پیوستید.");
      if (!updated.length) setCourseId(null);
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "عضویت در درس ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  async function createTopic(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !courseId) return;
    setBusyAction(true);
    try {
      const topic = await apiRequest<Topic>("/courses/" + courseId + "/topics", token, {
        method: "POST",
        body: JSON.stringify({ title: topicTitle, description: topicDescription || null, sort_order: topics.length + 1 }),
      });
      setTopics((current) => [...current, topic]);
      setTopicTitle("");
      setTopicDescription("");
      setModal(null);
      notify("success", "مبحث به درس اضافه شد.");
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "ساخت مبحث ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  async function createQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !courseId) return;
    setBusyAction(true);
    try {
      const question = await apiRequest<Question>("/courses/" + courseId + "/questions", token, {
        method: "POST",
        body: JSON.stringify({
          topic_id: Number(questionTopicId),
          prompt: questionPrompt,
          explanation: questionExplanation || null,
          difficulty: questionDifficulty,
          status: "published",
          options: [
            { text: optionOne, is_correct: correctOption === "0" },
            { text: optionTwo, is_correct: correctOption === "1" },
          ],
        }),
      });
      setQuestions((current) => [question, ...current]);
      setQuestionPrompt("");
      setQuestionExplanation("");
      setOptionOne("");
      setOptionTwo("");
      setCorrectOption("0");
      setModal(null);
      notify("success", "سؤال منتشرشده به بانک سؤال اضافه شد.");
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "ساخت سؤال ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  async function createAssessment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !courseId) return;
    if (!assessmentQuestionIds.length) {
      notify("error", "حداقل یک سؤال منتشرشده انتخاب کنید.");
      return;
    }
    setBusyAction(true);
    try {
      const assessment = await apiRequest<Assessment>("/courses/" + courseId + "/assessments", token, {
        method: "POST",
        body: JSON.stringify({
          title: assessmentTitle,
          instructions: assessmentInstructions || null,
          question_ids: assessmentQuestionIds,
          duration_minutes: assessmentDuration ? Number(assessmentDuration) : null,
          max_attempts: Number(assessmentAttempts),
        }),
      });
      setAssessments((current) => [assessment, ...current]);
      setAssessmentTitle("");
      setAssessmentInstructions("");
      setAssessmentDuration("");
      setAssessmentAttempts("1");
      setAssessmentQuestionIds([]);
      setModal(null);
      notify("success", "پیش‌نویس آزمون ساخته شد. برای نمایش به دانشجو آن را منتشر کنید.");
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "ساخت آزمون ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  async function publishAssessment(assessment: Assessment) {
    if (!token || !courseId) return;
    setBusyAction(true);
    try {
      const updated = await apiRequest<Assessment>(
        "/courses/" + courseId + "/assessments/" + assessment.id + "/publish",
        token,
        { method: "POST" },
      );
      setAssessments((current) => current.map((item) => item.id === updated.id ? updated : item));
      notify("success", "آزمون منتشر شد و برای دانشجویان ثبت‌نام‌شده قابل مشاهده است.");
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "انتشار آزمون ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  async function startAssessment(assessment: Assessment) {
    if (!token || !courseId) return;
    setBusyAction(true);
    try {
      const detail = await apiRequest<AssessmentDetail>(
        "/courses/" + courseId + "/assessments/" + assessment.id,
        token,
      );
      const attempt = await apiRequest<Attempt>(
        "/courses/" + courseId + "/assessments/" + assessment.id + "/attempts",
        token,
        { method: "POST" },
      );
      setExam({ assessment: detail, attempt, answers: {} });
      setLastResult(null);
      setActiveNav("assessments");
      setFlash(null);
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "شروع آزمون ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  async function saveAnswer(questionId: number, optionId: number) {
    if (!token || !exam) return;
    setExam((current) => current ? {
      ...current,
      answers: { ...current.answers, [String(questionId)]: optionId },
    } : current);
    try {
      await apiRequest(
        "/attempts/" + exam.attempt.id + "/answers/" + questionId,
        token,
        {
          method: "PUT",
          body: JSON.stringify({ selected_option_id: optionId }),
        },
      );
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "ذخیرهٔ پاسخ ناموفق بود.");
    }
  }

  async function submitAssessment() {
    if (!token || !exam) return;
    setBusyAction(true);
    try {
      const result = await apiRequest<Attempt>(
        "/attempts/" + exam.attempt.id + "/submit",
        token,
        { method: "POST" },
      );
      setLastResult({
        title: exam.assessment.title,
        score: result.score_percent || 0,
        correct: result.correct_count || 0,
        total: result.question_count,
      });
      setExam(null);
      setActiveNav("overview");
      notify("success", "آزمون با موفقیت ارسال و تصحیح شد.");
    } catch (caught) {
      notify("error", caught instanceof Error ? caught.message : "ارسال آزمون ناموفق بود.");
    } finally {
      setBusyAction(false);
    }
  }

  if (authLoading || !user) {
    return <main className="loading-screen"><span className="loading-mark">ن</span><p>در حال آماده‌سازی فضای یادگیری…</p></main>;
  }

  const pageTitle = exam ? "آزمون در حال انجام" : currentNav.title;
  const pageSubtitle = exam
    ? "پاسخ‌های شما به‌صورت جداگانه ذخیره می‌شوند."
    : selectedCourse
      ? selectedCourse.title + (selectedCourse.term ? " · " + selectedCourse.term : "")
      : "از اینجا مسیر یادگیری خود را پیگیری کنید.";

  function renderOverview() {
    if (!courses.length) {
      return (
        <EmptyState
          title={canManage ? "هنوز درسی ایجاد نشده است" : "هنوز عضو درسی نیستید"}
          description={canManage ? "اولین درس آزمایشی را بسازید و مباحث آن را اضافه کنید." : "با کد عضویتی که مدرس در اختیارتان گذاشته است به یک درس بپیوندید."}
          action={<button className="button button-primary" onClick={() => setModal(canManage ? "course" : "join")}>{canManage ? "ایجاد اولین درس" : "ورود با کد درس"}</button>}
        />
      );
    }
    if (!selectedCourse) {
      return <EmptyState title="یک درس انتخاب کنید" description="برای مشاهدهٔ آزمون‌ها و بازخوردها، درس موردنظر را انتخاب کنید." />;
    }
    if (canManage) {
      return (
        <>
          {lastResult && (
            <div className="result-banner">
              <span className="result-check">✓</span>
              <div><strong>نتیجهٔ آخرین آزمون: {lastResult.title}</strong><p>{countText(lastResult.correct)} پاسخ صحیح از {countText(lastResult.total)} سؤال ثبت شد.</p></div>
              <strong className="result-score">{scoreText(lastResult.score)}</strong>
            </div>
          )}
          <div className="metric-grid">
            <MetricCard label="دانشجویان عضو" value={countText(overview?.enrolled_students)} note="عضویت‌های فعال این درس" icon="♙" tone="jade" />
            <MetricCard label="آزمون‌های منتشرشده" value={countText(overview?.published_assessments)} note="قابل مشاهده یا بسته‌شده" icon="☷" tone="gold" />
            <MetricCard label="میانگین نمره" value={scoreText(overview?.average_score_percent)} note="از آزمون‌های ارسال‌شده" icon="⌁" tone="blue" />
            <MetricCard label="مباحث این درس" value={countText(topics.length)} note="موضوع‌های سازمان‌دهی‌شده" icon="◉" tone="plum" />
          </div>
          <div className="dashboard-columns">
            <section className="surface-card">
              <div className="card-heading"><div><span className="mini-label">داده‌های کلاس</span><h3>مباحث نیازمند مرور</h3></div><button className="text-button" onClick={() => setActiveNav("analytics")}>مشاهدهٔ گزارش <span aria-hidden="true">←</span></button></div>
              {topicAnalytics.some((item) => item.needs_review) ? (
                <div className="review-list">
                  {topicAnalytics.filter((item) => item.needs_review).slice(0, 4).map((item) => (
                    <div className="review-item" key={item.topic_id}><span className="review-dot" /><div className="review-details"><strong>{item.topic_title}</strong><small>{countText(item.question_presentations)} بار سؤال ارائه شده</small></div><strong className="review-rate">{scoreText(item.accuracy_percent)}</strong></div>
                  ))}
                </div>
              ) : (
                <EmptyInline text={topicAnalytics.length ? "در حال حاضر مبحثی با دادهٔ کافی برای هشدار وجود ندارد." : "هنوز داده‌ای از آزمون‌های ارسال‌شده برای تحلیل وجود ندارد."} />
              )}
            </section>
            <section className="surface-card">
              <div className="card-heading"><div><span className="mini-label">گام بعدی</span><h3>ادامهٔ ساخت درس</h3></div></div>
              <div className="next-step-list">
                <button className="next-step" onClick={() => setActiveNav("topics")}><span className="step-icon">01</span><span><strong>سازمان‌دهی مباحث</strong><small>{countText(topics.length)} مبحث ثبت‌شده</small></span><b aria-hidden="true">←</b></button>
                <button className="next-step" onClick={() => setActiveNav("questions")}><span className="step-icon">02</span><span><strong>تکمیل بانک سؤال</strong><small>{countText(publishedQuestions.length)} سؤال منتشرشده</small></span><b aria-hidden="true">←</b></button>
                <button className="next-step" onClick={() => setActiveNav("assessments")}><span className="step-icon">03</span><span><strong>ساخت آزمون</strong><small>{countText(assessments.length)} آزمون ساخته‌شده</small></span><b aria-hidden="true">←</b></button>
              </div>
            </section>
          </div>
          <section className="surface-card course-summary-card">
            <div className="card-heading"><div><span className="mini-label">درس انتخاب‌شده</span><h3>{selectedCourse.title}</h3></div><span className={selectedCourse.is_active ? "badge badge-green" : "badge badge-gray"}>{selectedCourse.is_active ? "فعال" : "غیرفعال"}</span></div>
            <p className="muted-copy">{selectedCourse.description || "برای این درس توضیحی ثبت نشده است."}</p>
            <div className="course-summary-footer"><span>{selectedCourse.term || "بدون نیم‌سال مشخص"}</span><button className="button button-secondary" onClick={() => setActiveNav("courses")}>مدیریت درس</button></div>
          </section>
        </>
      );
    }
    return (
      <>
        {lastResult && (
          <div className="result-banner">
            <span className="result-check">✓</span>
            <div><strong>نتیجهٔ آخرین آزمون: {lastResult.title}</strong><p>{countText(lastResult.correct)} پاسخ صحیح از {countText(lastResult.total)} سؤال ثبت شد.</p></div>
            <strong className="result-score">{scoreText(lastResult.score)}</strong>
          </div>
        )}
        <div className="metric-grid metric-grid-student">
          <MetricCard label="درس‌های من" value={countText(courses.length)} note="درس‌های عضو‌شده" icon="▤" />
          <MetricCard label="آزمون‌های قابل انجام" value={countText(assessments.filter((item) => item.status === "published").length)} note="در درس انتخاب‌شده" icon="☷" tone="gold" />
          <MetricCard label="مباحث درس" value={countText(topics.length)} note="برای مرور و تمرین" icon="◉" tone="blue" />
        </div>
        <section className="surface-card">
          <div className="card-heading"><div><span className="mini-label">برای ادامهٔ یادگیری</span><h3>آزمون‌های منتشرشده</h3></div><button className="text-button" onClick={() => setActiveNav("assessments")}>همهٔ آزمون‌ها <span aria-hidden="true">←</span></button></div>
          {assessments.filter((item) => item.status === "published").length ? (
            <div className="assessment-list">
              {assessments.filter((item) => item.status === "published").slice(0, 3).map((item) => (
                <AssessmentRow key={item.id} assessment={item} student onStart={() => startAssessment(item)} busy={busyAction} />
              ))}
            </div>
          ) : (
            <EmptyInline text="در این درس هنوز آزمون منتشرشده‌ای وجود ندارد. با انتشار آزمون توسط مدرس، این بخش به‌روز می‌شود." />
          )}
        </section>
        <section className="surface-card">
          <div className="card-heading"><div><span className="mini-label">ساختار درس</span><h3>مباحث آموزشی</h3></div><span className="count-badge">{countText(topics.length)} مبحث</span></div>
          {topics.length ? <div className="topic-chip-list">{topics.map((topic) => <div className="topic-chip" key={topic.id}><span className="topic-chip-dot" /><span><strong>{topic.title}</strong>{topic.description && <small>{topic.description}</small>}</span></div>)}</div> : <EmptyInline text="مباحث درس هنوز ثبت نشده‌اند." />}
        </section>
      </>
    );
  }

  function renderCourses() {
    return (
      <>
        <div className="content-toolbar">
          <div><span className="mini-label">{canManage ? "مدیریت تدریس" : "فضای دانشجویی"}</span><p className="muted-copy">{canManage ? "درس‌ها را انتخاب کنید یا یک درس آزمایشی جدید بسازید." : "درس‌های عضو‌شده را باز کنید یا با کد عضویت وارد یک درس شوید."}</p></div>
          <button className="button button-primary" onClick={() => setModal(canManage ? "course" : "join")}><span aria-hidden="true">＋</span>{canManage ? "ایجاد درس" : "ورود با کد درس"}</button>
        </div>
        {courses.length ? (
          <div className="course-grid">
            {courses.map((course, index) => (
              <button className={"course-card" + (course.id === courseId ? " course-card-selected" : "")} key={course.id} onClick={() => { setCourseId(course.id); setActiveNav("overview"); }}>
                <div className={"course-cover course-cover-" + (index % 4)}><span className="course-monogram">{course.title.slice(0, 1)}</span><span className="course-cover-label">{course.term || "درس دانشگاهی"}</span></div>
                <div className="course-card-body"><div className="course-card-title"><h3>{course.title}</h3><span className={course.is_active ? "status-dot status-dot-on" : "status-dot"} /></div><p>{course.description || "توضیحی برای این درس ثبت نشده است."}</p><div className="course-card-footer"><span>{canManage ? "مدرس درس" : "عضو درس"}</span><span className="course-open-link">باز کردن <b aria-hidden="true">←</b></span></div></div>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState title={canManage ? "اولین درس را ایجاد کنید" : "هنوز درسی ندارید"} description={canManage ? "پس از ایجاد درس، مباحث و سؤال‌ها را اضافه کرده و آزمون بسازید." : "کد عضویت را از مدرس بگیرید تا به درس اضافه شوید."} action={<button className="button button-primary" onClick={() => setModal(canManage ? "course" : "join")}>{canManage ? "ایجاد درس" : "ورود با کد"}</button>} />
        )}
      </>
    );
  }

  function renderTopics() {
    return (
      <>
        <div className="content-toolbar">
          <div><span className="mini-label">ساختار یادگیری</span><p className="muted-copy">مباحث، مرزهای تحلیل عملکرد دانشجویان هستند.</p></div>
          {canManage && <button className="button button-primary" onClick={() => setModal("topic")} disabled={!courseId}><span aria-hidden="true">＋</span>افزودن مبحث</button>}
        </div>
        {topics.length ? (
          <div className="topic-grid">
            {topics.map((topic, index) => (
              <article className="topic-card" key={topic.id}><span className="topic-order">{countText(index + 1).padStart(2, "۰")}</span><div className="topic-card-main"><h3>{topic.title}</h3><p>{topic.description || "برای این مبحث توضیحی ثبت نشده است."}</p></div><span className="topic-arrow" aria-hidden="true">↙</span></article>
            ))}
          </div>
        ) : <EmptyState title="مبحثی تعریف نشده است" description={canManage ? "اولین مبحث را اضافه کنید تا بتوانید سؤال‌ها را به آن متصل کنید." : "مدرس هنوز مباحث این درس را ثبت نکرده است."} action={canManage ? <button className="button button-primary" onClick={() => setModal("topic")}>افزودن مبحث</button> : undefined} />}
      </>
    );
  }

  function renderQuestions() {
    return (
      <>
        <div className="content-toolbar content-toolbar-wrap">
          <div><span className="mini-label">بانک محتوای درس</span><p className="muted-copy">سؤال‌ها به مبحث متصل‌اند و از همین‌جا وارد آزمون می‌شوند.</p></div>
          <button className="button button-primary" onClick={() => { setQuestionTopicId(topics.length ? String(topics[0].id) : ""); setModal("question"); }} disabled={!courseId || !topics.length}><span aria-hidden="true">＋</span>ساخت سؤال</button>
        </div>
        <div className="table-toolbar"><div className="search-box"><span aria-hidden="true">⌕</span><input aria-label="جست‌وجوی سؤال" placeholder="جست‌وجو در متن سؤال…" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} /></div><span className="count-badge">{countText(questions.length)} سؤال</span></div>
        {filteredQuestions.length ? (
          <div className="question-list">
            {filteredQuestions.map((question) => {
              const topic = topics.find((item) => item.id === question.topic_id);
              return <article className="question-card" key={question.id}>
                <div className="question-card-top"><span className="question-topic">{topic?.title || "بدون مبحث"}</span><div className="badge-group"><span className="badge badge-gray">{statusText(question.difficulty)}</span><span className={question.status === "published" ? "badge badge-green" : "badge badge-gray"}>{statusText(question.status)}</span></div></div>
                <h3>{question.prompt}</h3>
                <div className="question-options-preview">{question.options.map((option) => <span className={option.is_correct ? "answer-option answer-option-correct" : "answer-option"} key={option.id}><span className="answer-radio">{option.is_correct ? "✓" : ""}</span>{option.text}</span>)}</div>
              </article>;
            })}
          </div>
        ) : (
          <EmptyState title={questions.length ? "سؤالی با این عبارت پیدا نشد" : "بانک سؤال خالی است"} description={questions.length ? "عبارت دیگری را جست‌وجو کنید." : (topics.length ? "اولین سؤال را ایجاد کنید. برای ساخت آزمون باید سؤال منتشرشده داشته باشید." : "ابتدا یک مبحث بسازید و بعد سؤال‌ها را به آن متصل کنید.")} action={canManage && topics.length ? <button className="button button-primary" onClick={() => setModal("question")}>ساخت اولین سؤال</button> : undefined} />
        )}
      </>
    );
  }

  function renderAssessments() {
    if (exam) return renderExam();
    return (
      <>
        {canManage && <div className="content-toolbar"><div><span className="mini-label">ارزیابی هدفمند</span><p className="muted-copy">از سؤال‌های منتشرشده درس آزمون بسازید و پس از بازبینی منتشر کنید.</p></div><button className="button button-primary" onClick={() => setModal("assessment")} disabled={!publishedQuestions.length}><span aria-hidden="true">＋</span>ساخت آزمون</button></div>}
        {lastResult && !canManage && <div className="result-banner"><span className="result-check">✓</span><div><strong>آخرین نتیجه: {lastResult.title}</strong><p>{countText(lastResult.correct)} پاسخ صحیح از {countText(lastResult.total)} سؤال</p></div><strong className="result-score">{scoreText(lastResult.score)}</strong></div>}
        {assessments.length ? <div className="assessment-list">{assessments.map((assessment) => <AssessmentRow key={assessment.id} assessment={assessment} student={!canManage} onStart={() => startAssessment(assessment)} onPublish={() => publishAssessment(assessment)} busy={busyAction} />)}</div> : <EmptyState title="آزمونی ثبت نشده است" description={canManage ? "با انتخاب سؤال‌های منتشرشده اولین آزمون را بسازید." : "پس از انتشار آزمون توسط مدرس، اینجا نمایش داده می‌شود."} action={canManage && publishedQuestions.length ? <button className="button button-primary" onClick={() => setModal("assessment")}>ساخت آزمون</button> : undefined} />}
      </>
    );
  }

  function renderExam() {
    if (!exam) return null;
    return (
      <div className="exam-layout">
        <div className="exam-intro surface-card"><div><span className="mini-label">آزمون فعال</span><h2>{exam.assessment.title}</h2><p>{exam.assessment.instructions || "به سؤال‌ها پاسخ دهید؛ پاسخ انتخابی هر سؤال در سامانه ذخیره می‌شود."}</p></div><div className="exam-meta"><span>◷ {exam.assessment.duration_minutes ? countText(exam.assessment.duration_minutes) + " دقیقه" : "بدون محدودیت زمانی"}</span><span>▦ {countText(exam.assessment.questions.length)} سؤال</span></div></div>
        <div className="exam-progress-card"><div><span>پاسخ‌های ثبت‌شده</span><strong>{countText(Object.keys(exam.answers).length)} از {countText(exam.assessment.questions.length)}</strong></div><div className="progress-track"><span style={{ width: Math.min(100, (Object.keys(exam.answers).length / Math.max(1, exam.assessment.questions.length)) * 100) + "%" }} /></div></div>
        {exam.assessment.questions.map((question, index) => (
          <article className="exam-question surface-card" key={question.id}>
            <div className="exam-question-label"><span>سؤال {countText(index + 1)}</span><span>{countText(question.options.length)} گزینه</span></div>
            <h3>{question.prompt}</h3>
            <div className="exam-option-list">
              {question.options.map((option, optionIndex) => (
                <label className={"exam-option" + (exam.answers[String(question.id)] === option.id ? " exam-option-selected" : "")} key={option.id}>
                  <input type="radio" name={"question-" + question.id} checked={exam.answers[String(question.id)] === option.id} onChange={() => saveAnswer(question.id, option.id)} />
                  <span className="exam-option-letter">{String.fromCharCode(65 + optionIndex)}</span><span>{option.text}</span>
                </label>
              ))}
            </div>
          </article>
        ))}
        <div className="exam-submit-bar"><span>پس از ارسال نهایی، پاسخ‌ها دیگر قابل تغییر نیستند.</span><button className="button button-primary" disabled={busyAction} onClick={() => { if (window.confirm("آزمون ارسال شود؟ پس از ارسال امکان تغییر پاسخ‌ها نیست.")) void submitAssessment(); }}>{busyAction ? "در حال ارسال…" : "ارسال نهایی آزمون"}</button></div>
      </div>
    );
  }

  function renderAnalytics() {
    return (
      <>
        <div className="metric-grid">
          <MetricCard label="دانشجویان عضو" value={countText(overview?.enrolled_students)} note="افراد ثبت‌نام‌شده در درس" icon="♙" />
          <MetricCard label="آزمون‌های قابل گزارش" value={countText(overview?.published_assessments)} note="منتشرشده یا بسته‌شده" icon="☷" tone="gold" />
          <MetricCard label="ارسال‌های نهایی" value={countText(overview?.submitted_attempts)} note="تلاش‌های تصحیح‌شده" icon="✓" tone="blue" />
          <MetricCard label="میانگین نمره" value={scoreText(overview?.average_score_percent)} note="میانگین تمام تلاش‌های ارسال‌شده" icon="⌁" tone="plum" />
        </div>
        <section className="surface-card">
          <div className="card-heading"><div><span className="mini-label">عملکرد مبحثی</span><h3>کدام مباحث سخت‌تر بوده‌اند؟</h3><p>درصد پاسخ صحیح به‌ازای سؤال‌های ارائه‌شده در آزمون‌های ارسال‌شده</p></div></div>
          {topicAnalytics.length ? <div className="topic-analytics-list">{topicAnalytics.map((item) => <div className="topic-analytics-row" key={item.topic_id}>
            <div className="topic-analytics-meta"><div><strong>{item.topic_title}</strong><small>{countText(item.correct_responses)} پاسخ صحیح از {countText(item.question_presentations)} بار ارائهٔ سؤال</small></div><div className="topic-analytics-right">{item.needs_review && <span className="badge badge-amber">نیازمند مرور</span>}<strong>{scoreText(item.accuracy_percent)}</strong></div></div>
            <div className="analytics-bar"><span className={item.needs_review ? "analytics-bar-low" : ""} style={{ width: (item.accuracy_percent === null ? 0 : Math.max(0, Math.min(100, item.accuracy_percent))) + "%" }} /></div>
          </div>)}</div> : <EmptyInline text="برای تحلیل مبحثی، ابتدا آزمون منتشر کنید و منتظر ثبت نتایج دانشجویان بمانید." />}
          <p className="analytics-footnote">هشدار مرور یک قاعدهٔ راهنماست: حداقل سه بار ارائهٔ سؤال و دقت کمتر از ۶۰٪. این شاخص تشخیص قطعی یادگیری نیست.</p>
        </section>
        <section className="surface-card">
          <div className="card-heading"><div><span className="mini-label">عملکرد کلی</span><h3>دامنهٔ نمره‌ها</h3></div></div>
          <div className="score-range"><div><span>بالاترین نمره</span><strong>{scoreText(overview?.best_score_percent)}</strong></div><div><span>میانگین</span><strong>{scoreText(overview?.average_score_percent)}</strong></div><div><span>پایین‌ترین نمره</span><strong>{scoreText(overview?.lowest_score_percent)}</strong></div></div>
        </section>
      </>
    );
  }

  function renderStudents() {
    return (
      <section className="surface-card">
        <div className="card-heading"><div><span className="mini-label">گروه درس</span><h3>عملکرد دانشجویان</h3><p>فقط تلاش‌های ارسال‌شده در محاسبهٔ نمره‌ها منظور می‌شوند.</p></div><span className="count-badge">{countText(roster.length)} عضو</span></div>
        {studentSummaries.length ? <div className="table-scroll"><table className="data-table"><thead><tr><th>دانشجو</th><th>آزمون‌های ارسال‌شده</th><th>میانگین نمره</th><th>بهترین نمره</th><th>آخرین ارسال</th></tr></thead><tbody>{studentSummaries.map((student) => <tr key={student.student_id}><td><div className="student-cell"><span className="avatar">{student.full_name.slice(0, 1)}</span><div><strong>{student.full_name}</strong><small>{student.email}</small></div></div></td><td>{countText(student.submitted_attempts)}</td><td><strong>{scoreText(student.average_score_percent)}</strong></td><td>{scoreText(student.best_score_percent)}</td><td>{dateText(student.last_submitted_at)}</td></tr>)}</tbody></table></div> : <EmptyInline text="هنوز دانشجویی در این درس ثبت‌نام نکرده یا نتیجه‌ای ارسال نشده است." />}
      </section>
    );
  }

  return (
    <main className="dashboard-shell">
      <aside className="app-sidebar">
        <div className="sidebar-brand"><span className="brand-mark">ن</span><span><strong>نبض یادگیری</strong><small>فضای کار آموزشی</small></span></div>
        <div className="sidebar-profile"><div className="profile-avatar">{user.full_name.slice(0, 1)}</div><div className="profile-info"><strong>{user.full_name}</strong><small>{canManage ? "مدرس" : "دانشجو"}</small></div><span className="online-dot" aria-label="حساب فعال" /></div>
        <div className="sidebar-section-label">فضای کاری</div>
        <nav className="sidebar-nav" aria-label="ناوبری اصلی">
          {navItems.map((item) => <button key={item.key} className={"nav-link" + (activeNav === item.key ? " nav-link-active" : "")} onClick={() => { setActiveNav(item.key); if (exam && item.key !== "assessments") setFlash({ kind: "info", text: "آزمون فعال را می‌توانید از بخش آزمون‌ها ادامه دهید." }); }}><span className="nav-link-icon" aria-hidden="true">{item.icon}</span><span>{item.title}</span>{item.key === "analytics" && topicAnalytics.some((topic) => topic.needs_review) && <span className="nav-indicator" />}</button>)}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-help"><span className="help-icon">i</span><div><strong>نسخهٔ آزمایشی</strong><small>برای دادهٔ واقعی هنوز نیاز به بازبینی امنیتی دارد.</small></div></div>
          <button className="logout-button" onClick={signOut}><span aria-hidden="true">↪</span> خروج از حساب</button>
        </div>
      </aside>

      <section className="dashboard-main">
        <header className="dashboard-topbar">
          <div className="breadcrumb"><span>فضای کاری</span><b aria-hidden="true">/</b><strong>{pageTitle}</strong></div>
          <div className="topbar-actions">
            <label className="course-switcher"><span>درس فعال</span><select aria-label="انتخاب درس فعال" value={courseId ?? ""} onChange={(event) => setCourseId(event.target.value ? Number(event.target.value) : null)} disabled={!courses.length}>{courses.length ? courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>) : <option value="">بدون درس</option>}</select></label>
            <div className="topbar-avatar" title={user.full_name}>{user.full_name.slice(0, 1)}</div>
          </div>
        </header>

        <div className="dashboard-content">
          <div className="page-intro"><div><span className="mini-label">{canManage ? "پنل مدرس" : "پنل دانشجو"} / نسخهٔ آزمایشی</span><h1>{exam ? exam.assessment.title : currentNav.title}</h1><p>{pageSubtitle}</p></div>{!exam && <div className="page-intro-actions">{canManage && <button className="button button-secondary" onClick={() => setActiveNav("analytics")}>گزارش یادگیری <span aria-hidden="true">↗</span></button>}{!canManage && <button className="button button-primary" onClick={() => setModal("join")}>＋ عضویت در درس</button>}</div>}</div>
          {flash && <div className={"flash-message flash-" + flash.kind} role={flash.kind === "error" ? "alert" : "status"}><span>{flash.kind === "success" ? "✓" : flash.kind === "error" ? "!" : "i"}</span><p>{flash.text}</p><button aria-label="بستن پیام" onClick={() => setFlash(null)}>×</button></div>}
          {workspaceLoading && <div className="loading-strip"><span /> در حال دریافت درس‌ها…</div>}
          {contentLoading && <div className="loading-strip"><span /> در حال همگام‌سازی اطلاعات درس…</div>}

          {activeNav === "overview" && renderOverview()}
          {activeNav === "courses" && renderCourses()}
          {activeNav === "topics" && renderTopics()}
          {activeNav === "questions" && canManage && renderQuestions()}
          {activeNav === "assessments" && renderAssessments()}
          {activeNav === "analytics" && canManage && renderAnalytics()}
          {activeNav === "students" && canManage && renderStudents()}

          <footer className="dashboard-footer"><span>نبض یادگیری <b>·</b> نسخهٔ زیرساختی</span><span>داده‌ها از سرور درس انتخاب‌شده دریافت می‌شوند.</span></footer>
        </div>
      </section>

      {modal && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setModal(null); }}>
        <section className="dialog-card" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
          <div className="dialog-heading"><div><span className="mini-label">نبض یادگیری</span><h2 id="dialog-title">{modal === "course" ? "ایجاد درس جدید" : modal === "join" ? "عضویت در درس" : modal === "topic" ? "افزودن مبحث" : modal === "question" ? "ساخت سؤال" : "ساخت آزمون"}</h2><p>{modal === "course" ? "اطلاعات پایهٔ درس را وارد کنید." : modal === "join" ? "کد عضویت را از مدرس بگیرید." : modal === "topic" ? "مبحث‌ها برای دسته‌بندی سؤال‌ها و تحلیل نتایج استفاده می‌شوند." : modal === "question" ? "سؤال جدید با دو گزینه ساخته و منتشر می‌شود." : "از سؤال‌های منتشرشدهٔ این درس انتخاب کنید."}</p></div><button className="icon-button" onClick={() => setModal(null)} aria-label="بستن پنجره">×</button></div>
          {modal === "course" && <form className="dialog-form" onSubmit={createCourse}>
            <label className="field-label" htmlFor="course-title">عنوان درس</label><input id="course-title" className="text-input" value={courseTitle} onChange={(event) => setCourseTitle(event.target.value)} minLength={2} maxLength={160} required placeholder="مثلاً شبکه‌های کامپیوتری" />
            <label className="field-label" htmlFor="course-term">نیم‌سال / دوره <span>اختیاری</span></label><input id="course-term" className="text-input" value={courseTerm} onChange={(event) => setCourseTerm(event.target.value)} maxLength={80} placeholder="مثلاً پاییز ۱۴۰۵" />
            <label className="field-label" htmlFor="course-description">توضیحات <span>اختیاری</span></label><textarea id="course-description" className="text-input text-area" value={courseDescription} onChange={(event) => setCourseDescription(event.target.value)} maxLength={4000} placeholder="توضیح کوتاه دربارهٔ درس…" />
            <div className="dialog-actions"><button className="button button-secondary" type="button" onClick={() => setModal(null)}>انصراف</button><button className="button button-primary" type="submit" disabled={busyAction}>{busyAction ? "در حال ساخت…" : "ایجاد درس"}</button></div>
          </form>}
          {modal === "join" && <form className="dialog-form" onSubmit={joinCourse}>
            <label className="field-label" htmlFor="join-code">کد عضویت درس</label><input id="join-code" className="text-input code-input" value={joinCode} onChange={(event) => setJoinCode(event.target.value.toUpperCase())} maxLength={16} minLength={6} required placeholder="مثلاً A1B2C3D4" autoCapitalize="characters" />
            <p className="form-hint">کد عضویت را دقیقاً از مدرس همان درس دریافت کنید.</p>
            <div className="dialog-actions"><button className="button button-secondary" type="button" onClick={() => setModal(null)}>انصراف</button><button className="button button-primary" type="submit" disabled={busyAction}>{busyAction ? "در حال عضویت…" : "عضویت در درس"}</button></div>
          </form>}
          {modal === "topic" && <form className="dialog-form" onSubmit={createTopic}>
            <label className="field-label" htmlFor="topic-title">نام مبحث</label><input id="topic-title" className="text-input" value={topicTitle} onChange={(event) => setTopicTitle(event.target.value)} minLength={2} maxLength={120} required placeholder="مثلاً مسیریابی" />
            <label className="field-label" htmlFor="topic-description">توضیح مبحث <span>اختیاری</span></label><textarea id="topic-description" className="text-input text-area" value={topicDescription} onChange={(event) => setTopicDescription(event.target.value)} maxLength={2000} placeholder="مباحث کلیدی این بخش…" />
            <div className="dialog-actions"><button className="button button-secondary" type="button" onClick={() => setModal(null)}>انصراف</button><button className="button button-primary" type="submit" disabled={busyAction}>{busyAction ? "در حال ذخیره…" : "ذخیرهٔ مبحث"}</button></div>
          </form>}
          {modal === "question" && <form className="dialog-form" onSubmit={createQuestion}>
            {!topics.length ? <div className="form-alert form-alert-error">ابتدا یک مبحث بسازید.</div> : <>
              <label className="field-label" htmlFor="question-topic">مبحث</label><select id="question-topic" className="text-input" value={questionTopicId} onChange={(event) => setQuestionTopicId(event.target.value)} required>{topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.title}</option>)}</select>
              <label className="field-label" htmlFor="question-prompt">متن سؤال</label><textarea id="question-prompt" className="text-input text-area" value={questionPrompt} onChange={(event) => setQuestionPrompt(event.target.value)} minLength={5} maxLength={10000} required placeholder="صورت سؤال را واضح و مشخص بنویسید…" />
              <label className="field-label" htmlFor="option-one">گزینهٔ اول</label><input id="option-one" className="text-input" value={optionOne} onChange={(event) => setOptionOne(event.target.value)} maxLength={500} required placeholder="متن گزینهٔ اول" />
              <label className="field-label" htmlFor="option-two">گزینهٔ دوم</label><input id="option-two" className="text-input" value={optionTwo} onChange={(event) => setOptionTwo(event.target.value)} maxLength={500} required placeholder="متن گزینهٔ دوم" />
              <div className="correct-choice-field"><span className="field-label">پاسخ صحیح</span><label><input type="radio" checked={correctOption === "0"} onChange={() => setCorrectOption("0")} /> گزینهٔ اول</label><label><input type="radio" checked={correctOption === "1"} onChange={() => setCorrectOption("1")} /> گزینهٔ دوم</label></div>
              <label className="field-label" htmlFor="question-difficulty">سطح دشواری</label><select id="question-difficulty" className="text-input" value={questionDifficulty} onChange={(event) => setQuestionDifficulty(event.target.value)}><option value="easy">آسان</option><option value="medium">متوسط</option><option value="hard">دشوار</option></select>
              <label className="field-label" htmlFor="question-explanation">توضیح پاسخ <span>اختیاری</span></label><textarea id="question-explanation" className="text-input text-area" value={questionExplanation} onChange={(event) => setQuestionExplanation(event.target.value)} maxLength={5000} placeholder="توضیح علمی برای مدرس…" />
            </>}
            <div className="dialog-actions"><button className="button button-secondary" type="button" onClick={() => setModal(null)}>انصراف</button><button className="button button-primary" type="submit" disabled={busyAction || !topics.length}>{busyAction ? "در حال ذخیره…" : "انتشار سؤال"}</button></div>
          </form>}
          {modal === "assessment" && <form className="dialog-form" onSubmit={createAssessment}>
            <label className="field-label" htmlFor="assessment-title">عنوان آزمون</label><input id="assessment-title" className="text-input" value={assessmentTitle} onChange={(event) => setAssessmentTitle(event.target.value)} minLength={2} maxLength={180} required placeholder="مثلاً آزمون هفتهٔ اول" />
            <label className="field-label" htmlFor="assessment-instructions">راهنما <span>اختیاری</span></label><textarea id="assessment-instructions" className="text-input text-area" value={assessmentInstructions} onChange={(event) => setAssessmentInstructions(event.target.value)} maxLength={4000} placeholder="راهنمای کوتاه برای دانشجو…" />
            <div className="field-two-column"><div><label className="field-label" htmlFor="assessment-duration">زمان (دقیقه) <span>اختیاری</span></label><input id="assessment-duration" className="text-input" type="number" min={1} max={300} value={assessmentDuration} onChange={(event) => setAssessmentDuration(event.target.value)} placeholder="بدون محدودیت" /></div><div><label className="field-label" htmlFor="assessment-attempts">دفعات مجاز</label><select id="assessment-attempts" className="text-input" value={assessmentAttempts} onChange={(event) => setAssessmentAttempts(event.target.value)}><option value="1">۱ بار</option><option value="2">۲ بار</option><option value="3">۳ بار</option></select></div></div>
            <div className="field-label">انتخاب سؤال‌ها <span>{countText(publishedQuestions.length)} سؤال منتشرشده</span></div>
            <div className="question-select-list">{publishedQuestions.map((question) => <label className="question-select-item" key={question.id}><input type="checkbox" checked={assessmentQuestionIds.includes(question.id)} onChange={(event) => setAssessmentQuestionIds((current) => event.target.checked ? [...current, question.id] : current.filter((id) => id !== question.id))} /><span><strong>{question.prompt}</strong><small>{topics.find((topic) => topic.id === question.topic_id)?.title || "بدون مبحث"}</small></span></label>)}</div>
            {!publishedQuestions.length && <p className="form-hint">برای ساخت آزمون ابتدا سؤال منتشرشده اضافه کنید.</p>}
            <div className="dialog-actions"><button className="button button-secondary" type="button" onClick={() => setModal(null)}>انصراف</button><button className="button button-primary" type="submit" disabled={busyAction || !publishedQuestions.length}>{busyAction ? "در حال ساخت…" : "ساخت پیش‌نویس آزمون"}</button></div>
          </form>}
        </section>
      </div>}
    </main>
  );
}

function EmptyInline({ text }: { text: string }) {
  return <div className="empty-inline"><span aria-hidden="true">◌</span><p>{text}</p></div>;
}

function AssessmentRow({
  assessment,
  student,
  onStart,
  onPublish,
  busy,
}: {
  assessment: Assessment;
  student?: boolean;
  onStart: () => void;
  onPublish?: () => void;
  busy: boolean;
}) {
  return (
    <article className="assessment-row">
      <div className="assessment-badge" aria-hidden="true">☷</div>
      <div className="assessment-main"><div className="assessment-title-line"><h3>{assessment.title}</h3><span className={assessment.status === "published" ? "badge badge-green" : assessment.status === "closed" ? "badge badge-gray" : "badge badge-amber"}>{statusText(assessment.status)}</span></div><p>{assessment.instructions || "بدون توضیحات اضافی"}</p><div className="assessment-meta"><span>▦ {countText(assessment.question_count)} سؤال</span><span>◷ {assessment.duration_minutes ? countText(assessment.duration_minutes) + " دقیقه" : "بدون محدودیت زمانی"}</span>{!student && <span>↻ {countText(assessment.max_attempts)} بار مجاز</span>}</div></div>
      <div className="assessment-actions">
        {student && assessment.status === "published" && <button className="button button-primary" onClick={onStart} disabled={busy}>شروع آزمون <span aria-hidden="true">←</span></button>}
        {!student && assessment.status === "draft" && <button className="button button-secondary" onClick={onPublish} disabled={busy}>انتشار آزمون</button>}
      </div>
    </article>
  );
}
