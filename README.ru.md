# Загрузка Agent Factory

Это публичный репозиторий для установки и проверки Agent Factory. Здесь находятся только понятные
installer-скрипты, privacy/security документы, checksums и скомпилированные бинарники в Releases.
Исходный код закрытого движка и control-plane здесь не публикуется.

Agent Factory никогда не отправляет на свой сервер ключи модельных провайдеров, исходный код,
промпты, diff, пути репозитория, вывод терминала или ответы моделей. Provider key остаётся на
компьютере пользователя и используется локальным runtime только для выбранного пользователем
OpenAI-compatible endpoint.

Удалённая техническая статистика выключена по умолчанию, не содержит контента и требует отдельного
локального и серверного согласия. Точные ограничения описаны в [PRIVACY.md](PRIVACY.md).

## Установка Linux/macOS

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh && sh install.sh
```

Для опубликованных macOS-релизов также доступен Homebrew tap:

```bash
brew install rokenshi/tap/agent-factory
```

## Установка Windows PowerShell

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1; .\install.ps1
```

Скрипт определит платформу, скачает архив из публичного GitHub Release, проверит RSA-SHA256 подпись
файла `SHA256SUMS`, затем checksum архива и выполнит встроенный `self-test`. После проверки
установщик сам откроет локальный onboarding. Повторный запуск безопасно обновляет command link;
для headless-режима задайте `AGENT_FACTORY_NO_SETUP=1`. Не используйте `sudo`.
