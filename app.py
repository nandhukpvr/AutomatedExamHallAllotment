import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
import subprocess
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
system_process = None

# Photo upload config
UPLOAD_FOLDER = 'static/student_photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="12345",
    database="exam_allotment")
cursor = db.cursor()

@app.route('/')
def home():
    global system_process
    is_running = system_process is not None and (system_process.poll() is None)
    current_time = datetime.now()
    end_time_str = request.cookies.get('system_end_time')
    time_expired = False
    time_remaining = None
    
    if end_time_str:
        try:
            end_time = datetime.fromisoformat(end_time_str)
            if current_time > end_time:
                time_expired = True
                if is_running:
                    system_process.terminate()
                    system_process = None
                    is_running = False
            else:
                time_remaining = end_time - current_time
        except ValueError:
            response = redirect(url_for('home'))
            response.set_cookie('system_end_time', '', max_age=0)
            return response
    return render_template('home.html', is_running=is_running, time_expired=time_expired, time_remaining=time_remaining)

@app.route('/start_system', methods=['POST'])
def start_system():
    global system_process
    if system_process is None or (system_process.poll() is None):
        gate_close_time = request.form.get('gate_close_time')
        end_time_str = None
        
        if gate_close_time:
            close_datetime = datetime.strptime(gate_close_time, '%H:%M').replace(
                year=datetime.now().year, 
                month=datetime.now().month, 
                day=datetime.now().day
            )
            if close_datetime < datetime.now():
                close_datetime += timedelta(days=1)
            end_time_str = close_datetime.isoformat()
        
        system_process = subprocess.Popen(['python', 'run_system.py'],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
        
        response = redirect(url_for('home'))
        if end_time_str:
            response.set_cookie('system_end_time', end_time_str, max_age=86400)
        return response
    return redirect(url_for('home'))

@app.route('/stop_system', methods=['POST'])
def stop_system():
    global system_process
    if system_process is not None and (system_process.poll() is None):
        system_process.terminate()
        try:
            system_process.wait(timeout=5)
        except Exception:
            system_process.kill()
        system_process = None
    response = redirect(url_for('home'))
    response.set_cookie('system_end_time', '', max_age=0)
    return response  

@app.route('/database')
def database_section():
    return render_template('database.html')

@app.route('/students', methods=['GET', 'POST'])
def students_page():
    messages = []
    if request.method == 'POST':
        ids = request.form.getlist('id[]')
        names = request.form.getlist('name[]')
        branches = request.form.getlist('branch[]')
        reg_nums = request.form.getlist('reg_num[]')
        photos = request.files.getlist('photo[]')  
        
        min_len = min(len(ids), len(names), len(branches), len(reg_nums))
        
        for i in range(min_len):
            sid = ids[i].strip()
            name = names[i].strip()
            branch = branches[i].strip()
            reg_no = reg_nums[i].strip()
            photo = photos[i] if i < len(photos) else None

            if not sid or not reg_no:
                continue

            cursor.execute("SELECT * FROM students WHERE id = %s OR register_no = %s", (sid, reg_no))
            existing = cursor.fetchone()

            if existing:
                messages.append(f"Student ID {sid} / Reg {reg_no} already exists. Skipped.")
            else:
                photo_path = None
                if photo and allowed_file(photo.filename):
                    ext = photo.filename.rsplit('.', 1)[1].lower()
                    filename = f"{reg_no}.{ext}"
                    photo_path = f"student_photos/{filename}"
                    photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
                
                cursor.execute(
                    "INSERT INTO students (id, name, branch, register_no, photo_path) VALUES (%s, %s, %s, %s, %s)",
                    (sid, name, branch, reg_no, photo_path)
                )
                photo_msg = f"Photo saved" if photo_path else "No photo"
                messages.append(f"Student ID {sid} added. {photo_msg}")

        db.commit()
    cursor.execute("SELECT id, name, branch, register_no, photo_path FROM students ORDER BY id")
    all_students = cursor.fetchall()
    return render_template('students.html', students=all_students, messages=messages)

@app.route('/delete_student/<int:sid>', methods=['POST'])
def delete_student(sid):
    
    cursor.execute("SELECT photo_path FROM students WHERE id = %s", (sid,))
    photo_result = cursor.fetchone()
    if photo_result and photo_result[0]:
        photo_file = os.path.join(app.config['UPLOAD_FOLDER'], photo_result[0].replace('student_photos/', ''))
        if os.path.exists(photo_file):
            os.remove(photo_file)
    
    cursor.execute("DELETE FROM students WHERE id = %s", (sid,))
    db.commit()
    return redirect(url_for('students_page'))

@app.route('/exam_halls', methods=['GET', 'POST'])
def exam_halls_page():
    if request.method == 'POST':
        room_no = request.form.get('room_no').strip()
        total_seats = int(request.form.get('total_seats') or 0)

        if room_no and total_seats > 0:
            cursor.execute("DELETE FROM exam_halls WHERE room_no = %s", (room_no,))
            
            for s in range(1, total_seats + 1):
                cursor.execute(
                    "INSERT INTO exam_halls (room_no, seat_no, is_occupied, student_id) "
                    "VALUES (%s, %s, 0, NULL)",
                    (room_no, str(s))
                )
            db.commit()
    
    cursor.execute("SELECT room_no, COUNT(*) AS total_seats FROM exam_halls GROUP BY room_no ORDER BY room_no")
    halls = cursor.fetchall()
    return render_template('exam_halls.html', halls=halls)

@app.route('/delete_hall/<room_no>', methods=['POST'])
def delete_hall(room_no):
    cursor.execute("DELETE FROM exam_halls WHERE room_no = %s", (room_no,))
    db.commit()
    return redirect(url_for('exam_halls_page'))

@app.route('/results')
def result_section():
    return render_template('results.html')

@app.route('/clear_allotment', methods=['POST'])
def clear_allotment():
    global system_process
    if system_process is not None and system_process.poll() is None:
        system_process.terminate()
        try:
            system_process.wait(timeout=5)
        except Exception:
            system_process.kill()
    system_process = None

    cursor.execute("UPDATE exam_halls SET is_occupied = 0, student_id = NULL")
    db.commit()
    return redirect(url_for('result_section'))

@app.route('/rooms')
def rooms():
    cursor.execute("SELECT DISTINCT room_no FROM exam_halls")
    all_rooms = cursor.fetchall()
    return render_template('rooms.html', rooms=[room[0] for room in all_rooms])

@app.route('/room/<room_no>')
def room_students(room_no):
    query = """
        SELECT eh.id, eh.seat_no, s.id, s.name, s.branch, s.register_no, s.photo_path
        FROM exam_halls eh
        JOIN students s ON eh.student_id = s.id
        WHERE eh.room_no = %s AND eh.is_occupied = 1
    """
    cursor.execute(query, (room_no,))
    students = cursor.fetchall()
    return render_template('room_students.html', students=students, room_no=room_no)

if __name__=='__main__':
    app.run(debug=True)
