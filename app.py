from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = "secretkey"


# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect('database.db')



# ---------- CREATE TABLES ----------
conn = sqlite3.connect('database.db')

conn.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    password TEXT,
    role TEXT
)
''')

conn.execute('''
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER,
    condition TEXT,
    risk INTEGER,
    priority TEXT,
    next_visit TEXT,
    call_status TEXT,
    call_reason TEXT,
    call_id TEXT,
    email TEXT
)
''')

conn.commit()
conn.close()


# ---------- LOGIN PAGE ----------
@app.route('/')
def login():
    return render_template('login.html')


# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password'].strip()
        role = request.form['role']

        if "@gmail.com" not in email:
            return redirect('/register?error=email')

        if len(password) < 6:
            return redirect('/register?error=password')

        conn = get_db()

        existing = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        if existing:
            return redirect('/register?error=exists')

        conn.execute(
            "INSERT INTO users (email, password, role) VALUES (?, ?, ?)",
            (email, password, role)
        )

        conn.commit()
        conn.close()

        return redirect('/?success=1')

    return render_template('register.html')


# ---------- LOGIN CHECK ----------
@app.route('/login_check', methods=['POST'])
def login_check():
    email = request.form['email'].strip().lower()
    password = request.form['password'].strip()
    role = request.form.get('role')

    if not email or not password:
        return redirect('/?error=empty')

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    ).fetchone()

    conn.close()

    if not user:
        return redirect('/?error=invalid')

    if user[3] != role:
        return redirect('/?error=role')

    session['user'] = email
    session['role'] = role

    if role == "admin":
        return redirect('/dashboard')
    else:
        return redirect('/patient')


# ---------- RISK ----------
def calculate_risk(age, condition):
    risk = 0
    if age > 60:
        risk += 2
    if condition.lower() in ['cancer', 'heart', 'icu']:
        risk += 3
    return risk




# ---------- CALL LOGIC ----------
def get_call_result(next_visit, is_rescheduled):
    today = datetime.now().date()
    visit_date = datetime.strptime(next_visit, "%Y-%m-%d").date()

    # ✅ PRIORITY: RESCHEDULE CHECK FIRST
    if is_rescheduled == 1:
        return "Connected", "Rescheduled"

    # ✅ ON TIME
    if visit_date >= today:
        return "Connected", "On Time"

    # ✅ MISSED CASE → USE 8086
    days_missed = (today - visit_date).days

    status, reason = run_8086(days_missed)

    return status, reason

    if days_missed <= 0:
        return "Connected", "On Time"
    elif days_missed > 5:
        return "Missed", "Switched Off"
    elif days_missed > 2:
        return "Missed", "No Answer"
    elif days_missed > 0:
        return "Missed", ";Late"


# ---------- 🔥 ADD-ON: PREDICTIVE LOGIC ----------
def calculate_risk_score(p):
    score = 0

    if p[7] == "Missed":
        score += 3

    from datetime import date, datetime
    visit_date = datetime.strptime(p[6], "%Y-%m-%d").date()
    if visit_date < date.today():
        score += 2

    if p[5] == "Critical":
        score += 1

    if int(p[2]) > 60:
        score += 1

    return score


def predict_status(score):
    if score <= 2:
        return "Safe"
    elif score <= 5:
        return "Risk"
    else:
        return "Likely to Miss"


# ---------- ADD PATIENT ----------
@app.route('/add', methods=['GET', 'POST'])
def add_patient():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        name = request.form['name']
        age = int(request.form['age'])
        condition = request.form['condition']
        next_visit = request.form['next_visit']
        email = request.form.get('email')
        priority = run_priority(age, condition)
        risk = calculate_risk(age, condition)  # optional (keep if needed)

        rand = random.random()

        if rand < 0.4:
            call_status = "Connected"
            call_reason = "On Time"
        elif rand < 0.7:
            call_status = "Busy"
            call_reason = "Retry"
        else:
            call_status = "Missed"
            call_reason = "No Response"

        call_id = "CALL" + str(random.randint(1000, 9999))

        conn = get_db()
        conn.execute("""
            INSERT INTO patients 
            (name, age, condition, risk, priority, next_visit, call_status, call_reason, call_id, email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, age, condition, risk, priority, next_visit, call_status, call_reason, call_id, email))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template('add.html')


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():

    conn = get_db()
    patients = conn.execute("SELECT * FROM patients").fetchall()

    from datetime import date
    today = date.today().isoformat()

    total = len(patients)
    critical = len([p for p in patients if p[5] == "Critical"])
    upcoming = len([p for p in patients if p[6] and p[6] > today])

    # 🔥 ADD-ON
    predictions = []
    for p in patients:
        score = calculate_risk_score(p)
        prediction = predict_status(score)
        predictions.append(prediction)

    conn.close()

    return render_template(
        "dashboard.html",
        patients=patients,
        total=total,
        critical=critical,
        upcoming=upcoming,
        escalations=patients,
        predictions=predictions
    )


# ---------- PATIENT ----------
from datetime import datetime, date

@app.route('/patient')
def patient():

    if 'user' not in session:
        return redirect('/')

    conn = get_db()
    p = conn.execute(
        "SELECT * FROM patients WHERE email=?",
        (session['user'],)
    ).fetchone()
    conn.close()

    status = "Unknown"
    call_status = "Unknown"
    reason = ""

    if p and p[6]:
        visit_date = datetime.strptime(p[6], "%Y-%m-%d").date()
        today = date.today()

        if visit_date > today:
            status = "Upcoming"
            call_status = "Not Called"
            reason = "Scheduled"

        elif visit_date == today:
            status = "Today"
            call_status, reason = get_call_result(p[6],p[11])

        else:
            status = "Missed"
            call_status, reason = get_call_result(p[6],p[11])

    # 🔥 ADD-ON
    prediction = "Unknown"
    if p:
        score = calculate_risk_score(p)
        prediction = predict_status(score)

    return render_template(
        "patient_dashboard.html",
        p=p,
        status=status,
        call_status=call_status,
        reason=reason,
        prediction=prediction
    )


# ---------- LOGS ----------
@app.route('/logs')
def logs():
    if 'user' not in session:
        return redirect('/')

    conn = get_db()
    data = conn.execute(
        "SELECT * FROM patients ORDER BY id DESC"
    ).fetchall()
    conn.close()

    updated_logs = []

    for p in data:
        
        status, reason = get_call_result(p[6],p[11])

        # 🔥 ADD-ON
        score = calculate_risk_score(p)
        prediction = predict_status(score)

        updated_logs.append((
            p[0], p[1], p[2], p[3], p[4], p[5],
            status, reason,
            p[8] if len(p) > 8 else "",
            prediction
        ))

    return render_template('logs.html', logs=updated_logs)


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/emergency')
def emergency():
    return """
    <body style="background:black; color:red; text-align:center; font-family:sans-serif;">
        <h1 style="margin-top:100px; font-size:50px;">🚨 EMERGENCY 🚨</h1>
        <p style="font-size:24px;">Immediate Attention Required</p>

        <script>
            setTimeout(() => {
                window.location.href = "/dashboard";
            }, 4000);  // ⏱ goes back after 4 sec
        </script>
    </body>
    """
from datetime import datetime, date

@app.route('/appointment')
def appointment():
    if 'user' not in session:
        return redirect('/')

    email = session['user']

    conn = get_db()
    p = conn.execute(
        "SELECT * FROM patients WHERE email=?",
        (email,)
    ).fetchone()
    conn.close()

    # ✅ EVERYTHING BELOW MUST BE INSIDE FUNCTION

    status = "Unknown"

    if p and p[6]:
        visit_date = datetime.strptime(p[6], "%Y-%m-%d").date()
        today = date.today()

        if visit_date > today:
            status = "Upcoming"
        elif visit_date == today:
            status = "Today"
        else:
            status = "Missed"

    return render_template("appointment.html", p=p, status=status)
@app.route('/contact')
def contact():
    return render_template('contact.html')
from flask import jsonify, request, session

@app.route('/update_appointment', methods=['POST'])
def update_appointment():
    email = session.get("user")

    if not email:
        return jsonify({
            "success": False,
            "message": "❌ User not logged in"
        })

    new_date = request.json.get("date")

    if not new_date:
        return jsonify({
            "success": False,
            "message": "❌ Please select a date"
        })

    conn = get_db()

    # ✅ Check doctor availability
    existing = conn.execute(
        "SELECT * FROM patients WHERE next_visit=?",
        (new_date,)
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({
            "success": False,
            "message": "❌ Doctor not available on this date. Choose another date."
        })

    # ✅ Update appointment
    conn.execute(
        "UPDATE patients SET next_visit=?, is_rescheduled=1 WHERE email=?",
        (new_date, email)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"✅ Appointment rescheduled to {new_date}"
    })
import os
import subprocess
import time

import subprocess
import time
import os

def run_8086(days):

    # ✅ WRITE INPUT TO EMU FOLDER
    with open(r"C:\emu8086\MyBuild\input.txt", "w") as f:
        f.write(str(days))

    # ✅ OPEN EMU
    subprocess.Popen([
        r"C:\emu8086\emu8086.exe"
    ])

    time.sleep(3)

    file_path = r"C:\emu8086\MyBuild\output.txt"

    # ✅ CHECK FILE
    if not os.path.exists(file_path):
        return "Missed", "No Output Generated"

    with open(file_path) as f:
        result = f.read().strip()

    if result == "":
        return "Missed", "No Execution"

    # ✅ MAP OUTPUT
    mapping = {
        '1': ("Connected", "On Time"),
        '2': ("Missed", "Delayed Response"),
        '3': ("Missed", "No Response"),
        '4': ("Missed", "Device Unreachable")
    }
    

    return mapping.get(result, ("Missed", "Unknown"))
import os
import subprocess
import time

import subprocess
import time
import os

def run_priority(age, condition):
    mapping = {
        "normal": 0,
        "heart": 1,
        "cancer": 2,
        "icu": 3
    }

    cond_val = mapping.get(condition.lower(), 0)

    input_path = r"C:\emu8086\MyBuild\input.txt"
    output_path = r"C:\emu8086\MyBuild\output.txt"

    # ✅ Write input
    with open(input_path, "w") as f:
        f.write(f"{age} {cond_val}")

    print("➡️ Input written. Open EMU and run program.")

    # ✅ OPEN EMU WITH FILE
    subprocess.Popen([
        r"C:\emu8086\emu8086.exe",
        r"C:\emu8086\MyBuild\priority.asm"
    ])

    # ⏳ WAIT for YOU to run it
    time.sleep(6)

    # ✅ READ OUTPUT
    if not os.path.exists(output_path):
        print("❌ output.txt not found")
        return "Normal"

    with open(output_path) as f:
        result = f.read().strip()

    print("⬅️ Output:", result)

    priority_map = {
        '1': "Critical",
        '2': "Moderate",
        '3': "Normal"
    }

    return priority_map.get(result, "Normal")
@app.route('/delete/<int:id>')
def delete_patient(id):
    if 'user' not in session:
        return redirect('/')

    conn = get_db()
    conn.execute("DELETE FROM patients WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/dashboard')

# ---------- RUN ----------
app.run(debug=True)