# WoW Stat Tracker Makefile
#
# Usage:
#   make help     - Show this help
#   make test     - Run tests with coverage
#   make build    - Build macOS app bundle
#   make format   - Format code with black
#   make lint     - Check code formatting
#   make clean    - Remove build artifacts

.PHONY: help test test-quick build dmg format check-format lint clean install-deps run all venv

# Venv paths
VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Default target
all: format lint test

help:
	@echo "WoW Stat Tracker - Available targets:"
	@echo ""
	@echo "  make test        - Run tests with coverage report"
	@echo "  make test-quick  - Run tests without coverage"
	@echo "  make build       - Build macOS app bundle"
	@echo "  make dmg         - Build app and create DMG installer"
	@echo "  make format      - Format code with black"
	@echo "  make check-format - Check formatting (no changes)"
	@echo "  make lint        - Run flake8 linter"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make install-deps - Install Python dependencies in venv"
	@echo "  make run         - Run the application"
	@echo "  make all         - Format, lint, and test"
	@echo ""

# Create venv if it doesn't exist
$(VENV)/bin/activate:
	@echo "Creating virtual environment..."
	python3 -m venv --system-site-packages $(VENV)
	$(PIP) install --upgrade pip

# Ensure venv exists
venv: $(VENV)/bin/activate

# Run tests with coverage
test: venv
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest test/ -v --cov=. --cov-report=html --cov-report=term-missing --cov-config=.coveragerc
	@echo ""
	@echo "Coverage report generated in htmlcov/"

# Run tests without coverage (faster)
test-quick: venv
	@echo "Running tests..."
	$(PYTHON) -m pytest test/ -v

# Build macOS app bundle
build:
	@echo "Building macOS app bundle..."
	./mac/build_mac_app.sh

# Build app and create DMG installer
dmg: build
	@echo "Creating DMG installer..."
	./mac/create_dmg.sh

# Format code with black
format: venv
	@echo "Formatting code with black..."
	$(PYTHON) -m black src/ test/ --line-length 88

# Check formatting without making changes
check-format: venv
	@echo "Checking code formatting..."
	$(PYTHON) -m black src/ test/ --check --line-length 88
	@echo "All files formatted correctly!"

# Run flake8 linter
lint: venv
	@echo "Running flake8 linter..."
	$(PYTHON) -m flake8 src/ test/

# Remove build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ __pycache__/ test/__pycache__/
	rm -rf htmlcov/ .coverage .pytest_cache/
	rm -rf *.egg-info/ .eggs/
	rm -f *.pyc *.pyo *.dmg
	@echo "Clean complete!"

# Install Python dependencies
install-deps: venv
	@echo "Installing dependencies..."
	$(PIP) install pytest pytest-cov black flake8 slpp pyinstaller pyinstaller-hooks-contrib
	@echo ""
	@echo "Note: GTK dependencies must be installed separately:"
	@echo "  macOS:  brew install gtk+3 gobject-introspection pygobject3"
	@echo "  Ubuntu: sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0"

# Run the application
run: venv
	@echo "Starting WoW Stat Tracker..."
	$(PYTHON) src/wowstat.py

# Install the app to /Applications (macOS)
install: build
	@echo "Installing to /Applications..."
	cp -r dist/WoWStatTracker.app /Applications/
	@echo "Installed to /Applications/WoWStatTracker.app"

# Uninstall the app (macOS)
uninstall:
	@echo "Removing from /Applications..."
	rm -rf /Applications/WoWStatTracker.app
	@echo "Uninstalled"

# Check for required tools
check-tools: venv
	@echo "Checking for required tools..."
	@echo "  python: $(PYTHON)"
	@$(PYTHON) -c "import pytest" 2>/dev/null && echo "  pytest: OK" || echo "  pytest: not found (run: make install-deps)"
	@$(PYTHON) -c "import black" 2>/dev/null && echo "  black: OK" || echo "  black: not found (run: make install-deps)"
	@$(PYTHON) -c "import pytest_cov" 2>/dev/null && echo "  pytest-cov: OK" || echo "  pytest-cov: not found (run: make install-deps)"
	@$(PYTHON) -c "import flake8" 2>/dev/null && echo "  flake8: OK" || echo "  flake8: not found (run: make install-deps)"
	@$(PYTHON) -c "import slpp" 2>/dev/null && echo "  slpp: OK" || echo "  slpp: not found (run: make install-deps)"
	@echo ""
