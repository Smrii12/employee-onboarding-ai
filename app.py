from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'employee-onboarding-secret-key-2023'
app.config['DATABASE'] = 'employee_onboarding.db'
CORS(
    app,
    supports_credentials=True,
    origins=["http://127.0.0.1:5000", "http://localhost:5000"]
)


# Database initialization
# Database initialization
def init_db():
    with app.app_context():
        conn = get_db()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        
        # Create employees table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id TEXT UNIQUE NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                position TEXT NOT NULL,
                department TEXT NOT NULL,
                start_date TEXT NOT NULL,
                forms_completed INTEGER DEFAULT 0,
                total_forms INTEGER DEFAULT 1,
                videos_completed INTEGER DEFAULT 0,
                total_videos INTEGER DEFAULT 1,
                documents_uploaded INTEGER DEFAULT 0,
                total_documents INTEGER DEFAULT 1
            )
        ''')
        
        # Create tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emp_id TEXT NOT NULL,
                emp_name TEXT NOT NULL,
                task_name TEXT NOT NULL,
                category TEXT NOT NULL,
                assigned_by TEXT NOT NULL,
                assigned_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT DEFAULT 'Assigned',
                FOREIGN KEY (emp_id) REFERENCES employees (emp_id) ON DELETE CASCADE
            )
        ''')
        
        # Create training_videos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                duration TEXT NOT NULL,
                category TEXT NOT NULL,
                upload_date TEXT NOT NULL,
                url TEXT DEFAULT ''   -- added url column
            )
        ''')

        # ✅ Insert default users only if empty
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                [
                    ('admin', 'admin123', 'admin'),
                    ('hr', 'hr123', 'hr')
                ]
            )

        conn.commit()

# Database connection helper
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  
    return conn

# Authentication decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return jsonify({'success': True, 'redirect': '/admin'})
        
        return jsonify({'success': False, 'error': 'Invalid credentials'})
    
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('admin_dashboard.html')

# API Routes for Employees
@app.route('/api/employees', methods=['GET'])
@login_required
def get_employees():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees")
    employees = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(employees)

# @app.route('/api/employees/<emp_id>', methods=['GET'])
# @login_required
# def get_employee(emp_id):
#     conn = get_db()
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM employees WHERE emp_id = ?", (emp_id,))
#     employee = cursor.fetchone()
#     conn.close()
    
#     if employee:
#         emp_dict = dict(employee)

#         # ✅ Add progress object for frontend checkboxes
#         emp_dict["progress"] = {
#             "forms_completed": emp_dict.get("forms_completed", 0),
#             "total_forms": emp_dict.get("total_forms", 5),
#             "videos_completed": emp_dict.get("videos_completed", 0),
#             "total_videos": emp_dict.get("total_videos", 4),
#             "documents_uploaded": emp_dict.get("documents_uploaded", 0),
#             "total_documents": emp_dict.get("total_documents", 6),
#         }

#         return jsonify(emp_dict)
    
#     return jsonify({'error': 'Employee not found'}), 404

@app.route('/api/employees', methods=['POST'])
@login_required
def add_employee():
    data = request.get_json()
    
    # Generate a new employee ID
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(CAST(SUBSTR(emp_id, 4) AS INTEGER)) FROM employees")
    max_id = cursor.fetchone()[0] or 0
    new_emp_id = f"EMP{str(max_id + 1).zfill(3)}"
    
    cursor.execute('''
        INSERT INTO employees 
        (emp_id, first_name, last_name, email, position, department, start_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (new_emp_id, data['firstName'], data['lastName'], data['email'], 
         data['position'], data['department'], data['startDate']))
    
    conn.commit()
    
    # Get the newly created employee
    cursor.execute("SELECT * FROM employees WHERE emp_id = ?", (new_emp_id,))
    new_employee = dict(cursor.fetchone())
    conn.close()
    
    return jsonify(new_employee), 201

