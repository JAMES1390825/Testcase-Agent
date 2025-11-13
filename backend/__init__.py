"""Application factory for the Testcase Agent backend."""

from __future__ import annotations

from pathlib import Path

from flask import Flask

from backend.config import BASE_DIR
from backend.routes import register_routes
from backend.services import load_prompt_templates
from backend.services import db as db_mod
from backend.services import embeddings as emb_mod


FRONTEND_DIR = BASE_DIR / "frontend"


def create_app() -> Flask:
	app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")

	app.config["PROMPT_TEMPLATES"] = load_prompt_templates()

	# Initialize database (no-op if DATABASE_URL not set)
	db_mod.init_db(echo=False)
	
	# Initialize embedding client (no-op if EMBEDDING_API_KEY not set)
	emb_mod.init_embedding_client()

	register_routes(app)

	@app.route("/")
	def index():
		return app.send_static_file("index.html")

	return app


__all__ = ["create_app"]
