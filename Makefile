# WoW Stat Tracker Makefile
#
# Usage:
#   make help     - Show this help
#   make test     - Run tests with coverage
#   make build    - Build macOS app bundle
#   make format   - Format code with black
#   make lint     - Check code formatting
#   make clean    - Remove build artifacts

.PHONY: help test test-quick build format lint clean install-deps run all

# Default target
all: format lint test

help:
	@echo "WoW Stat Tracker - Available targets:"
	@echo ""
	@echo "  make test        - Run tests with coverage report"
	@echo "  make test-quick  - Run tests without coverage"
	@echo "  make build       - Build macOS app bundle"
	@echo "  make format      - Format code with black"
	@echo "  make lint        - Check code formatting (no changes)"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make install-deps - Install Python dependencies"
	@echo "  make run         - Run the application"
	@echo "  make all         - Format, lint, and test"
	@echo ""

# Find Python and tools
PYTHON := $(shell command -v python3 2>/dev/null)
BLACK := $(shell command -v black 2>/dev/null)
PYTEST := $(shell command -v pytest 2>/dev/null)

# Run tests with coverage
test:
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest test/ -v --cov=. --cov-report=html --cov-report=term-missing --cov-config=.coveragerc
	@echo ""
	@echo "Coverage report generated in htmlcov/"

# Run tests without coverage (faster)
test-quick:
	@echo "Running tests..."
	$(PYTHON) -m pytest test/ -v

# Build macOS app bundle
build:
	@echo "Building macOS app bundle..."
	./build_mac_app.sh

# Format code with black
format:
	@echo "Formatting code with black..."
	$(PYTHON) -m black wowstat.py test/ --line-length 88

# Check formatting without making changes
lint:
	@echo "Checking code formatting..."
	$(PYTHON) -m black wowstat.py test/ --check --line-length 88
	@echo "All files formatted correctly!"

# Remove build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ __pycache__/ test/__pycache__/
	rm -rf htmlcov/ .coverage .pytest_cache/
	rm -rf *.egg-info/ .eggs/
	rm -f *.pyc *.pyo
	@echo "Clean complete!"

# Install Python dependencies
install-deps:
	@echo "Installing dependencies..."
	pip3 install PyGObject pytest pytest-cov black
	@echo ""
	@echo "Note: GTK dependencies must be installed separately:"
	@echo "  macOS:  brew install gtk+3 gobject-introspection"
	@echo "  Ubuntu: sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0"

# Run the application
run:
	@echo "Starting WoW Stat Tracker..."
	$(PYTHON) wowstat.py

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
check-tools:
	@echo "Checking for required tools..."
	@command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
	@echo "  python3: $(PYTHON)"
	@command -v black >/dev/null 2>&1 && echo "  black: $(BLACK)" || echo "  black: not found (run: pip3 install black)"
	@command -v pytest >/dev/null 2>&1 && echo "  pytest: $(PYTEST)" || echo "  pytest: not found (run: pip3 install pytest)"
	@echo ""
