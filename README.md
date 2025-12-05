# Customer Service Tester

A Django application for testing customer service interactions using AI agents.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

3. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

4. Run the server:
   ```bash
   python manage.py runserver
   ```

## Usage

- Visit `/messages/` to view and reply to messages.
- Visit `/messages/create-lead/` to create new leads.
- Visit `/admin/` for admin interface.

## Features

- Asynchronous lead creation and response grading.
- Message scoring with detailed rationales.
- Clean, responsive UI.