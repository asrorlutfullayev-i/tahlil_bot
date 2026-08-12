from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy menyu — har doim ko'rinadigan tugmalar"""
    keyboard = [
        ['📝 Kundalik', '✅ Vazifalar'],
        ['📊 Tahlil', '💬 Suhbat'],
        ['⏰ Eslatmalar', '📈 Statistika'],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def journal_menu_keyboard() -> InlineKeyboardMarkup:
    """Kundalik menyusi"""
    keyboard = [
        [InlineKeyboardButton('✍️ Yangi yozuv', callback_data='journal_new')],
        [InlineKeyboardButton('📖 Bugungi yozuvlar', callback_data='journal_today')],
        [InlineKeyboardButton('🏠 Bosh menyu', callback_data='back_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)


def tasks_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton('➕ Yangi vazifa', callback_data='task_add')],
        [InlineKeyboardButton('📋 Barcha vazifalar', callback_data='task_list')],
        [InlineKeyboardButton('✅ Bajarilganlar', callback_data='task_done_list')],
        [InlineKeyboardButton('🏠 Bosh menyu', callback_data='back_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)


def task_list_keyboard(tasks: list) -> InlineKeyboardMarkup:
    """Dynamic task list with toggle and delete buttons"""
    keyboard = []
    for task in tasks:
        status_icon = '✅' if task['status'] == 'done' else '⬜'
        keyboard.append([
            InlineKeyboardButton(f"{status_icon} {task['title']}", callback_data=f"task_toggle_{task['id']}"),
            InlineKeyboardButton('🗑', callback_data=f"task_del_{task['id']}"),
        ])
    keyboard.append([InlineKeyboardButton('➕ Yangi vazifa', callback_data='task_add')])
    keyboard.append([InlineKeyboardButton('◀️ Orqaga', callback_data='tasks_menu')])
    return InlineKeyboardMarkup(keyboard)


def analysis_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton('📅 Bugungi tahlil', callback_data='analysis_daily')],
        [InlineKeyboardButton('📆 Haftalik tahlil', callback_data='analysis_weekly')],
        [InlineKeyboardButton('📊 Oylik tahlil', callback_data='analysis_monthly')],
        [InlineKeyboardButton('🏠 Bosh menyu', callback_data='back_menu')],
    ]
    return InlineKeyboardMarkup(keyboard)


def reminder_list_keyboard(reminders: list) -> InlineKeyboardMarkup:
    keyboard = []
    for r in reminders:
        keyboard.append([
            InlineKeyboardButton(f"⏰ {r['text'][:30]} — {r['remind_at']}", callback_data=f"reminder_info_{r['id']}"),
            InlineKeyboardButton('🗑', callback_data=f"reminder_del_{r['id']}"),
        ])
    keyboard.append([InlineKeyboardButton('➕ Yangi eslatma', callback_data='reminder_add')])
    keyboard.append([InlineKeyboardButton('🏠 Bosh menyu', callback_data='back_menu')])
    return InlineKeyboardMarkup(keyboard)


def skip_keyboard(callback_data: str = 'skip') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('⏭ Otkazib yuborish', callback_data=callback_data)]])


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('🏠 Bosh menyu', callback_data='back_menu')]])


def chat_exit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('🚪 Suhbatdan chiqish', callback_data='chat_exit')]])
