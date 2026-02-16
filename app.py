import os
import io
import json
import pdfplumber
import docx
import smtplib
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import gspread

app = FastAPI()

# ---------------- GOOGLE SETUP ----------------

def get_google_services():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    creds_dict = json.loads(creds_json)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

    sheet_client = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds)

    return sheet_client, drive_service


def get_sheet():
    client, _ = get_google_services()
    SHEET_NAME = "BenchSalesCRM"

    try:
        sheet = client.open(SHEET_NAME).sheet1
    except:
        spreadsheet = client.create(SHEET_NAME)
        sheet = spreadsheet.sheet1
        sheet.append_row([
            "Date",
            "Candidate",
            "Vendor Email",
            "Resume Drive Link"
        ])

    return sheet


# ---------------- RESUME TEXT EXTRACTION ----------------

def extract_text(file_bytes, filename):
    if filename.endswith(".pdf"):
        text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text

    elif filename.endswith(".docx"):
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([p.text for p in doc.paragraphs])

    return ""


# ---------------- DRIVE UPLOAD ----------------

def upload_to_drive(file_bytes, filename):
    _, drive = get_google_services()

    file_metadata = {"name": filename}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), resumable=True)

    file = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    file_id = file.get("id")

    drive.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"}
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"


# ---------------- EMAIL ----------------

def send_email(to_email, candidate):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("yourgmail@gmail.com", "yourapppassword")

        message = f"Subject: Candidate Submission\n\nPlease find profile of {candidate}."
        server.sendmail("yourgmail@gmail.com", to_email, message)
        server.quit()
    except Exception as e:
        print("Email error:", e)


# ---------------- SUBMIT API ----------------

@app.post("/submit")
async def submit(
    candidate: str = Form(...),
    vendor_email: str = Form(...),
    resume: UploadFile = File(...)
):
    sheet = get_sheet()

    # Duplicate Detection
    records = sheet.get_all_records()
    for row in records:
        if row["Candidate"] == candidate and row["Vendor Email"] == vendor_email:
            raise HTTPException(status_code=400, detail="Duplicate submission detected")

    file_bytes = await resume.read()

    # Upload to Drive
    drive_link = upload_to_drive(file_bytes, resume.filename)

    # Extract text (optional use later)
    resume_text = extract_text(file_bytes, resume.filename)

    # Save to Sheet
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d"),
        candidate,
        vendor_email,
        drive_link
    ])

    # Send Email
    send_email(vendor_email, candidate)

    return {
        "message": "Profile submitted successfully",
        "drive_link": drive_link
    }


# ---------------- DASHBOARD ----------------

@app.get("/dashboard")
def dashboard():
    sheet = get_sheet()
    total = len(sheet.get_all_records())
    return {"total_submissions": total}
