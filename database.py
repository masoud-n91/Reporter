from sqlmodel import Field, SQLModel, create_engine, Session, select, Relationship
from typing import List, Optional
from datetime import date

class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    surname: str
    email: str
    username: str
    password: str

class Patient(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    dossier: str
    name: str
    surname: str
    gender: str
    age: int

    reports: List["Report"] = Relationship(back_populates="patient")


class Report(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    report_date: date
    report_text: str

    patient: Optional[Patient] = Relationship(back_populates="reports")


DATABASE_URL = 'sqlite:///./database.db'
# DATABASE_URL = 'postgresql://root:n1pWuZc7GruapxRavKzYp2Lu@chatbotdb:5432/postgres'
engine = create_engine(DATABASE_URL, echo=True)

# Create the database tables
SQLModel.metadata.create_all(engine)


def get_user_by_username(username: str):
    with Session(engine) as db_session:
        statement = select(User).where(User.username == username)
        return db_session.exec(statement).first()
    

def create_user(db_session, name, surname, email, username, password):
    user = User(name=name, surname=surname, email=email, username=username, password=password)
    with Session(engine) as db_session:
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def get_patient_by_dossier(dossier: str):
    with Session(engine) as db_session:
        statement = select(Patient).where(Patient.dossier == dossier)
        return db_session.exec(statement).first()


def create_patient(db_session, dossier, name, surname, gender, age):
    patient = Patient(dossier=dossier, name=name, surname=surname, gender=gender, age=age)
    with Session(engine) as db_session:
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)
    return patient


def get_reports(db_session, patient_id):
    statement = select(Report).where(Report.patient_id == patient_id)
    return db_session.exec(statement).all()


def add_report(db_session, patient_id, report_date, report_text):

    print("patient_id: ", patient_id, flush=True)
    print("type(patient_id): ", type(patient_id), flush=True)
    print("report_date: ", report_date, flush=True)
    print("type(report_date): ", type(report_date), flush=True)
    print("report_text: ", report_text, flush=True)
    print("type(report_text): ", type(report_text), flush=True)


    report = Report(patient_id=patient_id, report_date=report_date, report_text=report_text)
    with Session(engine) as db_session:
        db_session.add(report)
        db_session.commit()
        db_session.refresh(report)
    return report

