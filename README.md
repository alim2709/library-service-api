# Library Service

Online management system for book borrowings.

## Features

* JWT authenticated.
* Admin panel /admin/
* Documentation at /api/doc/swagger/
* Books inventory management.
* Books borrowing management.
* Notifications service through Telegram API (bot and chat).
* Scheduled notifications with Celery and Redis.
* Payments handle with Stripe API.


## How to run with Docker

Docker should be installed.

Create `.env` file with your variables (look at `.env.sample`
file, don't change `POSTGRES_DB` and `POSTGRES_HOST`).

```shell
docker-compose build
docker-compose up
```
* create admin user & Create schedule for running tasks
* get access token via /api/user/token/


A telegram bot has already been created for this application - https://t.me/alim_testing_bot
1. Write any message in bot
2. To retrieve chat_id use script `teleram-script.py`.
3. Add to env variables `chat_id` retrieved by script, to test functionality.
