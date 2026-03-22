# 🤖 Bot Discord — Scoutinho Team

## Co robi bot?
- ✅ Tworzy kanały komendą `!setup`
- 👋 Wita nowych członków na kanale #👋 | witam
- 🎮 Nadaje rolę **gracz** automatycznie po dołączeniu
- 🚫 Usuwa wulgaryzmy automatycznie
- 📋 Logi wejść/wyjść na kanale #logi
- 🎬 Powiadomienia o nowym filmiku na YouTube
- 🔴 Powiadomienia o streamie na Kick
- 🎉 Giveawaye z odliczaniem i losowaniem

---

## ⚙️ Instalacja na Railway

### Krok 1 — GitHub
1. Wejdź na https://github.com i utwórz konto (jeśli nie masz)
2. Kliknij **+** → **New repository**
3. Nazwij go np. `sztywne-gity-bot`
4. Wgraj pliki: `bot.py` i `requirements.txt`

### Krok 2 — Railway
1. Wejdź na https://railway.app
2. Zaloguj się przez GitHub
3. Kliknij **New Project** → **Deploy from GitHub repo**
4. Wybierz swoje repozytorium

### Krok 3 — Zmienne środowiskowe
W Railway wejdź w **Variables** i dodaj:

| Zmienna | Wartość |
|---------|---------|
| `DISCORD_TOKEN` | Token Twojego bota z Developer Portal |
| `YT_API_KEY` | Klucz YouTube Data API v3 (patrz niżej) |

### Krok 4 — YouTube API Key (darmowe)
1. Wejdź na https://console.cloud.google.com
2. Utwórz nowy projekt
3. Wyszukaj **YouTube Data API v3** → włącz
4. Wejdź w **Credentials** → **Create credentials** → **API Key**
5. Skopiuj klucz i wklej do Railway jako `YT_API_KEY`

---

## 🎮 Komendy bota

| Komenda | Opis |
|---------|------|
| `!setup` | Tworzy wszystkie kanały (tylko admin) |
| `!giveaway 2 Skin CS2` | Giveaway na 2 dni o Skina CS2 |

---

## ➕ Dodanie wulgaryzmów
W pliku `bot.py` znajdź linię:
```python
BANNED_WORDS = ["chuj", "kurwa", ...]
```
I dodaj kolejne słowa do listy.
