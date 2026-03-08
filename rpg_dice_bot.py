"""
🎲 RPG Dice Bot — для RP-игр в стиле Library of Ruina / DnD

Установка:
    pip install python-telegram-bot

Запуск:
    1. Вставь свой токен в TOKEN ниже
    2. python rpg_dice_bot.py
"""

import re
import random
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)

# ─── НАСТРОЙКА ────────────────────────────────────────────────────────────────
TOKEN = "8756493820:AAFQiLdIE8hwTbP23GLOqfo_iJNF1--PzoQ"  # Получить у @BotFather в Telegram
# ──────────────────────────────────────────────────────────────────────────────


# ─── ПАРСИНГ ──────────────────────────────────────────────────────────────────

def parse_roll(text: str):
    """
    Разбирает текст броска.
    Примеры:
        "3-5"            → (3, 5, 0, 0)
        "5-10 +2"        → (5, 10, 2, 0)
        "3-8 +15%"       → (3, 8, 0, 15)
        "5-12 +3 +20%"   → (5, 12, 3, 20)
        "3-5 -1 -10%"    → (3, 5, -1, -10)
    Возвращает None если формат неверный.
    """
    text = re.sub(r'^/\w+\s*', '', text).strip()

    range_match = re.search(r'(\d+)\s*[-–]\s*(\d+)', text)
    if not range_match:
        return None

    min_val = int(range_match.group(1))
    max_val = int(range_match.group(2))

    if min_val > max_val:
        min_val, max_val = max_val, min_val

    after = text[range_match.end():]

    # Сначала ищем проценты
    percent_bonus = 0
    for m in re.findall(r'([+-]?\d+)%', after):
        percent_bonus += int(m)

    # Убираем проценты
    after_no_pct = re.sub(r'[+-]?\d+%', '', after)

    # Ищем плоские бонусы
    flat_bonus = 0
    for m in re.findall(r'([+-]\d+)', after_no_pct):
        flat_bonus += int(m)

    return min_val, max_val, flat_bonus, percent_bonus


def do_roll(min_val: int, max_val: int, flat: int = 0, pct: int = 0):
    """Бросает кубик и применяет модификаторы. Возвращает (база, итог)."""
    base = random.randint(min_val, max_val)
    result = base + flat
    if pct != 0:
        result = round(result * (1 + pct / 100))
    return base, result


def fmt_mod(flat, pct):
    """Форматирует модификаторы для отображения."""
    parts = []
    if flat > 0:
        parts.append(f"+{flat}")
    elif flat < 0:
        parts.append(str(flat))
    if pct > 0:
        parts.append(f"+{pct}%")
    elif pct < 0:
        parts.append(f"{pct}%")
    return " ".join(parts)


def build_result_text(min_val, max_val, flat, pct, base, result):
    """Формирует текст результата (HTML)."""
    bar_len = 10
    if max_val != min_val:
        pos = int((base - min_val) / (max_val - min_val) * bar_len)
    else:
        pos = bar_len // 2
    bar = "░" * pos + "▓" + "░" * (bar_len - pos)

    lines = [f"🎲 <b>Бросок [{min_val}–{max_val}]</b>\n"]
    lines.append(f"<code>[{bar}]</code>")
    lines.append(f"Базовый бросок: <code>{base}</code>")

    if flat or pct:
        lines.append("\n<b>Модификаторы:</b>")
        if flat > 0:
            lines.append(f"  ➕ Плоский бонус: <code>+{flat}</code>")
        elif flat < 0:
            lines.append(f"  ➖ Штраф: <code>{flat}</code>")
        if pct > 0:
            lines.append(f"  📈 Процент: <code>+{pct}%</code>")
        elif pct < 0:
            lines.append(f"  📉 Процент: <code>{pct}%</code>")
        lines.append(f"\n⚔️ <b>Итого: <code>{result}</code></b>")
    else:
        lines.append(f"\n⚔️ <b>Результат: <code>{result}</code></b>")

    return "\n".join(lines)


