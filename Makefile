stoprigup:
	sudo systemctl stop rigup
startrigup:
	sudo systemctl start rigup
riguplogs:
	sudo journalctl -u rigup -f