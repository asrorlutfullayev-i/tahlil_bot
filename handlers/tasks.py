import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import add_task, get_tasks, update_task_status, delete_task
from keyboards import tasks_menu_keyboard, task_list_keyboard, main_menu_keyboard, skip_keyboard

logger = logging.getLogger(__name__)

async def tasks_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks menu when user clicks ✅ Vazifalar."""
    context.user_data['state'] = 'idle'
    await update.message.reply_text(
        '✅ *Vazifalar*\n\nNima qilmoqchisiz?',
        parse_mode='Markdown',
        reply_markup=tasks_menu_keyboard()
    )

async def tasks_menu_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show tasks menu from callback query."""
    query = update.callback_query
    context.user_data['state'] = 'idle'
    await query.edit_message_text(
        '✅ *Vazifalar*\n\nNima qilmoqchisiz?',
        parse_mode='Markdown',
        reply_markup=tasks_menu_keyboard()
    )

async def task_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start adding a new task (callback query)."""
    query = update.callback_query
    context.user_data['state'] = 'task_title'
    await query.edit_message_text(
        '📝 *Yangi vazifa*\n\nVazifa nomini yozing:',
        parse_mode='Markdown'
    )

async def task_receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive task title, ask for deadline."""
    title = update.message.text
    context.user_data['task_title'] = title
    context.user_data['state'] = 'task_deadline'
    await update.message.reply_text(
        f'📌 Vazifa: *{title}*\n\n'
        '📅 Muddat qo\'ying (masalan: 2025-12-31)\n'
        'Yoki quyidagi tugmani bosib o\'tkazib yuboring:',
        parse_mode='Markdown',
        reply_markup=skip_keyboard('skip_deadline')
    )

async def task_receive_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receive deadline and save task."""
    deadline = update.message.text
    title = context.user_data.get('task_title', 'Nomsiz vazifa')
    user_id = update.effective_user.id
    
    await add_task(user_id, title, deadline)
    context.user_data['state'] = 'idle'
    context.user_data.pop('task_title', None)
    
    await update.message.reply_text(
        f'✅ Vazifa qo\'shildi!\n\n'
        f'📌 *{title}*\n'
        f'📅 Muddat: {deadline}',
        parse_mode='Markdown',
        reply_markup=tasks_menu_keyboard()
    )

async def task_save_without_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save task without deadline (skip button pressed)."""
    query = update.callback_query
    title = context.user_data.get('task_title', 'Nomsiz vazifa')
    user_id = update.effective_user.id
    
    await add_task(user_id, title)
    context.user_data['state'] = 'idle'
    context.user_data.pop('task_title', None)
    
    await query.edit_message_text(
        f'✅ Vazifa qo\'shildi!\n\n'
        f'📌 *{title}*\n'
        f'📅 Muddat: belgilanmagan',
        parse_mode='Markdown',
        reply_markup=tasks_menu_keyboard()
    )

async def task_show_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show pending tasks list (callback query)."""
    query = update.callback_query
    user_id = update.effective_user.id
    tasks = await get_tasks(user_id, status='pending')
    
    if not tasks:
        await query.edit_message_text(
            '📭 *Bajarilmagan vazifalar yo\'q*\n\nYangi vazifa qo\'shish uchun tugmani bosing.',
            parse_mode='Markdown',
            reply_markup=tasks_menu_keyboard()
        )
        return
    
    await query.edit_message_text(
        f'📋 *Vazifalar ({len(tasks)} ta):*\n\nBajarish uchun bosing ✅ | O\'chirish 🗑',
        parse_mode='Markdown',
        reply_markup=task_list_keyboard(tasks)
    )

async def task_show_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show completed tasks (callback query)."""
    query = update.callback_query
    user_id = update.effective_user.id
    tasks = await get_tasks(user_id, status='done')
    
    if not tasks:
        await query.edit_message_text(
            '📭 *Bajarilgan vazifalar yo\'q*',
            parse_mode='Markdown',
            reply_markup=tasks_menu_keyboard()
        )
        return
    
    await query.edit_message_text(
        f'✅ *Bajarilgan vazifalar ({len(tasks)} ta):*',
        parse_mode='Markdown',
        reply_markup=task_list_keyboard(tasks)
    )

async def task_toggle_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle task status between pending and done."""
    query = update.callback_query
    task_id = int(query.data.split('_')[-1])
    user_id = update.effective_user.id
    
    # Get current tasks to find this one
    all_tasks = await get_tasks(user_id)
    current_task = next((t for t in all_tasks if t['id'] == task_id), None)
    
    if current_task:
        new_status = 'done' if current_task['status'] == 'pending' else 'pending'
        await update_task_status(task_id, new_status)
        status_text = '✅ bajarildi' if new_status == 'done' else '⬜ qayta ochildi'
        await query.answer(f'Vazifa {status_text}!')
    
    # Refresh task list
    tasks = await get_tasks(user_id, status='pending')
    if tasks:
        await query.edit_message_text(
            f'📋 *Vazifalar ({len(tasks)} ta):*',
            parse_mode='Markdown',
            reply_markup=task_list_keyboard(tasks)
        )
    else:
        await query.edit_message_text(
            '🎉 *Barcha vazifalar bajarildi!*',
            parse_mode='Markdown',
            reply_markup=tasks_menu_keyboard()
        )

async def task_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete a task."""
    query = update.callback_query
    task_id = int(query.data.split('_')[-1])
    user_id = update.effective_user.id
    
    await delete_task(task_id)
    await query.answer('🗑 Vazifa o\'chirildi!')
    
    # Refresh task list
    tasks = await get_tasks(user_id, status='pending')
    if tasks:
        await query.edit_message_text(
            f'📋 *Vazifalar ({len(tasks)} ta):*',
            parse_mode='Markdown',
            reply_markup=task_list_keyboard(tasks)
        )
    else:
        await query.edit_message_text(
            '📭 *Vazifalar yo\'q*',
            parse_mode='Markdown',
            reply_markup=tasks_menu_keyboard()
        )
