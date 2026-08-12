import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from database import add_reminder, get_user_reminders, delete_reminder, get_pending_reminders, mark_reminder_sent
from keyboards import reminder_list_keyboard, main_menu_keyboard

logger = logging.getLogger(__name__)

async def reminders_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show reminders menu."""
    context.user_data['state'] = 'idle'
    user_id = update.effective_user.id
    reminders = await get_user_reminders(user_id)
    
    if reminders:
        text = f'⏰ *Eslatmalar ({len(reminders)} ta):*'
    else:
        text = '⏰ *Eslatmalar*\n\nHozircha eslatmalar yo\'q.'
    
    await update.message.reply_text(
        text,
        parse_mode='Markdown',
        reply_markup=reminder_list_keyboard(reminders)
    )

async def reminder_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start adding reminder (callback query)."""
    query = update.callback_query
    context.user_data['state'] = 'reminder_text'
    await query.edit_message_text(
        '📝 *Yangi eslatma*\n\nNimani eslatib turish kerak?',
        parse_mode='Markdown'
    )

async def reminder_receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive reminder text, ask for time."""
    text = update.message.text
    context.user_data['reminder_text'] = text
    context.user_data['state'] = 'reminder_time'
    await update.message.reply_text(
        f'📌 Eslatma: *{text}*\n\n'
        '⏰ Qachon eslataman?\n\n'
        'Format: `YYYY-MM-DD HH:MM`\n'
        'Masalan: `2025-08-15 09:00`\n\n'
        'Yoki soat bilan yozing:\n'
        '`30m` — 30 minutdan keyin\n'
        '`2h` — 2 soatdan keyin\n'
        '`1d` — 1 kundan keyin',
        parse_mode='Markdown'
    )

async def reminder_receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive reminder time and save."""
    time_text = update.message.text.strip()
    user_id = update.effective_user.id
    reminder_text = context.user_data.get('reminder_text', 'Eslatma')
    
    try:
        # Parse relative time
        if time_text.endswith('m'):
            minutes = int(time_text[:-1])
            remind_at = datetime.now() + timedelta(minutes=minutes)
        elif time_text.endswith('h'):
            hours = int(time_text[:-1])
            remind_at = datetime.now() + timedelta(hours=hours)
        elif time_text.endswith('d'):
            days = int(time_text[:-1])
            remind_at = datetime.now() + timedelta(days=days)
        else:
            # Try parsing as datetime
            remind_at = datetime.strptime(time_text, '%Y-%m-%d %H:%M')
        
        remind_at_str = remind_at.strftime('%Y-%m-%d %H:%M')
        await add_reminder(user_id, reminder_text, remind_at_str)
        
        context.user_data['state'] = 'idle'
        context.user_data.pop('reminder_text', None)
        
        await update.message.reply_text(
            f'✅ *Eslatma o\'rnatildi!*\n\n'
            f'📌 {reminder_text}\n'
            f'⏰ {remind_at_str}',
            parse_mode='Markdown',
            reply_markup=main_menu_keyboard()
        )
    except (ValueError, OverflowError):
        await update.message.reply_text(
            '❌ Vaqt formatini tushunmadim.\n\n'
            'Masalan: `2025-08-15 09:00` yoki `30m` yoki `2h` yoki `1d`',
            parse_mode='Markdown'
        )

async def reminder_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a reminder (callback query)."""
    query = update.callback_query
    reminder_id = int(query.data.split('_')[-1])
    user_id = update.effective_user.id
    
    await delete_reminder(reminder_id)
    await query.answer('🗑 Eslatma o\'chirildi!')
    
    # Refresh list
    reminders = await get_user_reminders(user_id)
    if reminders:
        await query.edit_message_text(
            f'⏰ *Eslatmalar ({len(reminders)} ta):*',
            parse_mode='Markdown',
            reply_markup=reminder_list_keyboard(reminders)
        )
    else:
        await query.edit_message_text(
            '⏰ *Eslatmalar yo\'q*',
            parse_mode='Markdown',
            reply_markup=reminder_list_keyboard([])
        )

async def check_reminders_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job queue callback — check and send pending reminders."""
    try:
        reminders = await get_pending_reminders()
        for r in reminders:
            try:
                await context.bot.send_message(
                    chat_id=r['user_id'],
                    text=f'🔔 *Eslatma!*\n\n📌 {r["text"]}',
                    parse_mode='Markdown'
                )
                await mark_reminder_sent(r['id'])
            except Exception as e:
                logger.error(f'Failed to send reminder {r["id"]}: {e}')
    except Exception as e:
        logger.error(f'Reminder check error: {e}')
