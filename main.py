import logging
import os
import datetime
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import aiohttp
from psycopg2_pool import SimpleConnectionPool

# --- 初始设置 ---

# 加载 .env 文件中的环境变量
load_dotenv()

# 设置日志记录
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 从环境变量获取密钥和配置
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# HKBU GenAI API 配置
HKBU_API_KEY = os.getenv("HKBU_API_KEY")
HKBU_BASE_URL = os.getenv("HKBU_BASE_URL", "https://genai.hkbu.edu.hk/general/rest")
HKBU_MODEL_NAME = os.getenv("HKBU_MODEL_NAME", "gpt-4-o-mini")
HKBU_API_VERSION = os.getenv("HKBU_API_VERSION", "2024-05-01-preview")

# 数据库配置
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

# 记录机器人启动时间（用于 /stats 命令）
BOT_START_TIME = datetime.datetime.now(datetime.timezone.utc)

# --- 数据库操作 ---

'''def get_db_connection():
    """创建并返回一个数据库连接"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            sslmode="require"  # AWS RDS 云数据库需要 SSL
        )
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"数据库连接失败: {e}")
        return None'''

# 全局数据库连接池（启动时初始化）
db_pool = None

def init_db_pool():
    global db_pool
    db_pool = SimpleConnectionPool(
        minconn=1,
        maxconn=10,          # 并发高峰时可同时持有10个连接
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require"
    )

async def log_to_db(user_id: int, user_message: str, bot_response: str):
    def sync_insert():
        conn = None
        try:
            conn = psycopg2.connect(
                host=DB_HOST, dbname=DB_NAME, user=DB_USER,
                password=DB_PASSWORD, port=DB_PORT, sslmode="require"
            )
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO chat_logs (user_id, user_message, bot_response) VALUES (%s, %s, %s)",
                    (user_id, user_message, bot_response)
                )
            conn.commit()
        except Exception as e:
            logger.error(f"数据库错误: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
    await asyncio.to_thread(sync_insert)

def log_to_db(user_id: int, user_message: str, bot_response: str):
    """将聊天记录写入数据库"""
    conn = get_db_connection()
    if conn is None:
        logger.error("无法记录到数据库，因为没有数据库连接。")
        return

    try:
        with conn.cursor() as cur:
            query = sql.SQL("INSERT INTO chat_logs (user_id, user_message, bot_response) VALUES (%s, %s, %s)")
            cur.execute(query, (user_id, user_message, bot_response))
        conn.commit()
    except Exception as e:
        logger.error(f"写入数据库时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

# --- HKBU GenAI API 交互 ---

# 系统提示词：让 GPT 扮演 HKBU 校园助手角色
SYSTEM_PROMPT = (
    "You are CampusBot, a helpful campus assistant for HKBU (Hong Kong Baptist University) students. "
    "You can help with course-related questions, campus life, study tips, academic advice, and general knowledge. "
    "Always be friendly, concise, and supportive. When answering course-related questions, encourage students "
    "to also consult their instructors or official university resources for authoritative information."
)

async def get_llm_response(prompt: str) -> str:
    """异步调用 HKBU GenAI API"""
    if not HKBU_API_KEY:
        logger.error("HKBU_API_KEY 未设置")
        return "抱歉，我的大脑（AI模型）暂时无法连接，请稍后再试。"

    url = f"{HKBU_BASE_URL}/deployments/{HKBU_MODEL_NAME}/chat/completions?api-version={HKBU_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "api-key": HKBU_API_KEY
    }
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    }

    timeout = aiohttp.ClientTimeout(total=30)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"HKBU API 返回意外格式: {data}")
                    return "抱歉，AI 返回了意外的响应格式，请稍后再试。"
    except asyncio.TimeoutError:
        logger.error("HKBU API 超时")
        return "抱歉，AI 响应超时，请稍后再试。"
    except aiohttp.ClientError as e:
        logger.error(f"HKBU API 请求失败: {e}")
        return "抱歉，我在思考时遇到了一个问题，请稍后再试。"

