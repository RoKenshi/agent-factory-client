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
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh
less install.sh
sh install.sh
```

## Установка Windows PowerShell

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1
Get-Content .\install.ps1
.\install.ps1
```

Скрипт определит платформу, скачает архив из публичного GitHub Release, проверит Ed25519-подпись
`SHA256SUMS`, затем SHA-256 архива и выполнит встроенный `self-test`. Windows также требует
валидную Authenticode-подпись исполняемого файла.
