# Morrow — Expense Tracker

A personal finance dashboard built with Flask, vanilla HTML/CSS/JavaScript, Chart.js, and MySQL. It includes secure password hashing, account login, a readable animated teal theme, category and daily spending charts, monthly filtering, and CSV reports. The dashboard and supporting pages are branded as created and advertised by Parihar Technologies.

## Run locally

Requirements: Python 3.10+ and Docker Desktop.

1. Copy `.env.example` to `.env` and set a random `SECRET_KEY` for local use.
2. Start the app and MySQL: `docker compose up --build`
3. Open [http://localhost:8000](http://localhost:8000), create an account, and add expenses.

To run without Docker, create a virtual environment, install `requirements.txt`, and run `python app.py`. That uses a local SQLite database. Production requires both `APP_ENV=production`, a unique `SECRET_KEY`, and a MySQL `DATABASE_URL`.

## Deploy for a public portfolio link

Deploy the included Dockerfile to a container host and attach a managed MySQL 8 database. In the hosting dashboard, add these environment variables:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `SECRET_KEY` | A newly generated, long random value |
| `DATABASE_URL` | `mysql+pymysql://USER:PASSWORD@HOST:3306/expense_tracker?charset=utf8mb4` |

Set the container port to `8000` and use `/health` for the health check. Keep database credentials and the secret key in the host's secret manager; never commit them. The app creates its tables when it starts. The public app URL can then be shared with recruiters.

For a one-click host flow, push this folder to a Git repository and connect that repository to a Docker-capable host. Provision MySQL separately on the same provider or an external managed database provider, then add the variables above. A public production link requires access to a hosting account and a database; neither should be embedded in source code.

## Features

- User registration and sign-in with Werkzeug password hashing and session protection
- Personal expense records isolated by user, with create and delete actions
- Four signed-in sections: Overview, Transactions, Reports, and About
- Dashboard month picker, month-over-month comparison, category totals, and daily spending chart
- CSV report export for the selected month
- CSRF protection on forms, responsive layout, and a health endpoint
- Larger default text, responsive mobile navigation, animated page entry, and reduced-motion support

## Automatic transaction connections

The app currently supports manual expense entry. Automatic payment-app synchronization is not connected yet: the correct provider depends on the user's country and chosen apps, and requires an approved aggregator/API account plus user consent. Morrow must never collect payment-app passwords or scrape payment-app screens. Configure a provider such as a local open-banking/account-aggregator service or a supported bank-link provider before enabling the connection flow.

## Project structure

`app.py` contains Flask routes and SQLAlchemy models. `templates/` contains the server-rendered pages. `static/` contains the custom stylesheet and browser-side chart/dialog behavior.
