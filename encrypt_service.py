import logging
import os

from flask import Flask
from flasgger import Swagger
from flask_cors import CORS

from core.database import init_db

from routes.legacy_encrypt import bp as legacy_encrypt_bp
from routes.misc import bp as misc_bp
from routes.pdf import bp as pdf_bp
from routes.sign_link import bp as sign_link_bp
from routes.sign_xml import bp as sign_xml_bp
from routes.internal_keys import bp as internal_keys_bp
from routes.consume import bp as consume_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)
    Swagger(app, template_file="swaggerapi.yaml")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    init_db()

    app.register_blueprint(misc_bp)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(legacy_encrypt_bp)
    app.register_blueprint(sign_link_bp)
    app.register_blueprint(sign_xml_bp)
    app.register_blueprint(internal_keys_bp)
    app.register_blueprint(consume_bp)

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)