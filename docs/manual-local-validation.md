# Ручная проверка локального запуска и функциональности QuizCraft

Этот файл описывает, как локально запустить QuizCraft на Windows и вручную проверить основные backend, frontend, provider, RAG, кеш, редактирование, регенерацию и экспортные сценарии.

## 1. Что проверяем

Проверка покрывает текущие возможности продукта:

- локальный backend FastAPI;
- статический frontend;
- LM Studio как основной локальный provider;
- Ollama как опциональный provider, если он настроен;
- загрузку русских `TXT`, `DOCX`, `PDF` документов;
- прямую генерацию квиза;
- RAG-генерацию;
- повторную RAG-генерацию и наблюдаемое использование кеша;
- редактирование и сохранение квиза;
- регенерацию одного вопроса и отмену регенерации;
- экспорт в `JSON`, `DOCX`, `PPTX`;
- сохранность русского/кириллического текста на всех этапах.

## 2. Предварительные требования

- Windows с PowerShell 5.1 или новее.
- Python с установленными зависимостями проекта.
- Репозиторий находится в `D:\github\quizcraft`.
- Для удобства желательно иметь `.venv`; скрипт backend активирует `.venv\Scripts\Activate.ps1`, если файл существует.
- LM Studio запущен локально с включенным server mode.
- В LM Studio загружена модель, совпадающая с `LM_STUDIO_MODEL`.
- Для RAG нужна поддержка embeddings у выбранного provider.
- Для проверки DOCX/PPTX нужны Word, PowerPoint, LibreOffice или совместимые просмотрщики.

## 3. Подготовка `.env`

Открой PowerShell в корне проекта:

```powershell
Set-Location D:\github\quizcraft
```

Если файла `.env` еще нет, создай его из шаблона:

```powershell
Copy-Item .env.example .env
notepad .env
```

Минимальные значения для LM Studio:

```env
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=<имя_загруженной_модели_в_LM_Studio>
REQUEST_TIMEOUT=300
MAX_FILE_SIZE_MB=10
MAX_DOCUMENT_CHARS=50000
LOG_LEVEL=INFO
```

Если используешь whitelist моделей, добавь текущую модель:

```env
LM_STUDIO_ALLOWED_MODELS=<имя_загруженной_модели_в_LM_Studio>
```

Для Ollama, если хочешь проверить его отдельно:

```env
PROVIDERS_ENABLED=lm_studio,ollama
DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=<ollama_chat_model>
OLLAMA_EMBEDDING_MODEL=<ollama_embedding_model>
LM_STUDIO_ALLOWED_MODELS=<lm_studio_model>,<ollama_chat_model>
```

Если Ollama не проверяется, эти значения не нужны.

## 4. Как запустить локально

### 4.1. Запустить LM Studio

В LM Studio:

1. Загрузи модель, указанную в `LM_STUDIO_MODEL`.
2. Включи локальный server mode.
3. Проверь, что endpoint доступен на `http://localhost:1234/v1`.
4. Оставь LM Studio открытым на время проверки.

### 4.2. Запустить backend

Открой отдельное окно PowerShell:

```powershell
Set-Location D:\github\quizcraft
.\run-backend.ps1
```

Ожидаемый результат:

- backend стартует на `http://127.0.0.1:8000`;
- нет traceback;
- если `.venv` отсутствует, допускается warning о system Python;
- если `.env` отсутствует, будет warning, но для полной проверки `.env` должен быть настроен.

Ручной запуск без скрипта:

```powershell
Set-Location D:\github\quizcraft
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4.3. Запустить frontend

Открой второе окно PowerShell:

```powershell
Set-Location D:\github\quizcraft
.\run-frontend.ps1
```

Ожидаемый результат:

- frontend доступен на `http://127.0.0.1:5500`.

Открой UI:

```powershell
Start-Process http://127.0.0.1:5500
```

Ручной запуск без скрипта:

