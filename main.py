import logging
import os
import datetime
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT")

# 记录机器人启动时间（用于 /stats 命令）
BOT_START_TIME = datetime.datetime.now(datetime.timezone.utc)

# 初始化 OpenAI 客户端
try:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    logger.error(f"无法初始化 OpenAI 客户端: {e}")
    openai_client = None

# --- 数据库操作 ---

def get_db_connection():
    """创建并返回一个数据库连接"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"数据库连接失败: {e}")
        return None

def log_to_db(user_id: int, user_message: str, bot_response: str):
    """将聊天记录写入数据库"""
    conn = get_db_connection()
    if conn is None:
        logger.error("无法记录到数据库，因为没有数据库连接。")
        return

    try:
        with conn.cursor() as cur:
            # SQL 查询语句
            query = sql.SQL("INSERT INTO chat_logs (user_id, user_message, bot_response) VALUES (%s, %s, %s)")
            cur.execute(query, (user_id, user_message, bot_response))
        conn.commit()
    except Exception as e:
        logger.error(f"写入数据库时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

# --- OpenAI 交互 ---

# 系统提示词：让 GPT 扮演 HKBU 校园助手角色
SYSTEM_PROMPT = (
    "You are CampusBot, a helpful campus assistant for HKBU (Hong Kong Baptist University) students. "
    "You can help with course-related questions, campus life, study tips, academic advice, and general knowledge. "
    "Always be friendly, concise, and supportive. When answering course-related questions, encourage students "
    "to also consult their instructors or official university resources for authoritative information."
)

def get_llm_response(prompt: str) -> str:
    """调用 OpenAI API 获取回复"""
    if not openai_client:
        logger.error("OpenAI 客户端未初始化，无法获取回复。")
        return "抱歉，我的大脑（AI模型）暂时无法连接，请稍后再试。"

    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"调用 OpenAI API 时出错: {e}")
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
    """处理 /history 命令，显示用户最近的聊天记录"""
    user_id = update.effective_user.id
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("❌ 无法连接数据库，请稍后再试。")
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_message, bot_response, created_at FROM chat_logs "
                "WHERE user_id = %s ORDER BY created_at DESC LIMIT 5",
                (user_id,)
            )
            rows = cur.fetchall()

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
    except Exception as e:
        logger.error(f"查询聊天记录时出错: {e}")
        await update.message.reply_text("❌ 查询聊天记录时出错，请稍后再试。")
    finally:
        conn.close()

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /stats 命令，显示机器人统计信息"""
    conn = get_db_connection()
    uptime = datetime.datetime.now(datetime.timezone.utc) - BOT_START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    if conn is None:
        await update.message.reply_text(
            f"📊 <b>机器人统计</b>\n\n⏱ 运行时长：{uptime_str}\n❌ 数据库暂时不可用",
            parse_mode="HTML"
        )
        return

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM chat_logs")
            total_messages = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT user_id) FROM chat_logs")
            unique_users = cur.fetchone()[0]

        stats_text = (
            f"📊 <b>CampusBot 统计信息</b>\n\n"
            f"⏱ 运行时长：{uptime_str}\n"
            f"💬 处理消息总数：{total_messages}\n"
            f"👥 服务用户数：{unique_users}\n"
            f"🗄 数据库状态：✅ 正常"
        )
        await update.message.reply_html(stats_text)
    except Exception as e:
        logger.error(f"查询统计信息时出错: {e}")
        await update.message.reply_text("❌ 获取统计信息时出错，请稍后再试。")
    finally:
        conn.close()

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /clear 命令，清除用户的聊天记录"""
    user_id = update.effective_user.id
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("❌ 无法连接数据库，请稍后再试。")
        return

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_logs WHERE user_id = %s", (user_id,))
            deleted_count = cur.rowcount
        conn.commit()
        await update.message.reply_text(f"🗑 已成功清除你的 {deleted_count} 条聊天记录。")
    except Exception as e:
        logger.error(f"清除聊天记录时出错: {e}")
        conn.rollback()
        await update.message.reply_text("❌ 清除聊天记录时出错，请稍后再试。")
    finally:
        conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户的文本消息"""
    user_id = update.effective_user.id
    user_message = update.message.text
    logger.info(f"收到来自用户 {user_id} 的消息: {user_message}")

    # 1. 获取 OpenAI 的回复
    bot_response = get_llm_response(user_message)

    # 2. 将回复发送给用户
    await update.message.reply_text(bot_response)

    # 3. 将对话记录到数据库
    log_to_db(user_id, user_message, bot_response)

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
    main()