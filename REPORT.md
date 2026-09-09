# التقرير التقني الكامل — مشروع Hamrabi

## 1. نبذة عن المشروع

Hamrabi هو **منصة OSINT ذكية** (Open Source Intelligence) تساعد المحققين والباحثين على
جمع المعلومات من **المصادر المفتوحة والعامة فقط** (DNS، WHOIS، شهادات TLS، ملفات HTTP
العلنية، الملفات الشخصية العامة) وربطها مع بعضها لاكتشاف العلاقات بين الكيانات
(إيميل → دومين → IP → ...) مع حساب **درجة الثقة (Confidence)** لكل معلومة بناءً على
الأدلة، ثم تحليل النتائج بالذكاء الاصطناعي وإصدار **تقرير PDF** رسمي.

> للاستخدام القانوني والأكاديمي فقط — لا تهاجم ولا تصل إلى حسابات خاصة.

---

## 2. لغات البرمجة المستخدمة

| الجزء | اللغة | السبب |
| --- | --- | --- |
| **Backend (الخادم)** | Python 3.11+ | سرعة التطوير + مكتبات OSINT/AI جاهزة |
| **Frontend (الواجهة)** | JavaScript + JSX (React) | واجهات تفاعلية حديثة |
| **التخزين** | JSON (ملف محلي) / SQLite | بدون خادم قواعد بيانات إضافي |
| **البناء/النشر** | Docker Compose + Shell (PowerShell/Bat) | تشغيل مبسّط |

---

## 3. التقنيات والمكتبات المستخدمة

### Backend (`backend/requirements.txt`)
- **FastAPI 0.115** — إطار عمل API حديث وموثق آليًا.
- **Uvicorn** — خادم Python للـ API.
- **Pydantic 2** — التحقق من بيانات الإدخال (Validation).
- **PyJWT** — مصادقة بتذاكر JWT.
- **httpx** — الاتصال بالمصادر الخارجية (طُلب HTTP).
- **dnspython** — استعلامات DNS.
- **python-multipart** — استقبال رفع الصور.
- **reportlab** — إنشاء تقارير PDF.
- (اختياري) `pillow + pytesseract` — محرك OCR لتقنية الصور.

### Frontend (`frontend/package.json`)
- **React 18** + **ReactDOM** — بناء الواجهة.
- **React Router 6** — التنقل بين الصفحات.
- **Vite 5** — سيرفر تطوير سريع + بناء للتوزيع.

### أدوات
- **pytest** — اختبارات الوحدات.
- **Docker Compose** — تشغيل الخدمتين معًا.
- **Pydantic 2** — نوع البيانات في الـ API.

---

## 4. البنية المعمارية (Architecture)

```
                ┌──────────────────────────────────────────────┐
                │              INPUT                            │
                │  نص / اسم مستخدم / إيميل / دومين / IP /       │
                │  رابط / صورة  ──► Image OCR (استخراج نص/EXIF) │
                └──────────────────┬───────────────────────────┘
                                   ▼
                ┌──────────────────────────────────────────────┐
                │       Input Manager (تصنيف + تنظيف الإدخال)    │
                │       Entity Extraction (استخراج الكيانات)     │
                └──────────────────┬───────────────────────────┘
                                   ▼
                ┌──────────────────────────────────────────────┐
                │      OSINT Connectors                        │
                │  DNS · WHOIS · Certificate · HTTP/fingerprint│
                │  Subdomains (CT) · Public Profiles            │
                └──────────────────┬───────────────────────────┘
                                   ▼
                ┌──────────────────────────────────────────────┐
                │   Confidence Engine (درجة الثقة من الأدلة)     │
                │   Correlation Engine (رسم بياني للعلاقات)       │
                └──────────────────┬───────────────────────────┘
                                   ▼
                ┌──────────────────────────────────────────────┐
                │      AI Analysis (ملخص · تصنيف · تفسير)        │
                │      ملخص مؤكَّد بالأدلة فقط                    │
                └──────────────────┬───────────────────────────┘
                                   ▼
                ┌──────────────────────────────────────────────┐
                │  Dashboard · Graph View · PDF Report         │
                └──────────────────────────────────────────────┘
```

### مكونات Backend بالتفصيل

| الملف | الوظيفة |
| --- | --- |
| `app/main.py` | إنشاء تطبيق FastAPI + CORS + Rate Limiter + تضمين الـ Routers |
| `app/core/config.py` | إعدادات عبر متغيرات البيئة (Secret، CORS، TTL، limits) |
| `app/core/security.py` | تجزئة كلمات المرور + JWT |
| `app/core/limiter.py` | ميدلويار تقييد المعدل (60 طلب/دقيقة) |
| `app/modules/input_manager.py` | تصنيف نوع الإدخال + تنظيفه |
| `app/modules/entity_extraction.py` | استخراج IPs / إيميلات / دومينات / URLs / أسماء مستخدمين |
| `app/modules/ocr.py` | OCR + EXIF + فحص التوقيعات السحرية للصور |
| `app/modules/confidence.py` | قواعد حتمية لدرجات الثقة (evidence-based) |
| `app/modules/correlation.py` | محرك الربط بين الكيانات (graph engine) |
| `app/connectors/` | موصل واحد لكل مصدر بنفس schema الموحّد |
| `app/services/pipeline.py` | التنسيق الكامل + التوسع دومين→IP |
| `app/services/ai.py` | ذكاء اصطناعي متعدد (OpenAI/Anthropic) + بديل دون الحجز |
| `app/services/report.py` | PDF (ملخص تنفيذي، نتائج، مصادر، رسم بياني، جدول زمني، AI) |
| `app/services/store.py` | تخزين JSON/SQLite (مستخدمون + تحقيق + علاقات) |
| `app/api/routes/` | مسارات: auth · investigations · upload · ai · share |
| `app/models/entities.py` | نماذج البيانات (User, Investigation, Entity...) |

