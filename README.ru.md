# Загрузка Agent Factory

Это публичный репозиторий для установки и проверки Agent Factory. Здесь находятся только понятные
installer-скрипты, privacy/security документы, checksums и скомпилированные бинарники в Releases.
Исходный код закрытого движка и control-plane здесь не публикуется.

Agent Factory никогда не отправляет на свой сервер ключи модельных провайдеров, исходный код,
промпты, diff, пути репозитория, вывод терминала или ответы моделей. Provider key остаётся на
компьютере пользователя и используется локальным runtime только для выбранного пользователем
OpenAI-compatible endpoint.

После 24-часового пробного периода зарегистрированное использование требует отправки одного
обезличенного от содержимого пакета статистики в сутки. Он содержит только ограниченные поля о
модели, типе задачи, результате, длительности, токенах и известной стоимости. Код, промпты, ответы,
пути и provider keys не отправляются. Точный контракт описан в [PRIVACY.md](PRIVACY.md).

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

Обычная настройка состоит из четырёх решений: выбрать провайдера, вставить его ключ, выбрать режим
«экономия / баланс / качество» и подключить найденный coding agent. Модели по ролям назначаются
автоматически. В Advanced settings доступны точные чекбоксы моделей, custom OpenAI-compatible
endpoint, цепочки fallback для каждой роли и замена ключей. Новый ключ сначала проверяется, а уже
запущенные задачи сохраняют прежний обезличенный снимок маршрута. Команда `agent-factory open`
возвращает в локальный dashboard; постоянная локальная база данных не нужна.

## Обновление и удаление

Для обновления просто снова запустите установщик: он проверит подпись нового `latest`-релиза и
переключит команду на новую версию. Удаление бинарников сохраняет локальные настройки и историю:

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/uninstall.sh && sh uninstall.sh
```

Полное удаление локального состояния выполняется только явно: `sh uninstall.sh --purge-state`.
В Windows скачайте `uninstall.ps1` из этого репозитория и запустите `./uninstall.ps1`; для полного
удаления состояния используйте `./uninstall.ps1 -PurgeState`.
