# Stop any running Python processes
Stop-Process -Name python -ErrorAction SilentlyContinue

# Delete the SQLite database
Remove-Item -Path ".\db.sqlite3" -Force -ErrorAction SilentlyContinue

# Remove all migration files except __init__.py
Get-ChildItem -Recurse -Include *.py -Path .\*\migrations\* | Where-Object { $_.Name -ne "__init__.py" } | Remove-Item -Force
Get-ChildItem -Recurse -Include *.pyc -Path .\*\migrations\* | Remove-Item -Force

# Run Django migrations
python manage.py makemigrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser
