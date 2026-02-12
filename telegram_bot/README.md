# Telegram Baholash Boti

## Ishga tushirish

1. Python 3.11+ o‘rnating.
2. Kutubxonalarni o‘rnating:

```bash
pip install -r requirements.txt
```

3. `.env` faylini yarating:

```bash
cp .env.example .env
```

4. `.env` ichida `BOT_TOKEN` ni kiriting.

5. Botni ishga tushiring:

```bash
python -m app.bot
```

## Telegram sozlamalari

- Botni guruhga admin qiling.
- Privacy mode o‘chirilgan bo‘lishi kerak (`/setprivacy` → `Disable`).

## Asosiy buyruqlar

**Guruh ichida:**
- `/add @username Ism Familiya` yoki reply `/add Ism Familiya`
- `/grade` — baholashni boshlash
- Baholash tugagach oraliq inline xabar o'chadi, faqat baho xabari qoladi
- Bitta `Leaderboard` xabari guruhda yangilanib boradi va pin qilinadi

**Ota‑ona (private):**
- `/start` — ro‘yxatdan o‘tish va menyuni ochish
- `Bolani bog'lash` tugmasi — avval `#kod`, keyin faqat bola ismi tekshiruvi
- Ism tekshiruvi katta-kichik harfga bog'liq emas, kirill va lotin yozuvlari ham mos deb olinadi
- `Bog'langan bolalarim` tugmasi — bog‘langan bolalar ro‘yxati
- `Admin panel` tugmasi — faqat `6329800356` ID uchun, barcha guruh va o'quvchilar ro'yxatini ko'rsatadi
