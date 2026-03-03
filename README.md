# Song Archiver

Программа для пакетного поиска и скачивания песен по текстовому списку с **строгой валидацией**.

Можно работать двумя путями:
- автопоиск (YouTube),
- прямые ссылки на треки с сайтов (`песня | https://...`).

## Что умеет

- читает txt-файл со списком групп и треков;
- проверяет, что найден **каждый** трек (если хотя бы один не найден — останавливается);
- скачивает в MP3 и группирует по папкам исполнителей;
- формирует единый ZIP-архив;
- даёт 2 интерфейса: CLI и веб-страницу.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Также нужен `ffmpeg` в PATH (для конвертации в mp3).

## Формат входного списка

Можно смешивать форматы:

```txt
[Linkin Park]
Numb
In The End

Group: Imagine Dragons
- Believer
- Demons

Adele - Hello

# Формат 4: прямые ссылки на треки с сайтов
Kino - Gruppa Krovi | https://example.com/track1
[DDT]
Rodina | https://example.com/track2
```

Пример готового файла: `sample_songs.txt`.

## CLI запуск

```bash
python main.py --input sample_songs.txt
```

Интерактивный CLI:

```bash
python main.py --interactive
```

Параметры:
- `--input, -i` — путь к txt-файлу;
- `--output, -o` — рабочая папка (`downloads` по умолчанию);
- `--archive-name` — имя zip без расширения;
- `--min-score` — порог совпадения (0..1), по умолчанию `0.78`.
- `--proxy` — прокси: `host:port` или полный URL `http://user:pass@host:port`.
- `--proxy-user`, `--proxy-password` — логин/пароль прокси.
- `--cookies-file` — путь к `cookies.txt` (Netscape format) для обхода YouTube anti-bot.
- `--cookies-from-browser` — взять cookies из браузера (`chrome`, `edge`, `firefox`).
- `--js-runtime` — JS runtime для yt-dlp (рекомендуется `node`).


### Пример запуска с прокси

```bash
python main.py --input songs.txt --output downloads --archive-name songs --min-score 0.80 \
  --proxy 154.218.23.64:62794 --proxy-user FajEdqBYN --proxy-password CDYN99hjD
```

Если прокси не нужен, просто не указывайте эти параметры.

### Пример запуска с cookies (когда YouTube просит "Sign in to confirm you're not a bot")

```bash
python main.py --input songs.txt --cookies-file "C:\\Users\\edmir\\youtube_cookies.txt" --js-runtime node
```

или

```bash
python main.py --input songs.txt --cookies-from-browser chrome --js-runtime node
```

## Веб-интерфейс

Запуск:

```bash
python app.py
```

Откройте `http://127.0.0.1:8000`.

На странице вставьте список песен, укажите `min score` и имя архива — после успешной строгой проверки браузер сразу скачает ZIP.

Если указана прямая ссылка (`| https://...`), программа скачивает трек с этой ссылки через `yt-dlp` и не делает YouTube-поиск для этой строки.

## Как работает строгая валидация

1. Программа ищет несколько кандидатов для каждой песни.
2. Считает similarity score по названию + исполнителю.
3. Если хотя бы один трек ниже `min-score`, скачивание не начинается.

Это гарантирует, что архив создаётся только когда все песни подтверждены.


## Частые ошибки

- `No module named 'yt_dlp'` — не установлены зависимости. Выполните:

```bash
pip install -r requirements.txt
```

## Тесты

```bash
pytest -q
```
