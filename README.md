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

## How to run locally (without docker)

Install PostgreSQL and create database.

1. Clone the project
```shell
git clone https://github.com/alim2709/library-service-api.git
```
2. Open the project folder in your IDE
3. Open a terminal in the project folder

```shell
python -m venv venv
source venv/bin/activate # on MacOS
venv\Scripts\activate # on Windows
pip install -r requirements.txt
```
4. Set environment variables

Check out `.env.sample` file -> put all necessary variables -> rename `.env.sample` to `.env`

5. Make migrations and run server
```shell
python manage.py migrate
python manage.py runserver
```
6. Create admin user
7. Getting daily scheduled notifications in Telegram

* in `.env` file  set variable `CELERY_BROKER_URL=redis://localhost:6379` & `CELERY_RESULT_BACKEND=redis://localhost:6379`
* start Redis server:
```shell
    docker run -d -p 6379:6379 redis
```
* Go to admin panel & create periodic task with on of registered tasks
* Open the terminal & run `celery -A library_service_api worker -l info`
* Then open separately terminal & run `celery -A library_service_api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler`


A telegram bot has already been created for this application - https://t.me/alim_testing_bot
1. Write any message in bot
2. To retrieve chat_id use script `teleram-script.py`.
3. Add to env variables `chat_id` retrieved by script, to test functionality.
