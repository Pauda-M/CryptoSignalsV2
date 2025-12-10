@echo off
echo Running Black...
black .

echo Running isort...
isort .

echo Running flake8...
flake8

echo Running mypy...
mypy .

echo All tools finished.
pause
