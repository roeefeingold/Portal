import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")

db_user = os.environ.get("POSTGRES_USER", "portal")
db_pass = os.environ.get("POSTGRES_PASSWORD", "portal")
db_host = os.environ.get("POSTGRES_HOST", "db")
db_name = os.environ.get("POSTGRES_DB", "portal")
app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"
app.config["UPLOAD_FOLDER"] = "/app/static/uploads"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin3")

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg", "webp"}


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    image = db.Column(db.String(300), default="")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


with app.app_context():
    db.create_all()


@app.route("/")
def index():
    links = Link.query.order_by(Link.id).all()
    is_admin = session.get("admin", False)
    return render_template("index.html", links=links, is_admin=is_admin)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("index"))
        flash("Wrong password")
    return render_template("login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("index"))


@app.route("/admin/add", methods=["POST"])
def add_link():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    name = request.form.get("name", "").strip()
    url_val = request.form.get("url", "").strip()
    if not name or not url_val:
        flash("Name and URL are required")
        return redirect(url_for("index"))
    image_path = ""
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image_path = filename
    link = Link(name=name, url=url_val, image=image_path)
    db.session.add(link)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/admin/edit/<int:link_id>", methods=["POST"])
def edit_link(link_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    link = Link.query.get_or_404(link_id)
    link.name = request.form.get("name", link.name).strip()
    link.url = request.form.get("url", link.url).strip()
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            link.image = filename
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/admin/delete/<int:link_id>", methods=["POST"])
def delete_link(link_id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    link = Link.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
