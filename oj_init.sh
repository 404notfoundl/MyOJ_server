#!/bin/bash
echo enter venv
source venv/bin/activate
echo make migrations
python manage.py makemigrations oj_tasks problem_lib site_config site_users solutions
echo migrate
python manage.py migrate
#echo create super user
#python manage.py createsuperuser
echo "load initial data"
python manage.py loaddata site_config/init_data.json
