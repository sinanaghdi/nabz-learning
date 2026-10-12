# نبض یادگیری | Nabz Learning

پلتفرم فارسی برای کمک به مدرس و دانشجو در شناسایی مبحث‌هایی که به تمرین بیشتر نیاز دارند.

## وضعیت پروژه

**فازهای ۱ تا ۷ پیاده‌سازی و فاز ۷ در شاخهٔ اصلی ادغام شده است.** قابلیت‌های اصلی درس، بانک سؤال، آزمون، تحلیل، رابط فارسی RTL و بازیابی تلاش نیمه‌تمام آماده‌اند. رابط فارسی RTL، احراز هویت، درس و مباحث، بانک سؤال، آزمون، تصحیح خودکار، گزارش یادگیری و داشبوردهای نقش‌محور در مخزن وجود دارند.

## دموی تعاملی و انتشار در GitHub Pages

کد دمو در پوشهٔ [`demo/`](demo/) آماده است. این نسخه از داده‌های نمونه استفاده می‌کند و به API یا پایگاه داده متصل نیست.

**آدرس دمو پس از فعال‌سازی Pages:**  
https://sinanaghdi.github.io/nabz-learning/

### راه‌اندازی یک‌بارهٔ GitHub Pages

1. در مخزن GitHub، وارد **Settings → Pages** شوید.
2. در بخش **Build and deployment**، گزینهٔ **Source** را روی **GitHub Actions** بگذارید.
3. به **Actions → Deploy interactive demo to GitHub Pages** بروید و **Run workflow** را از شاخهٔ `main` اجرا کنید.
4. پس از موفق شدن اجرا، لینک بالا دموی زنده را باز می‌کند. تغییرات بعدی `demo/` روی `main` خودکار منتشر می‌شوند.

این تنظیم اولیه باید توسط صاحب مخزن انجام شود؛ توکن خودکار GitHub مجوز مدیریتی لازم برای فعال‌کردن Pages را ندارد. جزئیات در [راهنمای دمو](demo/README.md) آمده است.

## فناوری‌ها

- **Frontend:** Next.js, React, TypeScript و رابط راست‌چین فارسی
- **Backend:** FastAPI، Pydantic و SQLAlchemy 2
- **Database:** PostgreSQL و مهاجرت‌های Alembic
- **Authentication:** هش رمز عبور Argon2 و توکن امضاشدهٔ JWT
- **Local development:** Docker Compose
- **CI:** GitHub Actions برای بررسی بک‌اند و فرانت‌اند

## اجرای محلی

پیش‌نیاز: Docker Desktop با Docker Compose.

1. فایل متغیرهای محیطی را بسازید:
   - PowerShell: `Copy-Item .env.example .env`
   - macOS/Linux: `cp .env.example .env`
2. سرویس‌ها را اجرا کنید: `docker compose up --build`
3. رابط کاربری: http://localhost:3000
4. بررسی سلامت API: http://localhost:8000/api/v1/health
5. مستندات تعاملی API: http://localhost:8000/docs

برای توقف: `docker compose down`. از `docker compose down -v` فقط زمانی استفاده کنید که عمداً قصد حذف داده‌های محلی PostgreSQL را دارید.

## ایجاد حساب مدرس

ثبت‌نام عمومی فقط حساب دانشجو ایجاد می‌کند. از ترمینال مورد اعتماد، پس از اجرای بک‌اند، دستور زیر را اجرا کنید:

```bash
docker compose exec backend python -m app.cli create-privileged-user --role instructor --email instructor@example.edu --full-name "Course Instructor"
```

رمز عبور دو بار به‌صورت تعاملی دریافت می‌شود و در ترمینال نمایش داده نمی‌شود. ایجاد حساب مدرس/مدیر از API عمومی امکان‌پذیر نیست.

## قابلیت‌های اصلی

- ایجاد درس و عضویت دانشجو با کد ورود
- ساخت مباحث درس و بانک سؤال چندگزینه‌ای
- ساخت آزمون از سؤال‌های منتشرشده و انتشار آن
- ذخیرهٔ پاسخ و تصحیح سمت سرور
- بازیابی آزمون نیمه‌تمام و پاسخ‌های ذخیره‌شده
- گزارش عملکرد کلی، عملکرد مبحث‌ها و خلاصهٔ دانشجوها
- رابط فارسی RTL متناسب با نقش مدرس یا دانشجو

## مسیرهای مهم API

تمام مسیرها زیر پیشوند `/api/v1` هستند.

| روش | مسیر | دسترسی |
|---|---|---|
| `POST` | `/auth/register` | عمومی؛ فقط دانشجو |
| `POST` | `/auth/login` | عمومی |
| `GET` | `/auth/me` | کاربر واردشده |
| `POST` | `/courses` | مدرس/مدیر |
| `POST` | `/courses/enroll` | دانشجو با کد عضویت |
| `GET, POST` | `/courses/{id}/topics` | مشاهده با دسترسی درس / مدیریت توسط مدرس |
| `GET, POST` | `/courses/{id}/questions` | مدرس/مدیر |
| `POST` | `/courses/{id}/assessments` | مدرس/مدیر درس |
| `POST` | `/courses/{id}/assessments/{assessment_id}/publish` | مدرس/مدیر درس |
| `GET` | `/courses/{id}/assessments/{assessment_id}/attempts/active` | دانشجو؛ آزمون نیمه‌تمام خود |
| `PUT` | `/attempts/{id}/answers/{question_id}` | مالک آزمون، تا پیش از پایان زمان |
| `POST` | `/attempts/{id}/submit` | مالک آزمون |

دانشجو در payload سؤال‌های آزمون، کلید پاسخ یا توضیح سؤال را دریافت نمی‌کند. شروع مجدد یک آزمون نیمه‌تمام همان تلاش قبلی را برمی‌گرداند تا با تازه‌سازی صفحه، تلاش جدید مصرف نشود.

## اجرای بررسی‌ها

بک‌اند با Python 3.12+:

```bash
cd backend
python -m pip install -e ".[dev]"
ruff check app tests alembic
alembic upgrade head --sql
pytest
```

فرانت‌اند با Node.js 24 یا نسخهٔ سازگار:

```bash
cd frontend
npm install
npm run lint
npm run typecheck
npm run build
```

## محدودیت‌ها و آمادگی پایلوت

این پروژه هنوز برای دادهٔ حساس دانشجویان آمادهٔ استقرار عمومی نیست. پیش از استفاده واقعی باید مدیریت اسرار، HTTPS، محدودسازی تلاش ورود، بازیابی/تأیید حساب، پشتیبان‌گیری و آزمون بازیابی پایگاه داده، سیاست حریم خصوصی، پایش خطاها و بازبینی امنیتی تکمیل شوند. برای آزمون‌های پرریسک، نسخه‌گذاری و snapshot محتوای سؤال هنگام انتشار نیز لازم است.

چک‌لیست: [docs/SECURITY_PILOT_CHECKLIST.md](docs/SECURITY_PILOT_CHECKLIST.md).
