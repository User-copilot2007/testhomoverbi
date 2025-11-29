Простий приклад Django‑сайту з реєстрацією та входом (username + password).

1) Створи віртуальне середовище та встанови Django (в корені з цим архівом):
   python -m venv venv
   venv\Scripts\activate  (Windows)
   source venv/bin/activate (Linux / macOS)

   pip install "django>=4.2,<6.0"

2) Перейди в папку проекту:
   cd django_auth_site

3) Зроби міграції БД:
   python manage.py migrate

4) (Необов'язково) Створи адміністратора:
   python manage.py createsuperuser

5) Запусти dev-сервер:
   python manage.py runserver

6) Зайди в браузері:
   http://127.0.0.1:8000/                  — головна
   http://127.0.0.1:8000/accounts/signup/  — реєстрація
   http://127.0.0.1:8000/accounts/login/   — вхід

Все працює на стандартній моделі User.
