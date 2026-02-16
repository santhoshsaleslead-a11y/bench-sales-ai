import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session
import openai
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Google Sheets Setup
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("BenchSalesCRM").sheet1

# Save to Google Sheet
sheet.append_row([
    datetime.now().strftime("%Y-%m-%d"),
    request.form.get("email"),
    "Consultant Name",
    "$75/hr",
    "Client Name",
    "85%",
    "Submitted"
])



# 🔑 Add your OpenAI Key
openai.api_key = "YOUR_OPENAI_API_KEY"


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

    ai_result = ""
    email_status = ""

    if request.method == "POST":

        # AI Resume Matching
        resume = request.form.get("resume")
        jd = request.form.get("jd")

        if resume and jd:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user",
                     "content": f"Match this resume:\n{resume}\n\nWith this job description:\n{jd}\n\nGive match percentage and missing skills."}
                ]
            )
            ai_result = response.choices[0].message.content

        # Email Automation
        email_to = request.form.get("email")
        if email_to:
            msg = MIMEText("Profile submission for your requirement.")
            msg["Subject"] = "Consultant Submission"
            msg["From"] = "yourgmail@gmail.com"
            msg["To"] = email_to

            try:
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login("yourgmail@gmail.com", "your_app_password")
                server.sendmail("yourgmail@gmail.com", email_to, msg.as_string())
                server.quit()
                email_status = "Email Sent Successfully!"
            except:
                email_status = "Email Failed!"

    return render_template("dashboard.html", ai_result=ai_result, email_status=email_status)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
