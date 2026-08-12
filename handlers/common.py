import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    add_user,
    get_user,
    get_stats,
    get_pending_tasks_count,
    add_journal_entry,
    add_task,
    add_reminder,
)
from keyboards import main_menu_keyboard, back_keyboard
from ai_service import get_mentor
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ==================== COMMANDS ====================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command. Register user and show welcome."""
    user = update.effective_user
    await add_user(user.id, user.username or '', user.first_name or '')
    context.user_data['state'] = 'idle'
    
    welcome_text = (
        f"🎯 *Assalomu alaykum, {user.first_name}!*\n\n"
        f"Men sizning shaxsiy aqlli mentor-botingizman — *Ustoz* 🧠\n\n"
        f"💡 *Menga istalgan narsani yozishingiz mumkin:*\n"
        f"• Shunchaki suhbatlashish va savol berish\n"
        f"• *\"Bugun 3 soat React o'rgandim\"* (avtomatik kundalikka yoziladi)\n"
        f"• *\"Ertaga majlis bor eslatib qo'y\"* (avtomatik eslatma saqlanadi)\n"
        f"• *\"Vazifa: Loyihani tugatish\"* (avtomatik vazifaga qo'shiladi)\n\n"
        f"Quyidagi menyulardan ham foydalanishingiz mumkin 👇"
    )
    await update.message.reply_text(
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "📖 *Yordam*\n\n"
        "🔹 /start — Botni qayta ishga tushirish\n"
        "🔹 /menu — Bosh menyuni ko'rsatish\n"
        "🔹 /help — Ushbu yordam\n\n"
        "*Smart AI Rejim:*\n"
        "Menga shunchaki matn yozing — men uning niyatini avtomatik tushunaman (vazifa, kundalik, eslatma yoki suhbat).\n"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show main menu."""
    context.user_data['state'] = 'idle'
    await update.message.reply_text(
        '🏠 *Bosh menyu*\n\nQuyidagi tugmalardan birini tanlang:',
        parse_mode='Markdown',
        reply_markup=main_menu_keyboard()
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics."""
    user_id = update.effective_user.id
    stats = await get_stats(user_id)
    pending = await get_pending_tasks_count(user_id)
    
    stats_text = (
        f"📈 *Sizning statistikangiz*\n\n"
        f"📝 Jami yozuvlar: *{stats.get('total_entries', 0)}*\n"
        f"📅 Bugungi yozuvlar: *{stats.get('entries_today', 0)}*\n"
        f"📆 Shu haftada: *{stats.get('entries_this_week', 0)}*\n"
        f"🔥 Ketma-ket kunlar: *{stats.get('streak_days', 0)}* kun\n\n"
        f"✅ Jami vazifalar: *{stats.get('total_tasks', 0)}*\n"
        f"✔️ Bajarilgan: *{stats.get('completed_tasks', 0)}*\n"
        f"⏳ Kutilmoqda: *{pending}*\n"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown', reply_markup=main_menu_keyboard())

# ==================== ROUTERS ====================

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Smart message router with AI intent parser."""
    text = update.message.text
    user = update.effective_user
    state = context.user_data.get('state', 'idle')
    
    # Import handlers
    from handlers.journal import journal_start, journal_receive_activity, journal_receive_learning
    from handlers.tasks import tasks_start, task_receive_title, task_receive_deadline
    from handlers.analysis import analysis_start
    from handlers.chat import chat_start, chat_handle_message
    from handlers.reminders import reminders_start, reminder_receive_text, reminder_receive_time
    
    # Menu buttons
    menu_routes = {
        '📝 Kundalik': journal_start,
        '✅ Vazifalar': tasks_start,
        '📊 Tahlil': analysis_start,
        '💬 Suhbat': chat_start,
        '⏰ Eslatmalar': reminders_start,
        '📈 Statistika': show_stats,
    }
    
    if text in menu_routes:
        context.user_data['state'] = 'idle'
        await menu_routes[text](update, context)
        return
    
    # Specific input states
    state_handlers = {
        'journal_activity': journal_receive_activity,
        'journal_learning': journal_receive_learning,
        'task_title': task_receive_title,
        'task_deadline': task_receive_deadline,
        'reminder_text': reminder_receive_text,
        'reminder_time': reminder_receive_time,
    }
    
    if state in state_handlers:
        await state_handlers[state](update, context)
        return

    # UNIVERSAL SMART AI ROUTER (Handles any free text message!)
    thinking_msg = await update.message.reply_text('🧠 Ustoz o\'ylamoqda...')
    
    try:
        mentor = get_mentor()
        result = await mentor.parse_and_respond(user_message=text, user_name=user.first_name or '')
        
        intent = result.get('intent', 'chat')
        reply = result.get('reply', '')
        data = result.get('data', {})
        
        if intent == 'journal':
            entry_type = data.get('entry_type', 'activity')
            await add_journal_entry(user.id, entry_type, text, ai_feedback=reply)
            response_text = f"📝 *Kundalikka saqlandi!*\n\n👨‍🏫 *Mentor fikri:*\n{reply}"
        
        elif intent == 'task':
            task_title = data.get('task_title', text)
            await add_task(user.id, task_title)
            response_text = f"✅ *Vazifangizga qo'shildi:*\n📌 {task_title}\n\n👨‍🏫 *Mentor fikri:*\n{reply}"
            
        elif intent == 'reminder':
            rem_text = data.get('reminder_text', text)
            time_str = data.get('reminder_time', '30m')
            
            # Default to 30 mins if unable to parse relative time
            remind_at = datetime.now() + timedelta(minutes=30)
            if time_str.endswith('m'):
                remind_at = datetime.now() + timedelta(minutes=int(time_str[:-1]))
            elif time_str.endswith('h'):
                remind_at = datetime.now() + timedelta(hours=int(time_str[:-1]))
            elif time_str.endswith('d'):
                remind_at = datetime.now() + timedelta(days=int(time_str[:-1]))
                
            remind_at_formatted = remind_at.strftime('%Y-%m-%d %H:%M')
            await add_reminder(user.id, rem_text, remind_at_formatted)
            response_text = f"⏰ *Eslatma o'rnatildi!*\n📌 {rem_text}\n📅 {remind_at_formatted}\n\n👨‍🏫 *Mentor fikri:*\n{reply}"
            
        else: # chat
            response_text = f"👨‍🏫 *Ustoz:*\n\n{reply}"
            
        await thinking_msg.edit_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Smart router error: {e}")
        await thinking_msg.edit_text(f"👨‍🏫 *Ustoz:*\n\nSizni tushundim. Menga istalgan savolingizni berishingiz mumkin!", parse_mode='Markdown')


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route callback queries."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    from handlers.journal import journal_new, journal_show_today
    from handlers.tasks import task_add_start, task_show_list, task_show_done, task_toggle_status, task_delete, tasks_menu_show
    from handlers.analysis import analysis_daily, analysis_weekly, analysis_monthly
    from handlers.chat import chat_exit
    from handlers.reminders import reminder_add_start, reminder_delete
    
    exact_routes = {
        'journal_new': journal_new,
        'journal_today': journal_show_today,
        'task_add': task_add_start,
        'task_list': task_show_list,
        'task_done_list': task_show_done,
        'tasks_menu': tasks_menu_show,
        'analysis_daily': analysis_daily,
        'analysis_weekly': analysis_weekly,
        'analysis_monthly': analysis_monthly,
        'chat_exit': chat_exit,
        'reminder_add': reminder_add_start,
        'skip_deadline': task_receive_deadline_skip,
        'back_menu': back_to_menu,
    }
    
    if data in exact_routes:
        await exact_routes[data](update, context)
        return
    
    if data.startswith('task_toggle_'):
        await task_toggle_status(update, context)
    elif data.startswith('task_del_'):
        await task_delete(update, context)
    elif data.startswith('reminder_del_'):
        await reminder_delete(update, context)


async def task_receive_deadline_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from handlers.tasks import task_save_without_deadline
    await task_save_without_deadline(update, context)


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    context.user_data['state'] = 'idle'
    await query.edit_message_text('🏠 *Bosh menyu*\nQuyidagi tugmalardan birini tanlang 👇', parse_mode='Markdown')
