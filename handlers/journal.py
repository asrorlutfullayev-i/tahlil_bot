import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import add_journal_entry, get_journal_entries_today
from keyboards import journal_menu_keyboard, main_menu_keyboard, back_keyboard
from ai_service import get_mentor

logger = logging.getLogger(__name__)

async def journal_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show journal menu when user clicks 📝 Kundalik."""
    context.user_data['state'] = 'idle'
    await update.message.reply_text(
        '📝 *Kundalik*\n\nNima qilmoqchisiz?',
        parse_mode='Markdown',
        reply_markup=journal_menu_keyboard()
    )

async def journal_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start new journal entry — ask for activities. (callback query handler)"""
    query = update.callback_query
    context.user_data['state'] = 'journal_activity'
    context.user_data['journal_data'] = {}
    await query.edit_message_text(
        '📋 *Bugun nima ish qildingiz?*\n\n'
        'Qilgan ishlaringizni yozing. Masalan:\n'
        '_"3 soat React o\'rgandim, 2 soat loyiha ustida ishladim"_',
        parse_mode='Markdown'
    )

async def journal_receive_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive activity text and ask for learnings."""
    text = update.message.text
    context.user_data['journal_data'] = context.user_data.get('journal_data', {})
    context.user_data['journal_data']['activity'] = text
    context.user_data['state'] = 'journal_learning'
    
    user_id = update.effective_user.id
    await add_journal_entry(user_id, 'activity', text)
    
    await update.message.reply_text(
        '✅ Yozildi!\n\n'
        '📚 *Bugun nima o\'rgandingiz?*\n\n'
        'O\'rgangan narsalaringizni yozing. Masalan:\n'
        '_"React hooks ni tushundim, useEffect qanday ishlashini o\'rgandim"_',
        parse_mode='Markdown'
    )

async def journal_receive_learning(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive learning text, save, get AI feedback."""
    text = update.message.text
    user = update.effective_user
    journal_data = context.user_data.get('journal_data', {})
    activities = journal_data.get('activity', '')
    
    # Save learning entry
    await add_journal_entry(user.id, 'learning', text)
    
    # Reset state
    context.user_data['state'] = 'idle'
    context.user_data.pop('journal_data', None)
    
    # Send "thinking" message
    thinking_msg = await update.message.reply_text('🧠 Mentor tahlil qilmoqda...')
    
    try:
        # Get AI feedback
        mentor = get_mentor()
        feedback = await mentor.get_daily_feedback(
            activities=activities,
            learnings=text,
            user_name=user.first_name or ''
        )
        
        # Update AI feedback in the last entry
        result_text = (
            f'✅ *Kundalik saqlandi!*\n\n'
            f'👨🏫 *Mentor fikri:*\n\n{feedback}'
        )
        await thinking_msg.edit_text(result_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f'AI feedback error: {e}')
        await thinking_msg.edit_text(
            '✅ *Kundalik saqlandi!*\n\n'
            '⚠️ Mentor hozir band. Lekin yozuvingiz saqlandi!',
            parse_mode='Markdown'
        )

async def journal_show_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show today's journal entries. (callback query handler)"""
    query = update.callback_query
    user_id = update.effective_user.id
    entries = await get_journal_entries_today(user_id)
    
    if not entries:
        await query.edit_message_text(
            '📭 *Bugun hali yozuv yo\'q*\n\n'
            'Yangi yozuv boshlash uchun "✍️ Yangi yozuv" tugmasini bosing.',
            parse_mode='Markdown',
            reply_markup=journal_menu_keyboard()
        )
        return
    
    entries_text = ''
    for e in entries:
        type_icon = '📋' if e['entry_type'] == 'activity' else '📚' if e['entry_type'] == 'learning' else '📝'
        type_name = 'Faoliyat' if e['entry_type'] == 'activity' else 'O\'rganish' if e['entry_type'] == 'learning' else 'Eslatma'
        time_str = e['created_at'][11:16] if len(e['created_at']) > 16 else ''
        entries_text += f'{type_icon} *{type_name}* ({time_str})\n{e["content"]}\n\n'
    
    await query.edit_message_text(
        f'📅 *Bugungi yozuvlar ({len(entries)} ta):*\n\n{entries_text}',
        parse_mode='Markdown',
        reply_markup=journal_menu_keyboard()
    )
