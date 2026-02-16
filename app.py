from flask import Flask, render_template, request, redirect, session
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"


# ---------------- GOOGLE SHEETS SAFE CONNECTION ----------------
def get_sheet():
    try:
        google_creds = os.getenv("GOOGLE_CREDENTIALS")
        if not google_creds:
            print("No GOOGLE_CREDENTIALS found")
            return None

        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds_dict = json.loads(google_creds)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)

        return client.open("BenchSalesCRM").sheet1

    except Exception as e:
        print("Google Sheets Error:", e)
        return None


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

        sheet = get_sheet()

        if sheet:
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d"),
                vendor_email,
                consultant,
                rate,
                client,
                "Submitted"
            ])
            message = "Saved to Google Sheet Successfully!"
        else:
            message = "Google Sheet not connected."

    return render_template("dashboard.html", message=message)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


# ---------------- RUN FOR RENDER ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
