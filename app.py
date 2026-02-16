from flask import Flask, render_template, request, redirect, session
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------- FILE VALIDATION ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- GOOGLE SHEETS SAFE CONNECTION ----------------
def get_sheet():
    try:
        google_creds = os.getenv("GOOGLE_CREDENTIALS")
        if not google_creds:
            return None

        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = json.loads(google_creds)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        return client.open("BenchSalesCRM").sheet1

    except Exception as e:
        print("Google Sheets Error:", e)
        return None


# ---------------- REGISTRATION ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        sheet = get_sheet()
        if sheet:
            sheet.append_row(["USER", username, password])
            message = "Registration Successful!"
        else:
            message = "Sheet not connected."

    return render_template("register.html", message=message)


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":
            session["user"] = username
            return redirect("/dashboard")
        else:
            return "Invalid Credentials"

    return render_template("login.html")


# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect("/")

    message = ""

    if request.method == "POST":
        vendor_email = request.form.get("email")
        consultant = request.form.get("consultant")
        rate = request.form.get("rate")
        client = request.form.get("client")

        file = request.files.get("resume")
        filename = ""

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        sheet = get_sheet()
        if sheet:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d"),
                vendor_email,
                consultant,
                rate,
                client,
                filename,
                "Submitted"
            ])
            message = "Data & Resume Saved Successfully!"
        else:
            message = "Google Sheet not connected."

    return render_template("dashboard.html", message=message)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
