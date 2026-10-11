"use client";

import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { apiRequest, type User } from "../../lib/api";

type TokenResponse = { access_token: string; token_type: string };

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await apiRequest<TokenResponse>("/auth/login", undefined, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("nabz_access_token", result.access_token);
      const user = await apiRequest<User>("/auth/me", result.access_token);
      localStorage.setItem("nabz_user", JSON.stringify(user));
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ورود انجام نشد.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-backdrop auth-backdrop-one" aria-hidden="true" />
      <div className="auth-backdrop auth-backdrop-two" aria-hidden="true" />
      <Link className="auth-brand" href="/">
        <span className="brand-mark">ن</span>
        <span><strong>نبض یادگیری</strong><small>یادگیری با بازخورد روشن</small></span>
      </Link>
      <section className="auth-grid">
        <div className="auth-story">
          <span className="eyebrow">محیط یادگیری دانشگاهی</span>
          <h1>یادگیری را از زاویه‌ای دقیق‌تر ببین.</h1>
          <p>با تمرین، نتیجه را ثبت کن و بفهم کدام مبحث به توجه بیشتری نیاز دارد.</p>
          <div className="auth-story-note"><span className="story-dot" /> یک چرخهٔ ساده؛ از تمرین تا بازخورد</div>
        </div>
        <form className="auth-card" onSubmit={handleSubmit}>
          <div className="auth-card-heading">
            <span className="mini-label">خوش آمدید</span>
            <h2>ورود به حساب</h2>
            <p>برای ادامه، اطلاعات حساب خود را وارد کنید.</p>
          </div>
          <label className="field-label" htmlFor="email">ایمیل</label>
          <input id="email" className="text-input" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@university.edu" required />
          <label className="field-label" htmlFor="password">رمز عبور</label>
          <input id="password" className="text-input" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="رمز عبور حساب" required />
          {error && <div className="form-alert form-alert-error" role="alert">{error}</div>}
          <button className="button button-primary button-wide" type="submit" disabled={busy}>{busy ? "در حال ورود..." : "ورود به پنل"}<span aria-hidden="true">←</span></button>
          <p className="auth-switch">حساب ندارید؟ <Link href="/register">ثبت‌نام دانشجو</Link></p>
          <p className="auth-footnote">حساب استاد باید توسط مدیر سامانه ساخته شود.</p>
        </form>
      </section>
      <footer className="auth-footer">نبض یادگیری <span>·</span> نسخهٔ آزمایشی</footer>
    </main>
  );
}
