"""Launcher for running the backend package from the project root.

Usage (from project root, venv activated):
    python run_backend.py

This runs `backend.main` using package-based imports so `backend` is resolvable.
"""
import runpy


def main():
    runpy.run_module("backend.main", run_name="__main__")


if __name__ == "__main__":
    main()
