"""
🎲 RPG Dice Bot — для RP-игр в стиле Library of Ruina / DnD
Автор: Claude

Установка:
    pip install python-telegram-bot

Запуск:
    1. Вставь свой токен в TOKEN ниже
    2. python rpg_dice_bot.py
"""

import re
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
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
    # Убираем команду (/roll) если есть
    text = re.sub(r'^/\w+\s*', '', text).strip()

    # Ищем диапазон
    range_match = re.search(r'(\d+)\s*[-–]\s*(\d+)', text)
    if not range_match:
        return None

    min_val = int(range_match.group(1))
    max_val = int(range_match.group(2))

    if min_val > max_val:
        min_val, max_val = max_val, min_val

    # Текст после диапазона
    after = text[range_match.end():]

    # Сначала ищем проценты (чтобы не спутать с плоским бонусом)
    percent_bonus = 0
    for m in re.findall(r'([+-]?\d+)%', after):
        percent_bonus += int(m)

    # Убираем проценты из строки
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


def build_result_text(min_val, max_val, flat, pct, base, result):
    """Формирует красивый текст результата."""
    lines = [f"🎲 *Бросок \\[{min_val}–{max_val}\\]*\n"]

    # Визуальная шкала
    bar_len = 10
    if max_val != min_val:
        pos = int((base - min_val) / (max_val - min_val) * bar_len)
    else:
        pos = bar_len // 2
    bar = "░" * pos + "▓" + "░" * (bar_len - pos)
    lines.append(f"`[{bar}]`")
    lines.append(f"Базовый бросок: **{base}**")

    if flat or pct:
        lines.append("\n*Модификаторы:*")
        if flat > 0:
            lines.append(f"  ➕ Плоский бонус: `+{flat}`")
        elif flat < 0:
            lines.append(f"  ➖ Штраф: `{flat}`")
        if pct > 0:
            lines.append(f"  📈 Процент: `+{pct}%`")
        elif pct < 0:
            lines.append(f"  📉 Процент: `{pct}%`")
        lines.append(f"\n⚔️ *Итого: `{result}`*")
    else:
        lines.append(f"\n⚔️ *Результат: `{result}`*")

    return "\n".join(lines)


def reroll_keyboard(min_val, max_val, flat, pct):
    """Кнопка повторного броска."""
    data = f"rr:{min_val}:{max_val}:{flat}:{pct}"
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Бросить снова", callback_data=data)
    ]])


# ─── ХЕНДЛЕРЫ ─────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *RPG Dice Bot* — бросок костей для RP-игр\n\n"
        "*Одиночный бросок:*\n"
        "`/roll 3-5` — бросок в диапазоне 3–5\n"
        "`/roll 5-10 +2` — бросок \\+ плоский бонус\n"
        "`/roll 3-8 +15%` — бросок \\+ процент\n"
        "`/roll 5-12 +3 +20%` — оба бонуса\n\n"
        "*Несколько бросков сразу:*\n"
        "`/multiroll 3-5 3-5 3-5` — 3 броска\n"
        "`/multiroll 3-5 x3` — то же самое\n"
        "`/multiroll 3-5 \\| 4-8 \\+2 \\| 2-6` — разные диапазоны\n\n"
        "Или просто напиши диапазон: `5-10`\n\n"
        "_Удачи в бою, Либраторий\\!_ ⚔️"
    )
    await update.message.reply_text(text, parse_mode='MarkdownV2')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_multiroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Несколько бросков за раз. Пример: /multiroll 3-5 3-5 3-5 или /multiroll 3-5 x3"""
    text = update.message.text
    text = re.sub(r'^/\w+\s*', '', text).strip()

    if not text:
        await update.message.reply_text(
            "❌ Укажи диапазоны\\.\n\n"
            "Примеры:\n"
            "`/multiroll 3-5 3-5 3-5`\n"
            "`/multiroll 3-5 x3`\n"
            "`/multiroll 3-5 \\| 4-8 \\| 2-6 \\+10%`",
            parse_mode='MarkdownV2'
        )
        return

    # Поддержка формата "3-5 x3"
    repeat_match = re.match(r'^(.+?)\s+[xх×](\d+)$', text, re.IGNORECASE)
    if repeat_match:
        base_part = repeat_match.group(1).strip()
        count = min(int(repeat_match.group(2)), 10)
        parts = [base_part] * count
    else:
        # Разделяем по | или по пробелам между диапазонами
        if '|' in text:
            parts = [p.strip() for p in text.split('|') if p.strip()]
        else:
            # Разбиваем по каждому диапазону "число-число"
            parts = re.split(r'(?<=[\d%])\s+(?=\d+\s*[-–]\s*\d+)', text)
            parts = [p.strip() for p in parts if p.strip()]

    if not parts:
        await update.message.reply_text("❌ Не удалось распознать диапазоны\\.", parse_mode='MarkdownV2')
        return

    lines = ["🎲 *Множественный бросок*\n"]
    total = 0

    for i, part in enumerate(parts[:10], 1):
        parsed = parse_roll(part)
        if not parsed:
            lines.append(f"*{i}\\. Бросок* — ❌ неверный формат: `{part}`")
            continue
        min_val, max_val, flat, pct = parsed
        base, result = do_roll(min_val, max_val, flat, pct)
        total += result

        mods = ""
        if flat or pct:
            mod_parts = []
            if flat:
                mod_parts.append(f"\\+{flat}" if flat > 0 else str(flat))
            if pct:
                mod_parts.append(f"\\+{pct}%" if pct > 0 else f"{pct}%")
            mods = f" \\({', '.join(mod_parts)}\\)"

        lines.append(f"*{i}\\. \\[{min_val}–{max_val}\\]{mods}* → `{base}` ⚔️ `{result}`")

    if len(parts) > 1:
        lines.append(f"\n📊 *Сумма всех бросков: `{total}`*")

    # Кнопка повторить — сохраняем исходный текст
    raw = update.message.text
    short_data = raw[:60]
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Бросить снова", callback_data=f"mr:{short_data}")
    ]])

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode='MarkdownV2',
        reply_markup=keyboard
    )


async def on_multiroll_reroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Повторный мультибросок."""
    query = update.callback_query
    await query.answer()

    original = query.data[3:]  # убираем "mr:"
    fake_update_text = original

    text = re.sub(r'^/\w+\s*', '', fake_update_text).strip()
    repeat_match = re.match(r'^(.+?)\s+[xх×](\d+)$', text, re.IGNORECASE)
    if repeat_match:
        base_part = repeat_match.group(1).strip()
        count = min(int(repeat_match.group(2)), 10)
        parts = [base_part] * count
    else:
        if '|' in text:
            parts = [p.strip() for p in text.split('|') if p.strip()]
        else:
            parts = re.split(r'(?<=[\d%])\s+(?=\d+\s*[-–]\s*\d+)', text)
            parts = [p.strip() for p in parts if p.strip()]

    lines = ["🎲 *Множественный бросок*\n"]
    total = 0

    for i, part in enumerate(parts[:10], 1):
        parsed = parse_roll(part)
        if not parsed:
            continue
        min_val, max_val, flat, pct = parsed
        base, result = do_roll(min_val, max_val, flat, pct)
        total += result

        mods = ""
        if flat or pct:
            mod_parts = []
            if flat:
                mod_parts.append(f"\\+{flat}" if flat > 0 else str(flat))
            if pct:
                mod_parts.append(f"\\+{pct}%" if pct > 0 else f"{pct}%")
            mods = f" \\({', '.join(mod_parts)}\\)"

        lines.append(f"*{i}\\. \\[{min_val}–{max_val}\\]{mods}* → `{base}` ⚔️ `{result}`")

    if len(parts) > 1:
        lines.append(f"\n📊 *Сумма всех бросков: `{total}`*")

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Бросить снова", callback_data=query.data)
    ]])

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode='MarkdownV2',
        reply_markup=keyboard
    )


