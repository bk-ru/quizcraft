# Диаграмма пакетов: LLM

Показывает структуру и зависимости модулей внутри пакета `llm`.

## Модули

- **llm** — корневой пакет, экспортирует провайдеры и фабрику.
- **provider** — абстрактный класс `LLMProvider` и базовые модели.
- **lm_studio** — клиент LM Studio.
- **ollama** — клиент Ollama.
- **external_api** — клиент внешнего OpenAI-compatible API.
- **registry** — `ProviderRegistry` и `ProviderName`.
- **retry** — `RetryPolicy` и `RetryingCaller`.
- **factory** — фабрика: собирает `ProviderRuntime` из конфигурации, инстанцирует нужный клиент.

## Зависимости

- Все три клиента (`lm_studio`, `ollama`, `external_api`) зависят от `provider` и `retry`.
- `registry` зависит от `provider`.
- `factory` зависит от всех клиентов, `provider` и `registry`.
- `llm` экспортирует всё кроме `factory`.

## Диаграмма

```mermaid
classDiagram
  class llm {
  }
  class external_api {
  }
  class factory {
  }
  class lm_studio {
  }
  class ollama {
  }
  class provider {
  }
  class registry {
  }
  class retry {
  }
  llm --> external_api
  llm --> lm_studio
  llm --> ollama
  llm --> provider
  llm --> registry
  llm --> retry
  external_api --> provider
  external_api --> retry
  factory --> external_api
  factory --> lm_studio
  factory --> ollama
  factory --> provider
  factory --> registry
  lm_studio --> provider
  lm_studio --> retry
  ollama --> provider
  ollama --> retry
  registry --> provider
```
