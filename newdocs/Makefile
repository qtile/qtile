.PHONY: genkeyimg genwidgetscreenshots

genkeyimg:
	mkdir -p ./_static/keybindings
	rm -f ./_static/keybindings/*.png
	../scripts/gen-keybinding-img -o ./_static/keybindings
	@echo
	@echo "Keybinding images have been generated."

genwidgetscreenshots:
	rm -rf screenshots/widgets
	@echo "Generating screenshots for widgets using pytest fixtures."
	pytest -o python_files="ss_*.py" -o python_functions="ss_*" --backend x11 ../test
	@echo
	@echo "Generated widget screenshots"
