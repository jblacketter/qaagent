"""Sample Flask application for testing route discovery."""
from flask import Flask, Blueprint, jsonify, request

app = Flask(__name__)


def login_required(f):
    """Dummy auth decorator."""
    return f


# Direct app routes
@app.route("/health")
def health_check():
    return jsonify(status="ok")


@app.route("/login", methods=["POST"])
def login():
    return jsonify(token="abc")


# Blueprint with prefix
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


@api_bp.route("/items")
def list_items():
    return jsonify([])


@api_bp.route("/items/<int:item_id>")
def get_item(item_id):
    return jsonify(name="test")


@api_bp.route("/items", methods=["POST"])
@login_required
def create_item():
    return jsonify(created=True)


@api_bp.route("/items/<int:item_id>", methods=["PUT", "PATCH"])
@login_required
def update_item(item_id):
    return jsonify(updated=True)


@api_bp.route("/items/<int:item_id>", methods=["DELETE"])
@login_required
def delete_item(item_id):
    return jsonify(deleted=True)


# Users blueprint
users_bp = Blueprint("users", __name__, url_prefix="/api/v1/users")


@users_bp.route("/")
def list_users():
    return jsonify([])


@users_bp.route("/<uuid:user_id>")
def get_user(user_id):
    return jsonify({})


app.register_blueprint(api_bp)
app.register_blueprint(users_bp)
