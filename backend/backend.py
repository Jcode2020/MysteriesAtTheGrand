import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/health")
def health() -> tuple[object, int]:
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port_value = os.getenv("BACKEND_PORT", "5000")
    try:
        port = int(port_value)
    except ValueError as error:
        raise ValueError("BACKEND_PORT must be an integer") from error

    app.run(host=host, port=port)
