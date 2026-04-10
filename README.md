# COMP7940 CampusBot

A smart campus chatbot built with Telegram, OpenAI GPT-3.5-turbo, and PostgreSQL for COMP7940 at Hong Kong Baptist University (HKBU). It provides course advice, campus life tips, and study guidance to students.

## Features

- AI-powered conversation using OpenAI GPT-3.5-turbo
- Chat log persistence with PostgreSQL
- Chat history retrieval, bot statistics, and record clearing via bot commands
- One-command deployment with Docker Compose
- Optional CI/CD pipeline for automatic deployment to AWS App Runner

## Tech Stack

- Python 3.11
- python-telegram-bot v22.7
- OpenAI Python SDK v2.30.0
- PostgreSQL 15 (via psycopg2)
- Docker and Docker Compose
- AWS App Runner + ECR (optional)

## Quick Start

1. Fork and clone this repository.
2. Copy `.env.example` to `.env` and fill in your `TELEGRAM_TOKEN` and `OPENAI_API_KEY`. Database settings can be left as default when using Docker Compose.
3. Run `docker compose up --build` to start the bot and database.

Open Telegram, find your bot, and send `/start` to begin chatting.

## Bot Commands

- `/start` — Welcome message
- `/help` — List all available commands
- `/history` — View your last 5 chat records
- `/stats` — View bot statistics (uptime, total messages, user count)
- `/clear` — Clear your chat history
- Send any text message to get an AI-powered response

## Project Structure

- `main.py` — Main application (bot logic, OpenAI calls, database operations)
- `requirements.txt` — Python dependencies
- `Dockerfile` — Docker image build file
- `docker-compose.yml` — Docker Compose orchestration (bot + PostgreSQL)
- `init.sql` — Database initialization script (creates the chat_logs table)
- `.env.example` — Environment variable template
- `.github/workflows/main.yml` — CI/CD pipeline for AWS deployment

## Running Without Docker (Optional)

1. Create and activate a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Set up a PostgreSQL database and run `init.sql` to initialize the table.
4. Update `.env` with your database connection details.
5. Run `python main.py`.

## AWS Deployment (Optional)

The included GitHub Actions workflow automatically builds, pushes to Amazon ECR, and deploys to AWS App Runner on every push to the `main` branch. Configure the following secrets in your repository settings: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_ECR_REPOSITORY`, and `AWS_APP_RUNNER_SERVICE_ARN`.

## License

This is a course project for COMP7940. For educational use only.