# ─── ХЕНДЛЕРЫ ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>RPG Dice Bot</b> — бросок костей для RP-игр\n\n"
        "<b>Одиночный бросок:</b>\n"
        "<code>/roll 3-5</code> — бросок в диапазоне 3–5\n"
        "<code>/roll 5-10 +2</code> — бросок + плоский бонус\n"
        "<code>/roll 3-8 +15%</code> — бросок + процент\n"
        "<code>/roll 5-12 +3 +20%</code> — оба бонуса\n"
        "<code>/roll 3-5 -1 -10%</code> — штрафы\n\n"
        "<b>Несколько бросков сразу:</b>\n"
        "<code>/multiroll 3-5 3-5 3-5</code> — 3 броска\n"
        "<code>/multiroll 3-5 x3</code> — то же самое\n"
        "<code>/multiroll 3-5 -1 x3</code> — 3 броска со штрафом\n"
        "<code>/multiroll 3-5 | 4-8 +2 | 2-6</code> — разные диапазоны\n\n"
        "<i>Удачи в бою, Либраторий! ⚔️</i>"
    )
    await update.message.reply_text(text, parse_mode='HTML')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parsed = parse_roll(text)

    if not parsed:
        await update.message.reply_text(
            "❌ Неверный формат.\n\n"
            "Пример: <code>/roll 3-5</code> или <code>/roll 5-10 +2 +15%</code>",
            parse_mode='HTML'
        )
        return

    min_val, max_val, flat, pct = parsed
    base, result = do_roll(min_val, max_val, flat, pct)
    msg = build_result_text(min_val, max_val, flat, pct, base, result)

    await update.message.reply_text(msg, parse_mode='HTML')


async def cmd_multiroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Несколько бросков за раз."""
    text = update.message.text
    text = re.sub(r'^/\w+\s*', '', text).strip()

    if not text:
        await update.message.reply_text(
            "❌ Укажи диапазоны.\n\n"
            "Примеры:\n"
            "<code>/multiroll 3-5 3-5 3-5</code>\n"
            "<code>/multiroll 3-5 x3</code>\n"
            "<code>/multiroll 3-5 -1 x3</code>\n"
            "<code>/multiroll 3-5 | 4-8 +2 | 2-6 +10%</code>",
            parse_mode='HTML'
        )
        return

    parts = split_parts(text)

    if not parts:
        await update.message.reply_text("❌ Не удалось распознать диапазоны.")
        return

    msg = build_multiroll(parts)
    await update.message.reply_text(msg, parse_mode='HTML')


def split_parts(text):
    """Разбивает текст на отдельные броски."""
    repeat_match = re.match(r'^(.+?)\s+[xх×](\d+)$', text, re.IGNORECASE)
    if repeat_match:
        base_part = repeat_match.group(1).strip()
        count = min(int(repeat_match.group(2)), 10)
        return [base_part] * count

    if '|' in text:
        return [p.strip() for p in text.split('|') if p.strip()]

    parts = re.split(r'(?<=[\d%])\s+(?=\d+\s*[-–]\s*\d+)', text)
    return [p.strip() for p in parts if p.strip()]


def build_multiroll(parts):
    """Строит текст для мультиролла."""
    lines = ["🎲 <b>Множественный бросок</b>\n"]
    total = 0

    for i, part in enumerate(parts[:10], 1):
        parsed = parse_roll(part)
        if not parsed:
            lines.append(f"<b>{i}. Бросок</b> — ❌ неверный формат: <code>{part}</code>")
            continue

        min_val, max_val, flat, pct = parsed
        base, result = do_roll(min_val, max_val, flat, pct)
        total += result

        mods = ""
        if flat or pct:
            mods = f" ({fmt_mod(flat, pct)})"

        lines.append(f"<b>{i}. [{min_val}–{max_val}]{mods}</b> → <code>{base}</code> ⚔️ <code>{result}</code>")

    if len(parts) > 1:
        lines.append(f"\n📊 <b>Сумма всех бросков: <code>{total}</code></b>")

    return "\n".join(lines)


# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    if not TOKEN or TOKEN == "ВАШ_ТОКЕН_СЮДА":
        print("⚠️  Вставь токен бота в переменную TOKEN (строка 20)!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("roll", cmd_roll))
    app.add_handler(CommandHandler("multiroll", cmd_multiroll))

    print("🎲 RPG Dice Bot запущен! Нажми Ctrl+C чтобы остановить.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
