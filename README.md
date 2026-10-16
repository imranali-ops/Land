# ভূমিপত্র: ডিজিটাল ভূমি রেকর্ড, যাচাই ও ই-মিউটেশন (প্রোটোটাইপ)

LandTech Innovation Hackathon 2026. শুধু কাল্পনিক/নমুনা তথ্য ব্যবহার করুন, আসল NID বা জমির তথ্য নয়।

## ফোল্ডার
- `core/` হ্যাশ চেইন, যাচাই, দুইবার বিক্রি ঠেকানো (শুধু Python, Django ছাড়াই চলে)
- `accounts/` কাস্টম ইউজার ও রোল
- `records/` জমি, মালিক, মালিকানার ইতিহাস, সার্ভিস, অ্যাডমিন, টেস্ট
- `config/` Django সেটিংস ও URL
- `website/index.html` প্রজেক্ট পরিচিতির ওয়েবসাইট (ব্রাউজারে খুলুন)

## চালানোর ধাপ
1. `python -m venv .venv` তারপর Windows: `.venv\Scripts\activate`, Linux/Mac: `source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `.env.example` কপি করে `.env` বানান (Windows: `copy .env.example .env`)
4. `python -c "import secrets; print(secrets.token_urlsafe(64))"` তিনবার চালিয়ে `DJANGO_SECRET_KEY`, `NID_HMAC_KEY`, `DB_PASSWORD`-এ আলাদা মান বসান। `.env` কাউকে দেবেন না।
5. `docker compose up -d db` (অথবা নিজে PostgreSQL ইনস্টল করুন)
6. `python manage.py makemigrations accounts records`
7. `python manage.py migrate`
8. `python manage.py check`
9. `python manage.py test` (৩২টি টেস্ট পাস করার কথা)
10. `python manage.py createsuperuser` ও `python manage.py runserver`

শুধু Django ছাড়া মূল যুক্তি পরীক্ষা: `python -m unittest core.test_integrity`

## অবস্থা
Day 1-2 সম্পন্ন। বাকি: লগইন ও রোল, ডিজিটাল সিগনেচার, ডাটাবেস-স্তরের অডিট লগ, API, নামজারি, ফ্রন্টএন্ড, নিরাপত্তা পরীক্ষা, ডিপ্লয়মেন্ট।
