# Signal Processor

Desktop application for signal and noise spectrum analysis.

## Установка uv

Проект запускается и собирается через [uv](https://docs.astral.sh/uv/).

### Windows

Через PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Или через WinGet:

```powershell
winget install --id=astral-sh.uv -e
```

### Linux и macOS

Через официальный установщик:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Или через пакетный менеджер:

```sh
brew install uv
```

Для Linux также можно использовать пакетный менеджер вашего дистрибутива.

### Проверка установки:

```sh
uv --version
```

## Запуск

Из корня проекта:

```sh
uv sync
uv run python src/main.py
```

## Сборка

PyInstaller собирает приложение для платформы, на которой запускается сборка.

```sh
uv sync
uv run pyinstaller --clean SignalProcessor.spec
```

Результат сборки находится в `dist/`.

`config.toml` используется как внешний файл и должен находиться рядом с приложением.
