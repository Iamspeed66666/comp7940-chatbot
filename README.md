# COMP7940 Chatbot

A Telegram chatbot powered by OpenAI GPT-3.5-turbo with PostgreSQL conversation logging. Built for the COMP7940 course.

## Features

- **AI-Powered Conversations** — Responds to user messages using OpenAI's GPT-3.5-turbo model.
- **Chat Logging** — Stores all conversations (user ID, message, and bot response) in a PostgreSQL database.
- **Telegram Integration** — Runs as a Telegram bot using long-polling.
- **Containerized Deployment** — Dockerized for deployment on AWS App Runner.

## Architecture

```
User sends message on Telegram
        │
        ▼
  handle_message()
        │
        ▼
  get_llm_response()  ──►  OpenAI GPT-3.5-turbo API
        │
        ▼
  Reply sent to user on Telegram
        │
        ▼
  log_to_db()  ──►  PostgreSQL (chat_logs table)
```

## Tech Stack

| Technology | Purpose |
|---|---|
| Python | Application language |
| [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (v22.7) | Telegram Bot API framework |
| [OpenAI Python SDK](https://github.com/openai/openai-python) (v2.30.0) | OpenAI API client |
| PostgreSQL (via psycopg2) | Chat history database |
| Docker | Containerization |
| AWS App Runner + ECR | Cloud deployment |

## Prerequisites

- Python 3.10+
- A [Telegram Bot Token](https://core.telegram.org/bots#how-do-i-create-a-bot) (from BotFather)
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A PostgreSQL database with a `chat_logs` table

### Database Setup

Create the `chat_logs` table in your PostgreSQL database:

```sql
CREATE TABLE chat_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    user_message TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Iamspeed66666/comp7940-chatbot.git
cd comp7940-chatbot
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with the following values:

```
TELEGRAM_TOKEN=your-telegram-bot-token
OPENAI_API_KEY=your-openai-api-key
DB_HOST=your-database-host
DB_NAME=your-database-name
DB_USER=your-database-user
DB_PASSWORD=your-database-password
DB_PORT=5432
```

### 4. Run the bot

```bash
python main.py
```

The bot will start polling for messages. Open your bot in Telegram and send `/start` to begin.

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Displays a welcome message |
| `/help` | Lists all available commands |
| `/history` | Shows your last 5 chat messages from the database |
| `/stats` | Shows bot statistics (uptime, total messages, unique users) |
| `/clear` | Clears all your chat history from the database |
| *(any text)* | Sends the message to OpenAI and replies with the AI-generated response |

## Deployment

The project includes a GitHub Actions workflow (`.github/workflows/main.yml`) that automatically deploys on every push to `main`:

1. Builds a Docker image
2. Pushes it to Amazon ECR
3. Deploys to AWS App Runner

Required GitHub Secrets for deployment:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_ECR_REPOSITORY`
- `AWS_APP_RUNNER_SERVICE_ARN`

## Project Structure

```
├── main.py                 # Application entry point (bot logic, OpenAI, DB)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Multi-container orchestration (bot + PostgreSQL)
├── init.sql                # Database initialization script
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
└── .github/
    └── workflows/
        └── main.yml        # CI/CD pipeline for AWS deployment
```

## License

This project is for educational purposes as part of the COMP7940 course.
