
push:
	rsync -azv . haztecaso.com:jobo_bot --exclude "database.*" --exclude "*.log" --delete --exclude __pycache__ --exclude .git 