async def cmd_roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parsed = parse_roll(text)

    if not parsed:
        await update.message.reply_text(
            "❌ Неверный формат\\.\n\n"
            "Пример: `/roll 3-5` или `/roll 5-10 +2 +15%`",
            parse_mode='MarkdownV2'
        )
        return

    min_val, max_val, flat, pct = parsed
    base, result = do_roll(min_val, max_val, flat, pct)
    msg = build_result_text(min_val, max_val, flat, pct, base, result)

    await update.message.reply_text(
        msg,
        parse_mode='MarkdownV2',
        reply_markup=reroll_keyboard(min_val, max_val, flat, pct)
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает свободный текст (например, просто '3-5')."""
    text = update.message.text
    parsed = parse_roll(text)

    if parsed:
        min_val, max_val, flat, pct = parsed
        base, result = do_roll(min_val, max_val, flat, pct)
        msg = build_result_text(min_val, max_val, flat, pct, base, result)

        await update.message.reply_text(
            msg,
            parse_mode='MarkdownV2',
            reply_markup=reroll_keyboard(min_val, max_val, flat, pct)
        )


async def on_reroll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатие кнопки 'Бросить снова'."""
    query = update.callback_query
    await query.answer()

    try:
        _, min_s, max_s, flat_s, pct_s = query.data.split(":")
        min_val, max_val = int(min_s), int(max_s)
        flat, pct = int(flat_s), int(pct_s)
    except Exception:
        await query.edit_message_text("❌ Ошибка данных\\.", parse_mode='MarkdownV2')
        return

    base, result = do_roll(min_val, max_val, flat, pct)
    msg = build_result_text(min_val, max_val, flat, pct, base, result)

    await query.edit_message_text(
        msg,
        parse_mode='MarkdownV2',
        reply_markup=reroll_keyboard(min_val, max_val, flat, pct)
    )


# ─── ЗАПУСК ───────────────────────────────────────────────────────────────────

def main():
    if not TOKEN or TOKEN == "ВАШ_ТОКЕН_СЮДА":
        print("⚠️  Вставь токен бота в переменную TOKEN (строка 22)!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("roll", cmd_roll))
    app.add_handler(CommandHandler("multiroll", cmd_multiroll))
    app.add_handler(CallbackQueryHandler(on_reroll, pattern=r'^rr:'))
    app.add_handler(CallbackQueryHandler(on_multiroll_reroll, pattern=r'^mr:'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("🎲 RPG Dice Bot запущен! Нажми Ctrl+C чтобы остановить.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
