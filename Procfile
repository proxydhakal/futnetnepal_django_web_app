release: python manage.py makemigrations
release: python manage.py migrate
release: python manage.py collectstatic --no-input
web: gunicorn futnetnepal.wsgi --log-file -