```powershell
Set-Location D:\github\quizcraft
python -m http.server 5500 --directory frontend
```

## 5. Быстрая проверка API перед UI

В третьем окне PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/lm-studio
Invoke-RestMethod http://127.0.0.1:8000/export/formats
```

Ожидается:

- `/health` возвращает `status: ok`;
- `generation_modes` содержит `direct`, `rag`, `single_question_regen`;
- `providers_enabled` содержит `lm_studio`;
- `/health/lm-studio` показывает доступность LM Studio;
- `/export/formats` содержит `json`, `docx`, `pptx`.

Если проверяешь Ollama:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/ollama
```

Ожидается, что provider не disabled и отвечает как доступный. Если Ollama не включен, корректный результат — `status: disabled`.

## 6. Подготовка русских тестовых файлов

Подготовь минимум три файла:

- `russian-small.txt`;
- `russian-small.docx`;
- `russian-small.pdf`.

В каждый файл добавь уникальный маркер:

```text
Проверочный маркер: Ёжик_Москва_2026_кириллица.
```

Для RAG подготовь отдельный длинный русский документ, желательно больше 6000 символов. В нем должны быть несколько разделов с фактами, по которым можно ожидать вопросы.

## 7. Проверка backend-модулей тестами

Полная проверка:

```powershell
Set-Location D:\github\quizcraft
python -m pytest -q
python -m ruff check .
```

Точечная проверка по модулям:

```powershell
python -m pytest backend/tests/test_config.py backend/tests/test_bootstrap.py -q
python -m pytest backend/tests/test_api_health.py backend/tests/test_api_lm_studio.py -q
python -m pytest backend/tests/test_file_validation.py backend/tests/test_parsers.py backend/tests/test_document_ingestion_service.py -q
python -m pytest backend/tests/test_generation_orchestrator.py backend/tests/test_generation_request_builder.py backend/tests/test_quiz_validation.py -q
python -m pytest backend/tests/test_api_upload_and_generate.py backend/tests/test_api_quiz_read.py backend/tests/test_api_quiz_update.py -q
python -m pytest backend/tests/test_chunking.py backend/tests/test_retrieval.py backend/tests/test_context_assembler.py -q
python -m pytest backend/tests/test_rag_orchestrator.py backend/tests/test_api_generation_rag.py backend/tests/test_rag_cache.py -q
python -m pytest backend/tests/test_json_exporter.py backend/tests/test_docx_exporter.py backend/tests/test_pptx_exporter.py backend/tests/test_api_advanced_exports.py -q
python -m pytest backend/tests/test_provider_registry.py backend/tests/test_provider_feature_flags.py backend/tests/test_ollama_client.py -q
python -m pytest tests/test_frontend_shell.py tests/test_repository_layout.py -q
```

Ожидаемый результат для каждого блока — все тесты проходят без failures/errors.

## 8. Ручная проверка через frontend

### 8.1. Открытие UI

1. Открой `http://127.0.0.1:5500`.
2. Открой DevTools в браузере.
3. Проверь вкладку Console.

Pass:

- UI открывается;
- русские подписи отображаются корректно;
- в Console нет критических ошибок JavaScript.

Fail:

- белый экран;
- ошибки загрузки модулей;
- CORS/API ошибки при работающем backend.

### 8.2. Загрузка TXT

1. Загрузи `russian-small.txt`.
2. Дождись успешной загрузки.
3. Найди `document_id`, если UI его показывает.

Pass:

- файл принят;
- UI переходит к параметрам генерации;
- нет ошибки формата или размера.

Проверка артефакта:

