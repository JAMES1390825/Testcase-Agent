"""Blueprint registration helpers."""

from __future__ import annotations

from flask import Flask

from .generate import bp as generate_bp
from .enhance import bp as enhance_bp
from .health import bp as health_bp
from .jobs import bp as jobs_bp


def register_routes(app: Flask) -> None:
	app.register_blueprint(generate_bp)
	app.register_blueprint(enhance_bp)
	app.register_blueprint(health_bp)
	app.register_blueprint(jobs_bp)


__all__ = ["register_routes"]
