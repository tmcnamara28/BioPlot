"""Pytest configuration — set headless matplotlib backend for all tests."""
import matplotlib
matplotlib.use("Agg")
