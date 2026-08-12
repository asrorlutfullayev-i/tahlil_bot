import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import get_journal_entries_today, get_journal_entries_period
from keyboards import analysis_menu_keyboard, main_menu_keyboard, back_keyboard
from ai_service import get_mentor

logger = logging.getLogger(__name__)

async def analysis_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show analysis menu."""
    context.user_data['state'] = 'idle'
    await update.message.reply_text(
        '📊 *Tahlil*\n\nQaysi davrni tahlil qilmoqchisiz?',
        parse_mode='Markdown',
        reply_markup=analysis_menu_keyboard()
    )

async def analysis_daily(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze today's entries (callback query)."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.edit_message_text('🧠 *Tahlil qilinmoqda...*', parse_mode='Markdown')
    
    entries = await get_journal_entries_today(user_id)
    mentor = get_mentor()
    analysis = await mentor.analyze_daily(entries)
    
    await query.edit_message_text(
        f'📅 *Bugungi tahlil:*\n\n{analysis}',
        parse_mode='Markdown',
        reply_markup=analysis_menu_keyboard()
    )

async def analysis_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze this week's entries (callback query)."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.edit_message_text('🧠 *Haftalik tahlil qilinmoqda...*', parse_mode='Markdown')
    
    entries = await get_journal_entries_period(user_id, days=7)
    mentor = get_mentor()
    analysis = await mentor.analyze_period(entries, 'hafta')
    
    await query.edit_message_text(
        f'📆 *Haftalik tahlil:*\n\n{analysis}',
        parse_mode='Markdown',
        reply_markup=analysis_menu_keyboard()
    )

async def analysis_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze this month's entries (callback query)."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    await query.edit_message_text('🧠 *Oylik tahlil qilinmoqda...*', parse_mode='Markdown')
    
    entries = await get_journal_entries_period(user_id, days=30)
    mentor = get_mentor()
    analysis = await mentor.analyze_period(entries, 'oy')
    
    await query.edit_message_text(
        f'📊 *Oylik tahlil:*\n\n{analysis}',
        parse_mode='Markdown',
        reply_markup=analysis_menu_keyboard()
    )
