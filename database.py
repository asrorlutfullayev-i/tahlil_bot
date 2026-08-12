import logging
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import DB_PATH

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all database tables if they do not exist."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    timezone TEXT DEFAULT 'Asia/Tashkent'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    entry_type TEXT,
                    content TEXT,
                    ai_feedback TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT,
                    deadline TEXT,
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    text TEXT,
                    remind_at TEXT,
                    is_sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS ai_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
    except Exception as e:
        logger.error(f"Error in init_db: {e}")
        raise


async def add_user(user_id: int, username: str, first_name: str) -> None:
    """Insert user if not exists or ignore."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username, first_name)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Error in add_user: {e}")


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by user_id."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    except Exception as e:
        logger.error(f"Error in get_user: {e}")
        return None


async def add_journal_entry(user_id: int, entry_type: str, content: str, ai_feedback: Optional[str] = None) -> int:
    """Add journal entry and return entry id."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO journal_entries (user_id, entry_type, content, ai_feedback) VALUES (?, ?, ?, ?)",
                (user_id, entry_type, content, ai_feedback)
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error in add_journal_entry: {e}")
        return 0


async def get_journal_entries_today(user_id: int) -> List[Dict[str, Any]]:
    """Get today's journal entries for user."""
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM journal_entries WHERE user_id = ? AND DATE(created_at) = ? ORDER BY created_at DESC",
                (user_id, today_str)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_journal_entries_today: {e}")
        return []


async def get_journal_entries_period(user_id: int, days: int) -> List[Dict[str, Any]]:
    """Get journal entries for the last N days."""
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM journal_entries WHERE user_id = ? AND DATE(created_at) >= ? ORDER BY created_at DESC",
                (user_id, start_date)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_journal_entries_period: {e}")
        return []


async def add_task(user_id: int, title: str, deadline: Optional[str] = None) -> int:
    """Add a new task and return task id."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO tasks (user_id, title, deadline) VALUES (?, ?, ?)",
                (user_id, title, deadline)
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error in add_task: {e}")
        return 0


async def get_tasks(user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get tasks for a user, optionally filtered by status."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            if status:
                query = "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY id DESC"
                params = (user_id, status)
            else:
                query = "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC"
                params = (user_id,)
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_tasks: {e}")
        return []


async def update_task_status(task_id: int, status: str) -> None:
    """Update task status and set completed_at timestamp if done."""
    try:
        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'done' else None
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
                (status, completed_at, task_id)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Error in update_task_status: {e}")


async def delete_task(task_id: int) -> None:
    """Delete a task by task_id."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Error in delete_task: {e}")


async def get_pending_tasks_count(user_id: int) -> int:
    """Get total count of pending tasks for a user."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'pending'",
                (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
    except Exception as e:
        logger.error(f"Error in get_pending_tasks_count: {e}")
        return 0


async def add_reminder(user_id: int, text: str, remind_at: str) -> int:
    """Add a new reminder and return reminder id."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "INSERT INTO reminders (user_id, text, remind_at) VALUES (?, ?, ?)",
                (user_id, text, remind_at)
            )
            await db.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error in add_reminder: {e}")
        return 0


async def get_pending_reminders() -> List[Dict[str, Any]]:
    """Get all unsent reminders where remind_at <= current time."""
    try:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reminders WHERE is_sent = 0 AND remind_at <= ? ORDER BY remind_at ASC",
                (now_str,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_pending_reminders: {e}")
        return []


async def get_user_reminders(user_id: int) -> List[Dict[str, Any]]:
    """Get user's future/unsent reminders."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM reminders WHERE user_id = ? AND is_sent = 0 ORDER BY remind_at ASC",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_user_reminders: {e}")
        return []


async def mark_reminder_sent(reminder_id: int) -> None:
    """Mark reminder as sent."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Error in mark_reminder_sent: {e}")


async def delete_reminder(reminder_id: int) -> None:
    """Delete a reminder by id."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            await db.commit()
    except Exception as e:
        logger.error(f"Error in delete_reminder: {e}")


async def save_ai_context(user_id: int, role: str, content: str) -> None:
    """Save user or assistant message to AI context history."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO ai_context (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Error in save_ai_context: {e}")


async def get_ai_context(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Get last N entries of AI context history for user in chronological order."""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM (SELECT * FROM ai_context WHERE user_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
                (user_id, limit)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_ai_context: {e}")
        return []


async def get_stats(user_id: int) -> Dict[str, int]:
    """Returns dict with: total_entries, total_tasks, completed_tasks, streak_days, entries_today, entries_this_week."""
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')
        week_ago_str = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        async with aiosqlite.connect(DB_PATH) as db:
            # Total entries
            async with db.execute("SELECT COUNT(*) FROM journal_entries WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                total_entries = row[0] if row else 0

            # Total tasks
            async with db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                total_tasks = row[0] if row else 0

            # Completed tasks
            async with db.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'done'", (user_id,)) as cursor:
                row = await cursor.fetchone()
                completed_tasks = row[0] if row else 0

            # Entries today
            async with db.execute(
                "SELECT COUNT(*) FROM journal_entries WHERE user_id = ? AND DATE(created_at) = ?",
                (user_id, today_str)
            ) as cursor:
                row = await cursor.fetchone()
                entries_today = row[0] if row else 0

            # Entries this week
            async with db.execute(
                "SELECT COUNT(*) FROM journal_entries WHERE user_id = ? AND DATE(created_at) >= ?",
                (user_id, week_ago_str)
            ) as cursor:
                row = await cursor.fetchone()
                entries_this_week = row[0] if row else 0

            # Calculate streak_days
            async with db.execute(
                "SELECT DISTINCT DATE(created_at) as entry_date FROM journal_entries WHERE user_id = ? ORDER BY entry_date DESC",
                (user_id,)
            ) as cursor:
                dates_rows = await cursor.fetchall()
                dates = [r[0] for r in dates_rows if r[0]]

            streak_days = 0
            if dates:
                today = datetime.now().date()
                yesterday = today - timedelta(days=1)
                latest_date = datetime.strptime(dates[0], '%Y-%m-%d').date()

                if latest_date == today or latest_date == yesterday:
                    current_check = latest_date
                    dates_set = {datetime.strptime(d, '%Y-%m-%d').date() for d in dates}
                    while current_check in dates_set:
                        streak_days += 1
                        current_check -= timedelta(days=1)

            return {
                'total_entries': total_entries,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'streak_days': streak_days,
                'entries_today': entries_today,
                'entries_this_week': entries_this_week
            }
    except Exception as e:
        logger.error(f"Error in get_stats: {e}")
        return {
            'total_entries': 0,
            'total_tasks': 0,
            'completed_tasks': 0,
            'streak_days': 0,
            'entries_today': 0,
            'entries_this_week': 0
        }
