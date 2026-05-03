# QuizCraft

<p align="center">
  <img src="docs/images/hero.png" alt="QuizCraft UI" width="900">
</p>

<p align="center">
  <strong>Генерация квизов из любого документа — локально, без облака, на русском языке.</strong>
</p>

---

QuizCraft — локальный сервис генерации квизов на основе LLM. Загружаете документ (TXT, DOCX, PDF), выбираете параметры — получаете готовый квиз с вопросами разных типов. Редактируете прямо в браузере, экспортируете в JSON, DOCX или PPTX.

## Возможности

- **5 типов вопросов** — множественный выбор, истина/ложь, заполнить пробел, краткий ответ, соответствие
- **Прямая и RAG-генерация** — прямой промпт для коротких документов, RAG с векторным поиском для длинных
- **Редактор квиза** — правка вопросов, вариантов ответа, пересоздание отдельных вопросов без перегенерации всего квиза
- **Экспорт** — JSON, DOCX (карточки + ключ ответов), PPTX (quiz-show стиль, 2 слайда на вопрос)
- **Русский язык** — полная поддержка кириллицы на всём пути: парсинг → генерация → хранение → UI → экспорт
- **Полностью локально** — работает с LM Studio или Ollama, данные не покидают машину

## Быстрый старт

### Требования

- Python 3.11+
- [LM Studio](https://lmstudio.ai/) с загруженной моделью (или Ollama)
- PowerShell (Windows)

### Установка и запуск

```powershell
# 1. Клонировать и перейти в директорию
git clone https://github.com/bk-ru/quizcraft.git
cd quizcraft

# 2. Создать виртуальное окружение и установить зависимости
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

# 3. Настроить окружение
Copy-Item .env.example .env
# Отредактировать .env: указать имя модели в LM_STUDIO_MODEL

# 4. Запустить бэкенд и фронтенд (каждый в своём окне PowerShell)
.\run-backend.ps1
.\run-frontend.ps1
```

Открыть в браузере: **http://127.0.0.1:5500**

Бэкенд работает на `http://127.0.0.1:8000`, LM Studio ожидается на `http://127.0.0.1:1234`.

### Ручной запуск

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
python -m http.server 5500 --directory frontend
```

## Архитектура

```
quizcraft/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI маршруты (documents, generation, quizzes, settings, health)
│   │   ├── core/         # Конфигурация, провайдеры LLM (LM Studio, Ollama)
│   │   ├── domain/       # Модели, валидация, нормализация, ошибки
│   │   ├── export/       # Экспортёры JSON / DOCX / PPTX
│   │   ├── generation/   # Оркестраторы direct и RAG, кэш эмбеддингов, качество
│   │   ├── parsing/      # Парсеры TXT / DOCX / PDF, чанкинг
│   │   ├── prompts/      # Реестр промптов генерации и repair
│   │   └── storage/      # Файловое хранилище (.quizcraft/)
│   └── tests/            # pytest: поведение бэкенда, Cyrillic-покрытие
├── frontend/
│   ├── app.js            # Точка входа, композиция модулей
│   ├── generation-flow.js
│   ├── quiz-editor.js
│   ├── quiz-renderer.js
│   └── *.css             # tokens, base, layout, forms, quiz, feedback, responsive
├── docs/
│   ├── images/           # hero.png и другие медиафайлы
│   └── execplans/        # Планы выполнения задач
├── tests/                # pytest: структура репозитория, frontend shell
├── run-backend.ps1
└── run-frontend.ps1
```

## Конфигурация

Все настройки задаются через `.env` (на основе `.env.example`):

| Переменная | Описание |
|---|---|
| `LM_STUDIO_BASE_URL` | URL LM Studio (по умолчанию `http://127.0.0.1:1234`) |
| `LM_STUDIO_MODEL` | Имя модели, загруженной в LM Studio |
| `OLLAMA_BASE_URL` | URL Ollama (по умолчанию `http://127.0.0.1:11434`) |
| `OLLAMA_MODEL` | Имя модели Ollama |
| `PROVIDERS_ENABLED` | Список активных провайдеров, напр. `lm_studio,ollama` |
| `DEFAULT_PROVIDER` | Провайдер по умолчанию |
| `QUIZCRAFT_STORAGE_DIR` | Директория хранилища (по умолчанию `.quizcraft`) |

## Форматы экспорта

| Формат | Описание |
|---|---|
| **JSON** | Полная структура квиза со всеми полями |
| **DOCX** | Два раздела: карточки вопросов без ответов + таблица-ключ ответов |
| **PPTX** | Quiz-show стиль: слайд-вопрос + слайд-ответ для каждого вопроса |

## Проверки

```powershell
python -m pytest -q          # все тесты (450+)
python -m ruff check .        # линтер Python
```

## Стек

- **Backend** — FastAPI, Pydantic, python-docx, python-pptx, PyMuPDF
- **LLM** — LM Studio / Ollama (локальные модели, structured output)
- **Frontend** — Vanilla HTML/CSS/JS, без фреймворков
- **Хранилище** — JSON-файлы на диске (`.quizcraft/`)
- **Тесты** — pytest, 450+ тестов с покрытием кириллицы
