#!/usr/bin/env bash
# exit on error
set -o errexit

# Install requirements
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate