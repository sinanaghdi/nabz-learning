"use client";

import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";

import { apiRequest } from "../../lib/api";

type TokenResponse = { access_token: string; token_type: string };

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiRequest("/auth/register", undefined, {
        method: "POST",
        body: JSON.stringify({ full_name: name, email, password }),
      });
      const result = await apiRequest<TokenResponse>("/auth/login", undefined, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem("nabz_access_token", result.access_token);
      router.replace("/dashboard");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "ثبت‌نام انجام نشد.");
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
      <section className="auth-grid auth-grid-register">
        <div className="auth-story">
          <span className="eyebrow">شروع یادگیری هدفمند</span>
          <h1>هر تمرین، یک قدم به شناخت بهتر.</h1>
          <p>حساب دانشجویی بساز، با کد درس وارد کلاس شو و آزمون‌های منتشرشده را انجام بده.</p>
          <div className="auth-story-note"><span className="story-dot" /> ثبت‌نام عمومی فقط حساب دانشجو می‌سازد</div>
        </div>
        <form className="auth-card" onSubmit={handleSubmit}>
          <div className="auth-card-heading">
            <span className="mini-label">عضویت دانشجو</span>
            <h2>ساخت حساب</h2>
            <p>اطلاعات پایه را برای ساخت حساب وارد کنید.</p>
          </div>
          <label className="field-label" htmlFor="name">نام و نام خانوادگی</label>
          <input id="name" className="text-input" autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="نام کامل" minLength={2} maxLength={120} required />
          <label className="field-label" htmlFor="email">ایمیل</label>
          <input id="email" className="text-input" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="name@university.edu" required />
          <label className="field-label" htmlFor="password">رمز عبور</label>
          <input id="password" className="text-input" type="password" autoComplete="new-password" minLength={10} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="حداقل ۱۰ نویسه" required />
          {error && <div className="form-alert form-alert-error" role="alert">{error}</div>}
          <button className="button button-primary button-wide" type="submit" disabled={busy}>{busy ? "در حال ساخت حساب..." : "ساخت حساب دانشجویی"}<span aria-hidden="true">←</span></button>
          <p className="auth-switch">قبلاً ثبت‌نام کرده‌اید؟ <Link href="/login">ورود</Link></p>
          <p className="auth-footnote">با ساخت حساب، نقش دانشجو به‌صورت خودکار اختصاص داده می‌شود.</p>
        </form>
      </section>
      <footer className="auth-footer">نبض یادگیری <span>·</span> نسخهٔ آزمایشی</footer>
    </main>
  );
}
