# COMP7940 CampusBot

A smart campus chatbot built with Telegram, HKBU GenAI API, and PostgreSQL for COMP7940 at Hong Kong Baptist University (HKBU). It provides course advice, campus life tips, and study guidance to students.

## Features

- AI-powered conversation using HKBU GenAI API (GPT-4o-mini)
- Chat log persistence with PostgreSQL
- Chat history retrieval, bot statistics, and record clearing via bot commands
- Containerized deployment with Docker
- CI/CD pipeline for automatic deployment to AWS EC2

## Tech Stack

- Python 3.11
- python-telegram-bot v22.7
- HKBU GenAI REST API (via requests)
- PostgreSQL (psycopg2, with AWS RDS support)
- Docker and Docker Compose
- AWS EC2 + ECR

## Quick Start

1. Fork and clone this repository.
2. Copy `.env.example` to `.env` and fill in the required values:
   - `TELEGRAM_TOKEN` — your Telegram bot token from @BotFather
   - `HKBU_API_KEY` — your API key from the HKBU GenAI platform (https://genai.hkbu.edu.hk)
   - Database connection details (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`)
3. Run `docker compose up --build` to start the bot.

Open Telegram, find your bot, and send `/start` to begin chatting.

## Environment Variables

| Variable | Description |
|---|---|
| `TELEGRAM_TOKEN` | Telegram bot token from @BotFather |
| `HKBU_API_KEY` | API key from HKBU GenAI platform |
| `HKBU_BASE_URL` | GenAI API base URL (default: `https://genai.hkbu.edu.hk/general/rest`) |
| `HKBU_MODEL_NAME` | Model name (default: `gpt-4-o-mini`) |
| `HKBU_API_VERSION` | API version (default: `2024-05-01-preview`) |
| `DB_HOST` | PostgreSQL host address |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `DB_PORT` | Database port (default: `5432`) |

## Bot Commands

- `/start` — Welcome message
- `/help` — List all available commands
- `/history` — View your last 5 chat records
- `/stats` — View bot statistics (uptime, total messages, user count)
- `/clear` — Clear your chat history
- Send any text message to get an AI-powered response

## Project Structure

- `main.py` — Main application (bot logic, HKBU GenAI API calls, database operations)
- `requirements.txt` — Python dependencies
- `Dockerfile` — Docker image build file
- `docker-compose.yml` — Docker Compose orchestration
- `init.sql` — Database initialization script (creates the chat_logs table)
- `.env.example` — Environment variable template
- `.github/workflows/main.yml` — CI/CD pipeline for AWS EC2 deployment

## Running Without Docker (Optional)

1. Create and activate a Python virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Set up a PostgreSQL database and run `init.sql` to initialize the table.
4. Configure your `.env` file with all required variables.
5. Run `python main.py`.

## AWS EC2 Deployment

The included GitHub Actions workflow automatically:
1. Lints the code with flake8
2. Builds a Docker image and pushes it to Amazon ECR
3. SSHes into the EC2 instance, pulls the new image, and restarts the container

Configure the following secrets in your GitHub repository (**Settings → Secrets and variables → Actions**):

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key ID |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret access key |
| `AWS_REGION` | AWS region (e.g. `ap-east-1`) |
| `AWS_ECR_REPOSITORY` | ECR repository name (e.g. `comp7940-chatbot`) |
| `AWS_ECR_REGISTRY` | ECR registry URL (e.g. `123456789.dkr.ecr.ap-east-1.amazonaws.com`) |
| `EC2_HOST` | Public IP or DNS of your EC2 instance |
| `EC2_USER` | SSH username (e.g. `ec2-user` or `ubuntu`) |
| `EC2_SSH_KEY` | Private SSH key for connecting to EC2 |
| `TELEGRAM_TOKEN` | Telegram bot token (injected at container runtime) |

> **Note:** The EC2 instance must have Docker installed and the AWS CLI configured (or an IAM role attached) to pull images from ECR.
## License

This is a course project for COMP7940. For educational use only.