```powershell
Get-ChildItem D:\github\quizcraft\.quizcraft\documents | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

Открой последний JSON и проверь, что маркер `Ёжик_Москва_2026_кириллица` не испорчен.

### 8.3. Загрузка DOCX

Повтори сценарий с `russian-small.docx`.

Pass:

- документ парсится;
- кириллица сохранена в `.quizcraft\documents`;
- пустой или битый DOCX не должен приниматься как успешный.

### 8.4. Загрузка PDF

Повтори сценарий с `russian-small.pdf`.

Pass:

- PDF содержит извлекаемый текст;
- документ парсится;
- кириллица сохранена в `.quizcraft\documents`.

Fail:

- PDF является сканом без текстового слоя;
- backend возвращает контролируемую ошибку о невозможности извлечь текст.

### 8.5. Прямая генерация

1. Загрузи русский документ.
2. Выбери режим прямой генерации, если UI показывает выбор режима.
3. Укажи небольшое число вопросов, например 3.
4. Запусти генерацию.

Pass:

- UI показывает прогресс;
- backend не падает;
- появляется квиз;
- вопросы и варианты на русском;
- маркер или факты документа не превращаются в mojibake;
- в `.quizcraft\quizzes` появляется JSON квиза.

Проверка артефакта:

```powershell
Get-ChildItem D:\github\quizcraft\.quizcraft\quizzes | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

### 8.6. RAG-генерация

1. Загрузи длинный русский документ.
2. Выбери режим RAG, если UI показывает выбор режима.
3. Запусти генерацию.

Pass:

- генерация завершается успешно;
- результат отображается как RAG или содержит RAG prompt/version metadata;
- вопросы основаны на содержании документа;
- русский текст сохранен.

Fail:

- ошибка embeddings;
- пустой retrieved context;
- provider не поддерживает embeddings;
- результат не проходит валидацию.

### 8.7. Повторная RAG-генерация и кеш

Перед первой RAG-генерацией:

```powershell
Get-ChildItem D:\github\quizcraft\.quizcraft\rag_cache -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object Name, Length, LastWriteTime
```

После первой RAG-генерации повтори команду. Затем запусти такую же RAG-генерацию по тому же документу и с теми же параметрами, после чего снова повтори команду.

Pass:

- после первой RAG-генерации появляется JSON-файл в `.quizcraft\rag_cache`;
- при повторном одинаковом запросе не создается новый cache artifact;
- timestamp существующего cache artifact не должен обновляться без причины;
- в provider logs видно, что повторный запуск не пересчитывает embeddings всех chunks документа;
- query embedding для поиска может выполняться повторно, это допустимо.

Fail:

- cache artifact не создается после успешной RAG-генерации;
- cache artifact каждый раз перезаписывается для идентичного документа;
- повторный запуск заново считает embeddings всех chunks;
- русский retrieved context становится испорченным.

### 8.8. Редактирование и сохранение квиза

1. Открой сгенерированный квиз в редакторе.
2. Измени один вопрос или объяснение.
3. Добавь текст:

```text
Проверка редактирования: Ёжик_редактор_2026.
```

4. Нажми сохранение.
5. Перезагрузи страницу или заново открой квиз, если UI это поддерживает.

Pass:

- сохранение завершается успешно;
- текст не теряется;
- кириллица сохранена;
- версия или timestamp в `.quizcraft\quizzes\<quiz_id>.json` обновлены.

Fail:

- UI зависает в состоянии сохранения;
- backend возвращает validation error без понятного сообщения;
- после reload правки пропали;
- кириллица испорчена.

### 8.9. Отмена регенерации одного вопроса

1. На карточке вопроса нажми регенерацию.
2. В confirm modal выбери отмену.

Pass:

- modal закрывается;
- вопрос не меняется;
- provider request не должен завершиться заменой вопроса;
- остальные вопросы не меняются.

Fail:

- вопрос изменился после отмены;
- modal нельзя закрыть;
- UI остался заблокированным.

### 8.10. Отмена во время регенерации

1. Запусти регенерацию одного вопроса.
2. Пока операция выполняется, нажми кнопку отмены на карточке или `Esc`, если доступно.

Pass:

- операция отменяется;
- UI возвращается в рабочее состояние;
- исходный вопрос остается прежним;
- в DevTools Network запрос может быть отмечен как canceled/aborted.

