import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import save_ai_context, get_ai_context
from keyboards import chat_exit_keyboard, main_menu_keyboard
from ai_service import get_mentor

logger = logging.getLogger(__name__)

async def chat_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start free chat with AI mentor."""
    context.user_data['state'] = 'free_chat'
    await update.message.reply_text(
        '💬 *Suhbat rejimi*\n\n'
        'Men bilan erkin suhbatlashing! Savolingiz, muammoingiz yoki '
        'fikrlaringizni yozing — men mentor sifatida javob beraman.\n\n'
        'Chiqish uchun quyidagi tugmani bosing 👇',
        parse_mode='Markdown',
        reply_markup=chat_exit_keyboard()
    )

async def chat_handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free chat message."""
    user = update.effective_user
    message_text = update.message.text
    
    # Save user message to context
    await save_ai_context(user.id, 'user', message_text)
    
    # Show typing indicator
    thinking_msg = await update.message.reply_text('🧠 O\'ylamoqda...')
    
    try:
        # Get conversation history
        history = await get_ai_context(user.id, limit=20)
        
        # Get AI response
        mentor = get_mentor()
        response = await mentor.chat(
            message=message_text,
            context_history=history[:-1],  # Exclude the message we just saved
            user_name=user.first_name or ''
        )
        
        # Save AI response
        await save_ai_context(user.id, 'assistant', response)
        
        await thinking_msg.edit_text(
            f'👨🏫 *Ustoz:*\n\n{response}',
            parse_mode='Markdown',
            reply_markup=chat_exit_keyboard()
        )
    except Exception as e:
        logger.error(f'Chat error: {e}')
        await thinking_msg.edit_text(
            '⚠️ Javob berishda xatolik. Qayta urinib ko\'ring.',
            reply_markup=chat_exit_keyboard()
        )

async def chat_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exit chat mode (callback query)."""
    query = update.callback_query
    context.user_data['state'] = 'idle'
    await query.edit_message_text(
        '👋 Suhbat tugatildi. Bosh menyudan davom eting!',
    )