@app.route('/api/employees/<emp_id>', methods=['PUT'])
@login_required
def update_employee(emp_id):
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE employees 
        SET first_name = ?, last_name = ?, email = ?, position = ?, department = ?, start_date = ?,
            forms_completed = ?, videos_completed = ?, documents_uploaded = ?
        WHERE emp_id = ?
    ''', (data['firstName'], data['lastName'], data['email'], data['position'], 
         data['department'], data['startDate'], data.get('forms_completed', 0),
         data.get('videos_completed', 0), data.get('documents_uploaded', 0), emp_id))
    
    conn.commit()
    
    # Get the updated employee
    cursor.execute("SELECT * FROM employees WHERE emp_id = ?", (emp_id,))
    updated_employee = dict(cursor.fetchone())
    conn.close()
    
    return jsonify(updated_employee)

@app.route('/api/employees/<emp_id>', methods=['DELETE'])
@login_required
def delete_employee(emp_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employees WHERE emp_id = ?", (emp_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Employee deleted'})

# API Routes for Tasks
@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    emp_id = request.args.get('emp_id')
    
    conn = get_db()
    cursor = conn.cursor()
    
    if emp_id:
        cursor.execute("SELECT * FROM tasks WHERE emp_id = ?", (emp_id,))
    else:
        cursor.execute("SELECT * FROM tasks")
    
    tasks = [dict(row) for row in cursor.fetchall()]

    for task in tasks:
        # Use try/except to prevent crashing
        try:
            task['auto_status'] = classify_task(task)
        except Exception as e:
            print(f"[ERROR] Task ID {task.get('id')} classification failed:", e)
            task['auto_status'] = "Unknown"
    
    conn.close()
    
    return jsonify(tasks)


@app.route('/api/tasks', methods=['POST'])
@login_required
def add_task():
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tasks 
        (emp_id, emp_name, task_name, category, assigned_by, assigned_date, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['emp_id'], data['emp_name'], data['task_name'], data['category'],
         data['assigned_by'], datetime.now().strftime('%Y-%m-%d'), data['due_date'], 'Assigned'))
    
    conn.commit()
    
    # Get the newly created task
    task_id = cursor.lastrowid
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    new_task = dict(cursor.fetchone())
    conn.close()
    
    return jsonify(new_task), 201

# def classify_task(task):
#     """
#     Classifies task based on status and days since assigned
#     Returns: 'On Track', 'At Risk', or 'Delayed'
#     """
#     from datetime import datetime, timedelta

#     assigned_date = datetime.strptime(task['assigned_date'], '%Y-%m-%d').date()
#     today = datetime.now().date()
#     days_passed = (today - assigned_date).days

#     if task['status'] == 'Completed':
#         return 'On Track'  # or 'Completed'
#     elif days_passed > 5:
#         return 'Delayed'
#     elif days_passed > 2:
#         return 'At Risk'
#     else:
#         return 'On Track'


@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get existing task
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    # Prepare updated values (keep old values if key not sent)
    emp_id = data.get('emp_id', task['emp_id'])
    emp_name = data.get('emp_name', task['emp_name'])
    task_name = data.get('task_name', task['task_name'])
    category = data.get('category', task['category'])
    assigned_by = data.get('assigned_by', task['assigned_by'])
    due_date = data.get('due_date', task['due_date'])
    status = data.get('status', task['status'])
    
    cursor.execute('''
        UPDATE tasks 
        SET emp_id = ?, emp_name = ?, task_name = ?, category = ?, assigned_by = ?, 
            due_date = ?, status = ?
        WHERE id = ?
    ''', (emp_id, emp_name, task_name, category, assigned_by, due_date, status, task_id))
    
    conn.commit()
    
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_task = dict(cursor.fetchone())
    conn.close()
    
    return jsonify(updated_task)


@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Task deleted'})

# API Routes for Training Videos
@app.route('/api/training-videos', methods=['GET'])
@login_required
def get_training_videos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM training_videos")
    videos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(videos)

# API Route for Stats
@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    conn = get_db()
    cursor = conn.cursor()
    
    # Get active employees count
    cursor.execute("SELECT COUNT(*) FROM employees")
    active_employees = cursor.fetchone()[0]
    
    # Get completed onboardings (all tasks completed)
    cursor.execute('''
        SELECT COUNT(*) FROM employees 
        WHERE forms_completed = total_forms 
        AND videos_completed = total_videos 
        AND documents_uploaded = total_documents
    ''')
    completed_onboardings = cursor.fetchone()[0]
    
    # Get pending tasks
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != 'Completed'")
    pending_tasks = cursor.fetchone()[0]
    
    # Get overdue tasks (simplified logic)
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE due_date < date('now') AND status != 'Completed'")
    overdue_tasks = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'activeEmployees': active_employees,
        'activeChange': 2,  # Example data
        'completedThisMonth': completed_onboardings,
        'completionRate': 75,  # Example data
        'pendingTasks': pending_tasks,
        'overdueTasks': overdue_tasks,
        'avgCompletionTime': 14  # Example data in days
    })

@app.route('/api/employees/<emp_id>', methods=['GET'])
@login_required
def get_employee(emp_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM employees WHERE emp_id = ?", (emp_id,))
    employee = cursor.fetchone()
    conn.close()
    
    if employee:
        emp_dict = dict(employee)

        # 🔥 Dynamic totals (match # of checkboxes)
        total_forms = 1
        total_videos = 1
        total_documents = 1

        emp_dict["progress"] = {
            "forms_completed": emp_dict.get("forms_completed", 0),
            "total_forms": total_forms,
            "videos_completed": emp_dict.get("videos_completed", 0),
            "total_videos": total_videos,
            "documents_uploaded": emp_dict.get("documents_uploaded", 0),
            "total_documents": total_documents,
        }

        return jsonify(emp_dict)
    
    return jsonify({'error': 'Employee not found'}), 404


@app.route('/api/employees/<emp_id>/progress', methods=['PUT'])
@login_required
def update_progress(emp_id):
    data = request.get_json()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE employees 
        SET forms_completed = ?, videos_completed = ?, documents_uploaded = ?
        WHERE emp_id = ?
    ''', (
        data.get('forms_completed', 0),
        data.get('videos_completed', 0),
        data.get('documents_uploaded', 0),
        emp_id
    ))

    conn.commit()

    cursor.execute("SELECT forms_completed, total_forms, videos_completed, total_videos, documents_uploaded, total_documents FROM employees WHERE emp_id = ?", (emp_id,))
    progress = dict(cursor.fetchone())
    conn.close()

    return jsonify(progress)

