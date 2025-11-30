import os
import signal
import time
import subprocess
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for
import pymysql

# ---------------------------
# App + Config
# ---------------------------
app = Flask(__name__)

# Photo upload config
UPLOAD_FOLDER = 'static/student_photos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------------------
# Database connection (update credentials as needed)
# ---------------------------
db = pymysql.connect(
    host="localhost",
    user="rpi",           # update if needed
    password="",          # update if needed
    database="exam_allotment"
)
db.autocommit(True)
cursor = db.cursor()

# ---------------------------
# Process tracking + files
# ---------------------------
system_process = None
system_out_file = None
system_err_file = None

PID_FILE = '/tmp/system_pid'
OUT_LOG = '/tmp/system_out.log'
ERR_LOG = '/tmp/system_err.log'

# ---------------------------
# PID file helpers and safe kill helpers
# ---------------------------
def save_pid_file(pid):
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        app.logger.warning(f"Failed to write pid file: {e}")

def read_pid_file():
    try:
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return None

def remove_pid_file():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        app.logger.warning(f"Failed to remove pid file: {e}")

def start_system_subprocess():
    """
    Start system.py and return (Popen, out_handle, err_handle).
    """
    out = None
    err = None
    try:
        os.makedirs('/tmp', exist_ok=True)
        out = open(OUT_LOG, 'ab')
        err = open(ERR_LOG, 'ab')
    except Exception as e:
        app.logger.warning(f"Could not open log files: {e}")
        out = None
        err = None

    # Start in new session so it gets a separate pgid
    proc = subprocess.Popen(
        ['python', 'system.py'],
        stdout=out or subprocess.DEVNULL,
        stderr=err or subprocess.DEVNULL,
        preexec_fn=os.setsid
    )
    app.logger.info(f"Started system.py pid={proc.pid}")
    save_pid_file(proc.pid)
    return proc, out, err

def safe_kill_process_group(pid, timeout=5):
    """
    Safely kill target pid's process group after several checks to avoid killing server/ssh.
    Returns True if the process group was terminated (or didn't exist), False on abort/failure.
    """
    if not pid or pid <= 0:
        app.logger.warning("safe_kill_process_group: invalid pid, aborting.")
        return False

    my_pid = os.getpid()
    if pid == my_pid:
        app.logger.error(f"Refusing to kill own pid ({pid}). Aborting.")
        return False
    if pid == 1:
        app.logger.error("Refusing to kill pid 1. Aborting.")
        return False

    # get pgid for target
    try:
        target_pgid = os.getpgid(pid)
    except Exception as e:
        app.logger.info(f"Target pid {pid} does not exist (or no pgid): {e}. Nothing to kill.")
        remove_pid_file()
        return True

    current_pgid = os.getpgrp()
    # if the target pgid equals our current process group, abort
    if target_pgid == current_pgid:
        app.logger.error(f"Refusing to kill process group {target_pgid} because it equals current pgid {current_pgid}.")
        return False

    app.logger.info(f"Attempting SIGTERM on pgid={target_pgid} (pid={pid})")
    try:
        os.killpg(target_pgid, signal.SIGTERM)
    except Exception as e:
        app.logger.warning(f"SIGTERM to group failed: {e}")

    # wait for graceful exit
    waited = 0.0
    interval = 0.25
    while waited < timeout:
        try:
            os.kill(pid, 0)  # check existence
            time.sleep(interval)
            waited += interval
        except OSError:
            # process gone
            app.logger.info(f"Process {pid} terminated after SIGTERM.")
            remove_pid_file()
            return True

    app.logger.warning(f"Process {pid} still alive after {timeout}s, escalating to SIGKILL.")
    try:
        os.killpg(target_pgid, signal.SIGKILL)
    except Exception as e:
        app.logger.warning(f"SIGKILL to group failed: {e}")

    # final check
    try:
        os.kill(pid, 0)
        app.logger.error(f"Process {pid} still exists after SIGKILL attempt.")
        return False
    except OSError:
        app.logger.info(f"Process {pid} killed successfully with SIGKILL.")
        remove_pid_file()
        return True

