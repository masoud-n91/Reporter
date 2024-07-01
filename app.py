import os
import bcrypt
from flask import Flask, jsonify, flash, render_template, request, redirect, url_for, session as flask_session
from sqlmodel import Session, select
from pydantic import BaseModel
from ultralytics import YOLO
from database import get_user_by_username, create_user, get_patient_by_dossier, create_patient, get_reports, add_report, engine, User
import ast
import re
from datetime import date
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


app = Flask("Reporter")
app.secret_key = "my_secret_key"
app.config["UPLOAD_FOLDER"] = './uploads'
app.config["ALLOWED_EXTENSIONS"] = {'png', 'jpg', 'jpeg'}


object_detection_model = YOLO("yolov8n.pt")


# PyDantic models for request validation
class RegisterModel(BaseModel):
    name: str
    surname: str
    email: str
    username: str
    password: str
    check_password: str

class ReportModel(BaseModel):
    patient_id: int
    report_date: date
    report_text: str

class LoginModel(BaseModel):
    username: str
    password: str

class RegisterPatient(BaseModel):
    dossier: str
    name: str
    surname: str
    gender: str
    age: str


def allowed_file(filename):
    extention = filename.split('.')[-1]
    if extention not in app.config["ALLOWED_EXTENSIONS"]:
        return False
    else:
        return True


@app.route("/")
@app.route("/index")
def index():
    return render_template("index.html")


@app.route("/about-me")
def about_me():
    return render_template("about-me.html")


@app.route("/about-project")
def about_project():
    return render_template("about-project.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


@app.route("/signin", methods=['GET', 'POST'])
def signin():
    if request.method == "GET":
        return render_template("signin.html")
    
    elif request.method == "POST":
        try:
            login_data = LoginModel(
                username=request.form["username"],
                password=request.form["password"]
            )
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("signin"))
        
        user = get_user_by_username(login_data.username)
        if user:
            password_byte = login_data.password.encode("utf-8")
            if bcrypt.checkpw(password_byte, user.password):
                flask_session["user_id"] = user.id  # Using session to store user_id
                return redirect(url_for('profile'))
            else:
                flash("Wrong password", "danger")
                return redirect(url_for("signin"))
        else:
            flash("User not found", "danger")
            return redirect(url_for("signin"))


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("signup.html")
    elif request.method == "POST":
        try:
            register_data = RegisterModel(
                name=request.form["name"],
                surname=request.form["surname"],
                email=request.form["email"],
                username=request.form["username"],
                password=request.form["password"],
                check_password=request.form["check_password"]
            )
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for("register"))
        
        if register_data.password != register_data.check_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("register"))
        
        if not re.search(r'[A-Z]', register_data.password):
            flash("Uh Uh, no uPpercase in the password :D", "danger")
            return redirect(url_for("register"))
        
        if not re.search(r'\d', register_data.password):
            flash("Uh Uh, no digits in the password 0-o", "danger")
            return redirect(url_for("register"))
        
        if not re.search(r'[@$!%*?&]', register_data.password):
            flash("Uh Uh, no ch@racters in the password :)", "danger")
            return redirect(url_for("register"))
        
        if len(register_data.password) <= 12:
            flash("too short :p", "danger")
            return redirect(url_for("register"))

        with Session(engine) as db_session:
            # Check if the username already exists
            if get_user_by_username(register_data.username):
                flash("No No No, Username already exists", "danger")
                return redirect(url_for("register"))

            # Hash the password
            password_hash = bcrypt.hashpw(register_data.password.encode('utf-8'), bcrypt.gensalt())

            # Create user in the database
            create_user(db_session, register_data.name, register_data.surname, register_data.email, register_data.username, password_hash)

            flash("Sign up successful! Please log in.", "success")
            return redirect(url_for("signin"))


