import os
import shutil
import pdfplumber
import docx
from datetime import datetime, timedelta
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from passlib.context import CryptContext
from jose import jwt
from dotenv import load_dotenv
import smtplib

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

SECRET_KEY = "SUPERSECRETKEY"
ALGORITHM = "HS256"


# ------------------ DATABASE MODELS ------------------

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    password = Column(String)


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(Integer, primary_key=True)
    candidate = Column(String)
    vendor_email = Column(String)
    resume_file = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# ------------------ AUTH ------------------

def create_token(data: dict):
    expire = datetime.utcnow() + timedelta(hours=10)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        return user
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


# ------------------ REGISTER ------------------

@app.post("/register")
def register(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    hashed = pwd_context.hash(password)
    user = User(email=email, password=hashed)
    db.add(user)
    db.commit()
    return {"message": "User registered successfully"}


# ------------------ LOGIN ------------------

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()

    if not user or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_token({"sub": user.email})
    return {"access_token": token}


# ------------------ RESUME TEXT EXTRACTION ------------------

def extract_text(file_path):
    if file_path.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([p.text for p in doc.paragraphs])
    return ""


# ------------------ SUBMIT PROFILE ------------------

@app.post("/submit")
def submit_profile(
    candidate: str = Form(...),
    vendor_email: str = Form(...),
    resume: UploadFile = File(...),
    user=Depends(get_current_user)
):
    db = SessionLocal()

    # Duplicate Detection
    existing = db.query(Submission).filter(
        Submission.candidate == candidate,
        Submission.vendor_email == vendor_email
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Duplicate submission detected")

    # Save File
    os.makedirs("resumes", exist_ok=True)
    file_path = f"resumes/{resume.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)

    # Extract Text
    resume_text = extract_text(file_path)

    # Save to DB
    submission = Submission(
        candidate=candidate,
        vendor_email=vendor_email,
        resume_file=resume.filename
    )
    db.add(submission)
    db.commit()

    # Auto Email Send
    send_email(vendor_email, candidate)

    return {"message": "Profile submitted successfully"}


# ------------------ EMAIL FUNCTION ------------------

def send_email(to_email, candidate):
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))

        message = f"Subject: Candidate Submission\n\nPlease find profile of {candidate}."
        server.sendmail(os.getenv("EMAIL_USER"), to_email, message)
        server.quit()
    except Exception as e:
        print("Email error:", e)


# ------------------ ADMIN DASHBOARD ------------------

@app.get("/dashboard")
def dashboard(user=Depends(get_current_user)):
    db = SessionLocal()
    total = db.query(Submission).count()
    return {
        "total_submissions": total
    }