# ---------------------------
# Routes
# ---------------------------
@app.route('/')
def home():
    global system_process
    is_running = system_process is not None and (system_process.poll() is None)
    current_time = datetime.now()
    end_time_str = request.cookies.get('system_end_time')
    time_expired = False
    end_timestamp = None

    if end_time_str:
        try:
            end_time = datetime.fromisoformat(end_time_str)
            if current_time > end_time:
                time_expired = True
                if is_running:
                    # attempt safe kill of process group
                    try:
                        safe_kill_process_group(system_process.pid, timeout=2)
                    except Exception:
                        pass
                    # close logs if open
                    try:
                        global system_out_file, system_err_file
                        if system_out_file:
                            system_out_file.close(); system_out_file = None
                        if system_err_file:
                            system_err_file.close(); system_err_file = None
                    except Exception:
                        pass
                    try:
                        system_process.terminate()
                    except Exception:
                        pass
                    system_process = None
                    is_running = False
            else:
                end_timestamp = int(end_time.timestamp() * 1000)
        except ValueError:
            response = redirect(url_for('home'))
            response.set_cookie('system_end_time', '', max_age=0)
            return response

    return render_template('home.html',
                           is_running=is_running,
                           time_expired=time_expired,
                           end_timestamp=end_timestamp)

@app.route('/start_system', methods=['POST'])
def start_system():
    global system_process, system_out_file, system_err_file
    # only start if not running
    if system_process is None or (system_process and system_process.poll() is not None):
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

        proc, out, err = start_system_subprocess()
        system_process = proc
        system_out_file = out
        system_err_file = err

        response = redirect(url_for('home'))
        if end_time_str:
            response.set_cookie('system_end_time', end_time_str, max_age=86400)
        return response

    return redirect(url_for('home'))

@app.route('/stop_system', methods=['POST'])
def stop_system():
    global system_process, system_out_file, system_err_file
    pid_to_kill = None

    if system_process is not None and system_process.poll() is None:
        pid_to_kill = system_process.pid
    else:
        pid_to_kill = read_pid_file()

    if not pid_to_kill:
        app.logger.info("No pid found to stop.")
    else:
        ok = safe_kill_process_group(pid_to_kill, timeout=5)
        if not ok:
            app.logger.error("Failed to safely stop the process group; aborting to avoid harming server.")
        else:
            app.logger.info(f"Stopped system.py pid {pid_to_kill} successfully.")

    # close logs
    try:
        if system_out_file:
            system_out_file.close(); system_out_file = None
        if system_err_file:
            system_err_file.close(); system_err_file = None
    except Exception:
        pass

    system_process = None
    remove_pid_file()

    response = redirect(url_for('home'))
    response.set_cookie('system_end_time', '', max_age=0)
    return response

# ---------------------------
# Database / Students / Halls routes (kept similar)
# ---------------------------
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
        photos = request.files.getlist('photo[]')  # optional if present

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
                messages.append(f"Student ID {sid} added. {'Photo saved' if photo_path else 'No photo'}")
        db.commit()

    cursor.execute("SELECT id, name, branch, register_no, photo_path FROM students ORDER BY id")
    all_students = cursor.fetchall()
    return render_template('students.html', students=all_students, messages=messages)

@app.route('/delete_student/<int:sid>', methods=['POST'])
def delete_student(sid):
    cursor.execute(
        "UPDATE exam_halls SET is_occupied = 0, student_id = NULL WHERE student_id = %s",
        (sid,)
    )
    # 2) Remove photo file if it exists
    cursor.execute("SELECT photo_path FROM students WHERE id = %s", (sid,))
    photo_result = cursor.fetchone()
    if photo_result and photo_result[0]:
        photo_file = os.path.join(app.config['UPLOAD_FOLDER'], photo_result[0].replace('student_photos/', ''))
        if os.path.exists(photo_file):
            os.remove(photo_file)

    # 3) Delete the student row (now safe, no FK references)
    cursor.execute("DELETE FROM students WHERE id = %s", (sid,))

    # 4) Commit the changes
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
    pid_to_kill = None
    if system_process is not None and system_process.poll() is None:
        pid_to_kill = system_process.pid
    else:
        pid_to_kill = read_pid_file()

    if pid_to_kill:
        try:
            safe_kill_process_group(pid_to_kill, timeout=3)
        except Exception:
            pass

    system_process = None
    cursor.execute("UPDATE exam_halls SET is_occupied = 0, student_id = NULL")
    db.commit()
    remove_pid_file()
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

# ---------------------------
# App entry
# ---------------------------
if __name__ == '__main__':
    # For development/testing on Raspberry Pi, run with use_reloader=False so globals remain stable.
    app.run(debug=True, use_reloader=False, host='0.0.0.0')