# --- Telegram 机器人处理器 ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user
    await update.message.reply_html(
        f"你好，{user.mention_html()}！🎓\n\n"
        "我是 <b>CampusBot</b>，你的 HKBU 校园助手。我可以回答课程问题、校园生活咨询，以及各类学习建议。\n\n"
        "发送 /help 查看所有可用命令。",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /help 命令，列出所有可用命令"""
    help_text = (
        "🤖 <b>CampusBot 可用命令</b>\n\n"
        "/start — 显示欢迎消息\n"
        "/help — 显示此帮助信息\n"
        "/history — 查看你最近的 5 条聊天记录\n"
        "/stats — 查看机器人统计信息\n"
        "/clear — 清除你的所有聊天记录\n\n"
        "💬 <b>直接发送消息</b> — 向 AI 校园助手提问，获取即时解答！\n\n"
        "📚 可以问我关于课程、校园生活、学习技巧等任何问题。"
    )
    await update.message.reply_html(help_text)

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /history 命令，显示用户最近的聊天记录（异步版本）"""
    user_id = update.effective_user.id

    def sync_fetch_history():
        conn = None
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                sslmode="require"
            )
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_message, bot_response, created_at FROM chat_logs "
                    "WHERE user_id = %s ORDER BY created_at DESC LIMIT 5",
                    (user_id,)
                )
                return cur.fetchall()
        except Exception as e:
            logger.error(f"查询聊天记录时出错: {e}")
            raise
        finally:
            if conn:
                conn.close()

    try:
        rows = await asyncio.to_thread(sync_fetch_history)
    except Exception:
        await update.message.reply_text("❌ 无法连接数据库，请稍后再试。")
        return

    if not rows:
        await update.message.reply_text("📭 你还没有任何聊天记录。")
        return

    lines = ["📜 <b>你最近的 5 条聊天记录：</b>\n"]
    for i, (user_msg, bot_resp, created_at) in enumerate(rows, 1):
        timestamp = created_at.strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"<b>[{i}] {timestamp}</b>\n"
            f"👤 你：{user_msg[:100]}{'...' if len(user_msg) > 100 else ''}\n"
            f"🤖 Bot：{bot_resp[:100]}{'...' if len(bot_resp) > 100 else ''}\n"
        )
    await update.message.reply_html("\n".join(lines))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /stats 命令，显示机器人统计信息（异步版本）"""
    uptime = datetime.datetime.now(datetime.timezone.utc) - BOT_START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    # 定义同步数据库查询函数
    def sync_get_stats():
        conn = None
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                sslmode="require"
            )
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM chat_logs")
                total_messages = cur.fetchone()[0]

                cur.execute("SELECT COUNT(DISTINCT user_id) FROM chat_logs")
                unique_users = cur.fetchone()[0]

            return total_messages, unique_users
        except Exception as e:
            logger.error(f"查询统计信息时出错: {e}")
            raise
        finally:
            if conn:
                conn.close()

    # 在线程池中执行数据库操作
    try:
        total_messages, unique_users = await asyncio.to_thread(sync_get_stats)
        stats_text = (
            f"📊 <b>CampusBot 统计信息</b>\n\n"
            f"⏱ 运行时长：{uptime_str}\n"
            f"💬 处理消息总数：{total_messages}\n"
            f"👥 服务用户数：{unique_users}\n"
            f"🗄 数据库状态：✅ 正常"
        )
        await update.message.reply_html(stats_text)
    except Exception:
        # 数据库查询失败
        await update.message.reply_html(
            f"📊 <b>机器人统计</b>\n\n⏱ 运行时长：{uptime_str}\n❌ 数据库暂时不可用",
            parse_mode="HTML"
        )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /clear 命令，清除用户的聊天记录（异步版本）"""
    user_id = update.effective_user.id

    # 定义同步数据库删除函数
    def sync_clear_history():
        conn = None
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                sslmode="require"
            )
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chat_logs WHERE user_id = %s", (user_id,))
                deleted_count = cur.rowcount
            conn.commit()
            return deleted_count
        except Exception as e:
            logger.error(f"清除聊天记录时出错: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    try:
        deleted_count = await asyncio.to_thread(sync_clear_history)
        await update.message.reply_text(f"🗑 已成功清除你的 {deleted_count} 条聊天记录。")
    except Exception:
        await update.message.reply_text("❌ 清除聊天记录时出错，请稍后再试。")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    logger.info(f"收到来自用户 {user_id} 的消息: {user_message}")

    # 1. 异步获取 AI 回复
    bot_response = await get_llm_response(user_message)

    # 2. 异步发送回复
    await update.message.reply_text(bot_response)

    # 3. 异步记录到数据库（不阻塞主流程）
    asyncio.create_task(log_to_db(user_id, user_message, bot_response))

def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """记录由更新引起的错误"""
    logger.error("出现异常:", exc_info=context.error)

# --- 主函数 ---

def main():
    """启动机器人"""
    if not TELEGRAM_TOKEN:
        logger.critical("未找到 TELEGRAM_TOKEN，机器人无法启动！")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # 添加命令和消息处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 添加错误处理器
    application.add_error_handler(error_handler)

    logger.info("机器人正在启动...")
    # 以轮询方式运行机器人
    application.run_polling()

if __name__ == '__main__':
    PORT = int(os.getenv("PORT", 8000)) # App Runner 会动态分配端口
    WEBHOOK_URL = os.getenv("WEBHOOK_URL") # 你的 App Runner 服务 URL
    WEBHOOK_PATH = "/webhook"

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=os.getenv("WEBHOOK_SECRET"), # 可选，但强烈建议设置
    )