import google.generativeai as genai
from config import GEMINI_API_KEY
import logging
import json
import re

logger = logging.getLogger(__name__)

# List of fallback models to try if primary fails
MODELS_TO_TRY = [
    'gemini-2.5-flash',
    'gemini-flash-latest',
    'gemini-3.6-flash',
    'gemini-2.5-pro'
]

SYSTEM_PROMPT = """
Sen tajribali, g'amxo'r va professional shaxsiy mentor/yordamchisan. Sening ismingiz "Ustoz".

Sening vazifalaring:
1. Foydalanuvchining shaxsiy rivojlanishi, o'rganishi va vazifalariga g'amxo'rlik qilish
2. Har bir xabarni diqqat bilan o'rganib, uning niyatini (intent) aniqlash
3. Motivatsiya berish, o'rganishda yo'naltirish, tanqid va maqtovlarni to'g'ri berish
4. O'ZBEK tilida, do'stona, samimiy va professional muloqot qilish

Javob berishda doimo foydalanuvchiga yordam berish va uni o'stirishga intil.
"""

INTENT_PARSER_PROMPT = """
Foydalanuvchi quyidagi xabarni yubordi:
"{user_message}"

Foydalanuvchining niyatini va xabarning mazmunini aniqla hamda FAKAT quyidagi JSON formatida javob ber:

```json
{{
  "intent": "chat" | "journal" | "task" | "reminder",
  "reply": "Foydalanuvchiga mentor sifatida samimiy va foydali javobingiz (o'zbek tilida)",
  "data": {{
    "entry_type": "activity" yoki "learning",
    "task_title": "vazifa nomi (agar intent task bo'lsa)",
    "reminder_text": "eslatma matni (agar intent reminder bo'lsa)",
    "reminder_time": "eslatma vaqti masalan '30m', '2h', '1d', yoki 'YYYY-MM-DD HH:MM' (agar intent reminder bo'lsa)"
  }}
}}
```

Qoidalar:
1. "journal": Agar foydalanuvchi bugun nima qilgani, nima o'rgangani yoki kunlik faoliyati haqida yozgan bo'lsa.
2. "task": Agar foydalanuvchi "bajarishim kerak", "vazifa qo'sh", "reja qil" kabi biror ishni bajarmoqchi bo'lsa.
3. "reminder": Agar foydalanuvchi "eslat", "eslatib qo'y", "vaqtda ayt" kabi so'zlardan foydalanib eslatma so'rasa.
4. "chat": Oddiy savollar, salomlashish, fikr almashish yoki boshqa har qanday suhbatlar.

Faqat va faqat JSON obyektini qaytar, boshqa hech qanday ortiqcha matn yozma!
"""


class MentorAI:
    def __init__(self):
        """Initialize Gemini AI mentor service with fallback support."""
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = None
            self.active_model_name = None
            
            # Try initializing with the first working model
            for model_name in MODELS_TO_TRY:
                try:
                    self.model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=SYSTEM_PROMPT
                    )
                    self.active_model_name = model_name
                    logger.info(f"MentorAI initialized with model: {model_name}")
                    break
                except Exception as e:
                    logger.warning(f"Failed to initialize {model_name}: {e}")
            
            if not self.model:
                raise RuntimeError("Hech qaysi Gemini modeli ishga tushmadi")

        except Exception as e:
            logger.error(f"MentorAI initialization failed: {e}")
            raise

    async def generate_with_fallback(self, prompt: str) -> str:
        """Generate content with automatic model fallback."""
        for model_name in MODELS_TO_TRY:
            try:
                m = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM_PROMPT
                )
                response = await m.generate_content_async(prompt)
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.warning(f"Model {model_name} failed: {e}")
                continue
        
        return "Kechirasiz, hozirda AI javob bera olmadi. Keyinroq qayta urinib ko'ring."

    async def parse_and_respond(self, user_message: str, user_name: str = '') -> dict:
        """Smartly process any free message from user and extract intent + reply."""
        try:
            prompt = INTENT_PARSER_PROMPT.format(user_message=user_message)
            raw_response = await self.generate_with_fallback(prompt)
            
            # Extract JSON from Markdown codeblocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = raw_response.strip()

            parsed = json.loads(json_str)
            return parsed
        except Exception as e:
            logger.error(f"Parse and respond error: {e}")
            # Fallback smart chat response if JSON parsing fails
            reply = await self.generate_with_fallback(
                f"Foydalanuvchi ({user_name}): {user_message}\n\nMentor sifatida qisqa va foydali javob ber:"
            )
            return {
                "intent": "chat",
                "reply": reply,
                "data": {}
            }

    async def get_daily_feedback(self, activities: str, learnings: str, user_name: str = '') -> str:
        """Get mentor feedback on today's activities and learnings."""
        display_name = user_name if user_name else 'do\'stim'
        prompt = f"""
Foydalanuvchi: {display_name}

📋 Bugun qilgan ishlari:
{activities}

📚 Bugun o'rgangan narsalari:
{learnings}

Ushbu kun haqida qisqa mentor fikringni bildir. Yaxshi qilgan narsalarini maqta, yetishmovchiliklarini ko'rsat, va ertaga nima qilish kerakligini maslahat ber.
"""
        return await self.generate_with_fallback(prompt)

    async def analyze_daily(self, entries: list) -> str:
        """Analyze today's entries."""
        if not entries:
            return "📭 Bugun hali hech narsa yozilmagan. Bugungi ishlaringiz va o'rganganlaringizni yozib qoldiring!"
        
        entries_text = "\n".join([f"- [{e['entry_type']}] {e['content']}" for e in entries])
        prompt = f"Quyidagi bugungi kunlik yozuvlarni tahlil qil va mentor sifatida qisqa xulosa ber:\n\n{entries_text}"
        return await self.generate_with_fallback(prompt)

    async def analyze_period(self, entries: list, period_name: str) -> str:
        """Analyze entries for period."""
        if not entries:
            return f"📭 {period_name.capitalize()} davomida yozuvlar topilmadi."
        
        entries_text = "\n".join([f"- {e['created_at'][:10]}: {e['content']}" for e in entries])
        prompt = f"Quyidagi {period_name}lik yozuvlarni mentor sifatida chuqur tahlil qil:\n\n{entries_text}"
        return await self.generate_with_fallback(prompt)

    async def chat(self, message: str, context_history: list, user_name: str = '') -> str:
        """Free chat with AI mentor."""
        prompt = f"Foydalanuvchi ({user_name}): {message}\n\nQisqa, samimiy va maslahatgo'y mentor sifatida javob ber:"
        return await self.generate_with_fallback(prompt)


# Singleton
mentor_ai = None

def get_mentor() -> MentorAI:
    global mentor_ai
    if mentor_ai is None:
        mentor_ai = MentorAI()
    return mentor_ai
