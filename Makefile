# playgta5-fixes — Linux convenience targets
# Usage: make <target>

.PHONY: help setup patch run lan verify browser doctor status stop shortcut clean

help:
	@echo "playgta5-fixes — Linux targets"
	@echo ""
	@echo "  make setup      Extract + merge game data, then patch game.wasm"
	@echo "  make patch      Apply the game.wasm fixes only"
	@echo "  make run        Start the local server and open the browser"
	@echo "  make lan        Serve to other devices on your network"
	@echo "  make verify     Check the installation"
	@echo "  make browser    Check for a WebGPU-capable browser"
	@echo "  make doctor     Full health check (install + browser + status)"
	@echo "  make status     Show install + server status"
	@echo "  make stop       Stop a running local server"
	@echo "  make shortcut   Install the desktop shortcut"
	@echo "  make clean      Delete the downloaded ZIP (after verification)"

setup:
	./playgta5.sh setup

patch:
	./playgta5.sh patch

run:
	./playgta5.sh start

lan:
	./playgta5.sh lan

verify:
	./playgta5.sh verify

browser:
	./playgta5.sh browser

doctor:
	./playgta5.sh doctor

status:
	./playgta5.sh status

stop:
	./playgta5.sh stop

shortcut:
	./playgta5.sh shortcut

clean:
	@if [ -f GTA5Webport.zip ]; then rm -f GTA5Webport.zip && echo "Removed GTA5Webport.zip"; else echo "No ZIP to remove"; fi