Fail:

- отмененный запрос все равно заменил вопрос;
- UI завис;
- изменились другие вопросы.

### 8.11. Успешная регенерация одного вопроса

1. Запусти регенерацию одного вопроса.
2. Дождись завершения.

Pass:

- изменился только выбранный вопрос;
- остальные вопросы остались без изменений;
- новый вопрос валиден;
- русский текст сохранен;
- `.quizcraft\quizzes\<quiz_id>.json` обновлен.

Fail:

- заменился весь квиз;
- изменились соседние вопросы;
- новый вопрос невалиден;
- русский язык потерян.

### 8.12. Экспорт JSON

1. Нажми экспорт JSON.
2. Открой скачанный файл.

Pass:

- файл скачивается;
- JSON валиден;
- сохраненные правки присутствуют;
- кириллица читается нормально.

### 8.13. Экспорт DOCX

1. Нажми экспорт DOCX.
2. Открой файл в Word или LibreOffice.

Pass:

- файл открывается;
- вопросы, варианты и ответы читаемы;
- русский текст не испорчен.

### 8.14. Экспорт PPTX

1. Нажми экспорт PPTX.
2. Открой файл в PowerPoint или LibreOffice.

Pass:

- файл открывается;
- слайды содержат вопросы и варианты;
- русский текст не испорчен.

## 9. Где смотреть данные и логи

Локальные backend artifacts создаются относительно корня запуска backend:

```text
D:\github\quizcraft\.quizcraft\documents
D:\github\quizcraft\.quizcraft\quizzes
D:\github\quizcraft\.quizcraft\rag_cache
```

Что смотреть при ошибках:

- backend PowerShell output;
- frontend PowerShell output;
- browser DevTools Console;
- browser DevTools Network;
- LM Studio logs;
- Ollama logs, если проверяется Ollama;
- JSON files в `.quizcraft\documents`;
- JSON files в `.quizcraft\quizzes`;
- JSON files в `.quizcraft\rag_cache`;
- `request_id` из API response или response headers.

Признаки проблем с кириллицей:

- символы вида `Ð`, `Рџ`, `�`;
- русские буквы заменены вопросительными знаками;
- маркер `Ёжик_Москва_2026_кириллица` отсутствует или поврежден.

## 10. Что записать по итогам проверки

Заполни краткий отчет:

```text
Дата проверки:
Git HEAD:
Windows version:
Python version:
LM Studio model:
Ollama model, если проверялся:

Backend start: pass/fail
Frontend start: pass/fail
Health endpoints: pass/fail
TXT upload: pass/fail
DOCX upload: pass/fail
PDF upload: pass/fail
Direct generation: pass/fail
RAG generation: pass/fail
RAG cache reuse: pass/fail
Edit and save: pass/fail
Single-question regeneration cancel: pass/fail
Single-question regeneration success: pass/fail
JSON export: pass/fail
DOCX export: pass/fail
PPTX export: pass/fail
Cyrillic preservation: pass/fail

Failures:
- request_id:
- screenshot/log excerpt:
- affected artifact path:
- exact user action before failure:
```

Не прикладывай API keys, приватные provider credentials или полный текст чувствительных документов.

## 11. Минимальный happy path

Если нужно быстро проверить только основной сценарий:

1. Запусти LM Studio.
2. Запусти backend через `.\run-backend.ps1`.
3. Запусти frontend через `.\run-frontend.ps1`.
4. Открой `http://127.0.0.1:5500`.
5. Загрузи русский TXT.
6. Сгенерируй direct quiz.
7. Отредактируй один вопрос и сохрани.
8. Экспортируй JSON.
9. Загрузи длинный русский документ.
10. Сгенерируй RAG quiz.
11. Повтори RAG generation и проверь `.quizcraft\rag_cache`.
12. Экспортируй DOCX и PPTX.

Если эти шаги проходят без ошибок и кириллица сохраняется, базовая локальная функциональность работает.