# API Route to add a new training video
@app.route('/api/training-videos', methods=['POST'])
@login_required
def add_training_video():
    data = request.get_json()
    
    # Simple validation
    if not data.get('title') or not data.get('duration') or not data.get('category'):
        return jsonify({'error': 'Title, duration, and category are required'}), 400
    
    upload_date = data.get('upload_date', datetime.now().strftime('%Y-%m-%d'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO training_videos (title, duration, category, upload_date,url)
        VALUES (?, ?, ?, ?,?)
    ''', (data['title'], data['duration'], data['category'], upload_date,data['url']))
    
    conn.commit()
    
    # Fetch the newly added video
    video_id = cursor.lastrowid
    cursor.execute("SELECT * FROM training_videos WHERE id = ?", (video_id,))
    new_video = dict(cursor.fetchone())
    conn.close()
    
    return jsonify(new_video), 201


# Check if user is authenticated
@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    if 'username' in session:
        return jsonify({'authenticated': True, 'username': session['username']})
    return jsonify({'authenticated': False}), 401

# Insert default training videos if table is empty
def insert_default_videos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM training_videos")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO training_videos (title, duration, category, upload_date, url) VALUES (?, ?, ?, ?, ?)",
            [
                ("Ultimez-A journey to build beyond", "5:35", "Onboarding", "2025-08-01", "https://www.youtube.com/embed/11tQ6PwrlIM"),
                ("Workplace Ethics", "2:12", "Culture", "2025-08-05", "https://www.youtube.com/embed/b_n6i1ug0tQ"),
                ("Software development life cycle", "2:47", "Software development", "2025-08-10", "https://www.youtube.com/embed/GxmfcnU3feo")
            ]
        )
    conn.commit()
    conn.close()

from datetime import datetime, timedelta

def classify_task(task):
    try:
        assigned_date_str = task.get('assigned_date')
        if not assigned_date_str:
            assigned_date = datetime.now().date()
        else:
            assigned_date = datetime.strptime(assigned_date_str, '%Y-%m-%d').date()
        
        status = task.get('status') or 'Assigned'
        today = datetime.now().date()
        days_passed = (today - assigned_date).days

        if status == 'Completed':
            return 'Completed'
        elif days_passed < 0:
            return 'Not yet started'
        elif days_passed > 5:
            return 'Delayed'
        elif days_passed > 2:
            return 'At Risk'
        else:
            return 'On Track'
    
    except Exception:
        return "Unknown"


def send_reminder(task):
    """
    Mock sending reminder: prints to console
    """
    print(f"[Reminder] Task '{task['task_name']}' for {task['emp_name']} is {task['auto_status']}")

@app.route('/api/tasks/send-reminders', methods=['POST'])
@login_required
def send_reminders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE status != 'Completed'")
    tasks = [dict(row) for row in cursor.fetchall()]

    for task in tasks:
        task['auto_status'] = classify_task(task)
        if task['auto_status'] in ['At Risk', 'Delayed']:
            send_reminder(task)
    
    conn.close()
    return jsonify({'message': 'Reminders sent (mocked/logged)'}), 200

@app.route('/api/report', methods=['GET'])
@login_required
def task_report():
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT e.emp_id, e.first_name, e.last_name, t.task_name, t.assigned_date, t.status
            FROM employees e
            LEFT JOIN tasks t ON e.emp_id = t.emp_id
        ''')
        rows = cursor.fetchall()

        report = {}
        today = datetime.now().date()

        for row in rows:
            emp_id = row['emp_id']
            emp_name = f"{row['first_name']} {row['last_name']}"

            if emp_id not in report:
                report[emp_id] = {
                    "employee_name": emp_name,
                    "tasks": []
                }

            if row['task_name']:  # only if employee has a task
                # ✅ Handle assigned_date safely
                try:
                    if row['assigned_date']:
                        # works if assigned_date is already a date
                        if isinstance(row['assigned_date'], str):
                            assigned_date = datetime.strptime(row['assigned_date'], '%Y-%m-%d').date()
                        else:
                            assigned_date = row['assigned_date']
                    else:
                        assigned_date = today
                except Exception:
                    assigned_date = today

                due_date = assigned_date + timedelta(days=5)

                # ✅ Handle status safely
                status = row['status'] if row['status'] else "Not Started"
                days_passed = (today - assigned_date).days

                # ✅ Classification logic
                if status == "Completed":
                    auto_status = "Completed"
                elif days_passed > 5:
                    auto_status = "Delayed"
                elif days_passed > 2 and status == "Not Started":
                    auto_status = "At Risk"
                else:
                    auto_status = "On Track"

                # if auto_status in ["At Risk", "Delayed"]:
                #     print(f"[MOCK EMAIL] Reminder sent to {emp_name} for task '{row['task_name']}' - Status: {auto_status}")

                reminder_sent = auto_status in ["At Risk", "Delayed"]
                report[emp_id]["tasks"].append({
                    "task_name": row['task_name'],
                    "assigned_date": assigned_date.strftime('%Y-%m-%d'),
                    "due_date": due_date.strftime('%Y-%m-%d'),
                    "current_status": status,
                    "report_status": auto_status
                })

        conn.close()
        return jsonify(list(report.values()))

    except Exception as e:
        import traceback
        print("---- ERROR IN /api/report ----")
        print(traceback.format_exc())   # full traceback in terminal
        return jsonify({"error": str(e)}), 500

import joblib
import numpy as np

# --- Load your trained model once ---
progress_model = joblib.load("progress_model.pkl")
print("Model loaded:", progress_model)

import pandas as pd

@app.route('/api/predict-progress', methods=['POST'])
def predict_progress():
    data = request.get_json()
    time_spent = data.get('time_spent_hours', 0)
    task_type = data.get('task_type', 'Other')
    previous_delays = data.get('previous_delays', 0)

    # Build a dataframe with same structure as training
    df = pd.DataFrame([{
        "time_spent_hours": time_spent,
        "previous_delays": previous_delays,
        "task_type": task_type
    }])

    # One-hot encode like training (drop_first=True)
    df = pd.get_dummies(df, columns=['task_type'], drop_first=True)

    # Align with model’s training columns
    for col in progress_model.feature_names_in_:  
        if col not in df.columns:
            df[col] = 0  # add missing columns

    df = df[progress_model.feature_names_in_]  # reorder

    pred = progress_model.predict(df)[0]
    pred_label = "Delayed" if pred == 1 else "On Track"

    return jsonify({"prediction": pred_label})



if __name__ == '__main__':
    init_db()
    insert_default_videos()
    app.run(debug=True, port=5000)