### مكونات Frontend
| الصفحة | الوظيفة |
| --- | --- |
| `pages/Login.jsx` | تسجيل الدخول |
| `pages/Dashboard.jsx` | قائمة التحقيقات |
| `pages/NewInvestigation.jsx` | إدخال نص / مؤشر + رفع صورة (OCR/EXIF) |
| `pages/Results.jsx` | الكيانات والنتائج والأدلة وزر تحليل AI |
| `pages/EntityView.jsx` | تفاصيل كيان واحد + علاقاته |
| `pages/Sources.jsx` | جدول المصادر (Source/Timestamp/Query/Result/Confidence) |
| `pages/GraphView.jsx` | رسم بياني تفاعلي للعلاقات |

---

## 5. واجهة API (المسارات الرئيسية)

- `GET /api/health` — فحص سلامة الخادم.
- `POST /api/auth/register` — تسجيل مستخدم جديد.
- `POST /api/auth/token` — تسجيل الدخول واستخراج الـ JWT.
- `POST /api/investigations` — إنشاء تحقيق (إدخال + استخراج + توكيyezh).
- `GET /api/investigations` — قائمة تحقيقات المستخدم.
- `GET /api/investigations/{id}` — تفاصيل تحقيق.
- `POST /api/upload` — رفع صورة لـ OCR/EXIF.
- `POST /api/investigations/{id}/ai` — تحليل الذكاء الاصطناعي.
- `GET /api/investigations/{id}/report` — تنزيل تقرير PDF.
- `POST /api/investigations/{id}/share` — إنشاء رابط مشاركة.

> وثائق الـ API التفاعلية: `http://127.0.0.1:8000/docs`

---

## 6. طريقة التشغيل والاستخدام

### المتطلبات
- Python 3.11+
- Node.js 18+
- Docker (اختياري)

### الطريقة الأولى — التشغيل التلقائي (Windows)
```powershell
./start.ps1
```
يبدأ الخادم + الواجهة معًا ويفتح المتصفح على `http://localhost:5173`.

### الطريقة الثانية — يدويًا
```powershell
# 1) Backend
py -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -r backend\requirements.txt
backend\.venv\Scripts\python backend\run.py      # -> http://127.0.0.1:8000

# 2) Frontend
cd frontend
npm install
npm run dev                                      # -> http://localhost:5173
```

### الطريقة الثالثة — Docker
```bash
docker compose up --build   # backend :8000 - frontend :5173
```

### خطوات الاستخدام داخل النظام
1. **سجّل حساب** جديد من صفحة `Login`.
2. من **New Investigation** أدخل نصًا تحقيقيًا (نص حر) أو مؤشرًا (IP/إيميل/دومين/URL)،
   أو ارفع **صورة** لاستخراج نصها وبيانات EXIF.
3. النظام يستخرج **الكيانات** ويلاحظ **الأدلة** من كل موصل.
4. تصفح **Results** لعرض النتائج، و**Entity View** لتفاصيل كل كيان،
   و**Graph View** للعلاقات البصرية، و**Sources** لجدول الأدلة مع درجات الثقة.
5. اضغط **Analyze with AI** لتوليد ملخص وتصنيف مؤيّد بالأدلة (يتطلب مفتاح OpenAI/Anthropic).
6. اضغط **Download PDF** لإنشاء التقرير الرسمي (ملخص تنفيذي + رسم بياني + جدول زمني).

### تفعيل الذكاء الاصطناعي (اختياري)
```powershell
set HAMRABI_AI_PROVIDER=openai
set OPENAI_API_KEY=sk-...
# أو:
set HAMRABI_AI_PROVIDER=anthropic
set ANTHROPIC_API_KEY=...
```
> بدون مفتاح، يتحول النظام تلقائيًا إلى مُلخّص حتمي (offline fallback).

### OCR (اختياري)
```bash
pip install pillow pytesseract
# + تثبيت محرك Tesseract من: https://github.com/tesseract-ocr/tesseract
```

---

## 7. الاختبارات (Testing)

```powershell
backend\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
backend\.venv\Scripts\python -m pytest backend\tests -q
```

يغطي المجموعة، التحكم في الصلاحيات، معالجة الإدخال، الحماية من XSS/CRLF،
التحقق من الرفعات، تقييد المعدل، معالجة الثقة، استخراج الكيانات والتنبيه.

### فحص سريع
```powershell
backend\.venv\Scripts\python backend\sanity_check.py
```

---

## 8. هيكل التخزين

| المخزن | المحتوى |
| --- | --- |
| `backend/app/hamrabi.db` (JSON) | المستخدمون والتحقيقات علاقاتهم |
| `backend/app/generated_reports/` | نسخة PDF الناتجة لكل تحقيق |

---

## 9. ملخص الأرقام

- **اللغات:** Python + JavaScript (React) + JSON.
- **المصادرات:** FastAPI + Uvicorn + Pydantic + JWT + httpx + dnspython + reportlab.
- **الواجهة:** React 18 + React Router 6 + Vite.
- **التشغيل:** PowerShell script / Docker Compose.
- **الkhodma:** Backend API :8000 + Frontend :5173 + تقارير PDF.

---

*انتهى التقرير — كان يوم 2026-08-08.*