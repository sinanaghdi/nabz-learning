import Link from "next/link";

const steps = [
  { number: "۰۱", title: "تمرین هدفمند", description: "تمرین‌های کوتاه و مرتبط با مباحث یک درس، با تمرکز بر یادگیری واقعی." },
  { number: "۰۲", title: "بازخورد روشن", description: "دانشجو متوجه می‌شود کدام مبحث را بهتر است دوباره مرور کند." },
  { number: "۰۳", title: "دید بهتر برای مدرس", description: "پاسخ‌ها در آینده به مدرس کمک می‌کنند نقاط دشوار کلاس را دقیق‌تر ببیند." },
];

export default function HomePage() {
  return (
    <main className="page-shell">
      <header className="site-header">
        <Link className="brand" href="/" aria-label="نبض یادگیری، صفحه اصلی">
          <span className="brand-mark" aria-hidden="true">ن</span><span>نبض یادگیری</span>
        </Link>
        <span className="header-note">پروژهٔ آزمایشی برای یادگیری بهتر در دانشگاه</span>
      </header>
      <section className="hero" aria-labelledby="hero-title">
        <div>
          <p className="eyebrow">یادگیری، با بازخورد دقیق‌تر</p>
          <h1 id="hero-title">فقط نمره را نبینیم؛ بفهمیم کجا یادگیری سخت شده است.</h1>
          <p className="hero-copy">
            نبض یادگیری در حال شکل‌گیری است؛ بستری برای تمرین‌های کوتاه و کمک به دانشجو
            و مدرس تا مبحث‌هایی را که نیاز به توجه بیشتری دارند، بهتر شناسایی کنند.
          </p>
          <span className="status-pill"><span aria-hidden="true" /> نسخهٔ اولیه · در حال توسعه</span>
        </div>
        <div className="visual-card" aria-label="نمای انتزاعی از بازخورد یادگیری">
          <div className="orbit"><div className="orbit-inner" aria-hidden="true">ن</div></div>
          <div className="visual-caption">تمرین ← بازخورد ← یادگیری هدفمندتر</div>
        </div>
      </section>
      <section className="section" aria-labelledby="steps-title">
        <div className="section-heading">
          <div><h2 id="steps-title">قرار است چه چیزی بهتر شود؟</h2><p>شروع کوچک، با تمرکز روی یک چرخهٔ واقعی یادگیری.</p></div>
        </div>
        <div className="steps">
          {steps.map((step) => (
            <article className="step-card" key={step.number}>
              <span className="step-number">{step.number}</span><h3>{step.title}</h3><p>{step.description}</p>
            </article>
          ))}
        </div>
      </section>
      <footer className="site-footer">
        <span>نبض یادگیری · نسخهٔ زیرساختی</span>
        <span>هنوز برای استفادهٔ واقعی یا نگهداری دادهٔ دانشجویان آماده نیست.</span>
      </footer>
    </main>
  );
}