@app.route("/logout")
def logout():
    flask_session.pop("user_id")
    return redirect(url_for("index"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    generated_report = request.args.get('generated_report')

    with Session(engine) as db_session:
        user = db_session.get(User, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return render_template("profile.html", username=user.username, generated_report=generated_report)


@app.route("/patient-entry", methods=["GET", "POST"])
def patient_entry():
    if flask_session.get('user_id'):
        if request.method == "GET":
            return render_template("patient-entry.html")
        elif request.method == "POST":
            try:
                patient_data = RegisterPatient(
                    dossier=request.form["dossier"],
                    name=request.form["name"],
                    surname=request.form["surname"],
                    gender=request.form["gender"],
                    age=request.form["age"],
                )
            except Exception as e:
                flash(f"Error: {str(e)}", "danger")
                return redirect(url_for("patient-entry"))
            
            with Session(engine) as db_session:
                # Check if the patient already exists
                if get_patient_by_dossier(patient_data.dossier):
                    flash("a patient with this dossier number already exists", "danger")
                    return redirect(url_for("patient-entry"))
                
            create_patient(db_session, patient_data.dossier, patient_data.name, patient_data.surname, patient_data.gender, patient_data.age)

            flash("New patient added to the database successful!", "success")
            return redirect(url_for("profile"))

    else:
        return redirect(url_for("index"))


@app.route("/patient-history", methods=["GET", "POST"])
def patient_history():
    
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    if request.method == "GET":
        return render_template("patient-history.html")
    
    elif request.method == "POST":
        dossier_no = request.form["dossier"]

        patient = get_patient_by_dossier(dossier_no)
    
        if not patient:
            flash("Patient not found", "danger")
            return redirect(url_for("patient_history"))

        with Session(engine) as db_session:

            reports = get_reports(db_session, patient.id)

            if not reports:
                flash("No reports found for this patient", "danger")
                return redirect(url_for("patient_history"))
            else:
                list_reports = []
                list_patient = []
                for report in reports:
                    temp_dict = {}
                    temp_dict["report_date"] = report.report_date.strftime('%Y-%m-%d'),
                    temp_dict["report_text"] = report.report_text
                    list_reports.append(temp_dict)

                temp_dict = {}
                temp_dict["id"] = patient.id
                temp_dict["dossier"] = patient.dossier
                temp_dict["name"] = patient.name
                temp_dict["surname"] = patient.surname
                temp_dict["gender"] = patient.gender
                temp_dict["age"] = patient.age
                list_patient.append(temp_dict)
                
                return redirect(url_for("show_patient_reports", patient=str(list_patient), reports=str(list_reports)))
    

@app.route("/show-patient-reports")
def show_patient_reports():

    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    if request.method == "GET":

        patient_str = request.args.get('patient')
        reports_str = request.args.get('reports')

        patient = str2list(patient_str)
        
        reports = str2list(reports_str)

        return render_template("show-patient-reports.html", patient=patient, reports=reports, enumerate=enumerate, url_for=url_for)

def str2list(string):
    try:
        result = ast.literal_eval(string)
        if isinstance(result, list):
            return result
        else:
            raise ValueError("The provided string does not represent a list.")
    except (ValueError, SyntaxError) as e:
        print(f"Error converting string to list: {e}")
        return None
    

@app.route("/report-generation", methods=["GET", "POST"])
def report_generation():
    
    user_id = flask_session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    if request.method == "GET":
        return render_template("report-generation.html")
    
    elif request.method == "POST":
        dossier_no = request.form["dossier"]
        patient = get_patient_by_dossier(dossier_no)

        if not patient:
            flash("Patient not found", "danger")
            return redirect(url_for("report_generation"))
        
        list_patient = []
        temp_dict = {}
        temp_dict["id"] = patient.id
        temp_dict["dossier"] = patient.dossier
        temp_dict["name"] = patient.name
        temp_dict["surname"] = patient.surname
        temp_dict["gender"] = patient.gender
        temp_dict["age"] = patient.age
        list_patient.append(temp_dict)

        my_image = request.files['image']
        if not my_image.filename == "":
            if my_image and allowed_file(my_image.filename):
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], my_image.filename)
                my_image.save(save_path)
                results = object_detection_model(save_path)

                detected_objects = {}
                names = object_detection_model.names
                for r in results:
                    for c in r.boxes.cls:
                        if names[int(c)] not in detected_objects:
                            detected_objects[names[int(c)]] = 1
                        else:
                            detected_objects[names[int(c)]] += 1

                report = generate_report(detected_objects, list_patient[0])

                save_report(report, list_patient[0])

                return redirect(url_for('profile', generated_report=report))
            
        return redirect(url_for('profile'))
    

def save_report(report:str, patient:dict):
    print("save_report 1------------------------------------------------")
    # try:
    report_data = ReportModel(
        patient_id=patient["id"],
        report_date=date.today(),
        report_text=report
    )
    # except Exception as e:
    #     print("save_report 2------------------------------------------------")

    #     flash(f"Error: {str(e)}", "danger")
    #     return redirect(url_for("report_generation"))
    
    with Session(engine) as db_session:

        print("save_report 3------------------------------------------------")

        print("report_data: ", report_data)
        add_report(db_session, report_data.patient_id, report_data.report_date, report_data.report_text)

        print("save_report 4------------------------------------------------")

        flash("New Report entered!", "success")
    

def generate_report(objects:dict, patient:dict):

    generation_config = {
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 4096,
    }

    safety_settings = [
        {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
        },
        {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
        },
        {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
        },
        {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
        },
    ]

    sys_prompt = f"""
    You are a hilarious chatbot that helps to identify objects in an image.
    A list of objects related to a patient will be provided.
    Use the information to say what you can see in the image in a funny way.
    
    ** "OBJECTS": {objects}
    ** "PATIENT": {patient}
    """

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro-latest",
        safety_settings=safety_settings,
        generation_config=generation_config,
        system_instruction=sys_prompt,
    )

    chat_session = model.start_chat()

    response = chat_session.send_message("Hey man, what do you see in this image?")

    return response.text
    
