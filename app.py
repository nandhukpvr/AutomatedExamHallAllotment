import mysql.connector
from flask import Flask, render_template,request,redirect,url_for
# import remove_allotment
import subprocess


    
app= Flask(__name__)

db = mysql.connector.connect(
    host="localhost",
    user="root",           # replace with your MySQL username
    password="12345",  # replace with your MySQL password
    database="exam_allotment")
cursor = db.cursor()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/insert',methods=['GET','POST'])
def how_many():
    if request.method=='POST':
        num_students=int(request.form['num_students'])
        return render_template('student_form.html',num_students=num_students)
    return render_template('how_many.html')

@app.route('/submit', methods=['POST'])
def submit():
    ids = request.form.getlist('id[]')
    names = request.form.getlist('name[]')
    branches = request.form.getlist('branch[]')
    reg_nums = request.form.getlist('reg_num[]')

    messages = []

    for i in range(len(ids)):
        student_id = ids[i]
        name = names[i]
        branch = branches[i]
        reg_num = reg_nums[i]

        # Check if student exists by id or register_no
        cursor.execute("SELECT * FROM students WHERE id = %s OR register_no = %s", (student_id, reg_num))
        existing = cursor.fetchone()

        if existing:
            # Student exists, do not update
            messages.append(f"Student ID {student_id} or Register No {reg_num} already exists.")
        else:
            # Insert new student
            cursor.execute("""
                INSERT INTO students (id, name, branch, register_no)
                VALUES (%s, %s, %s, %s)
            """, (student_id, name, branch, reg_num))
            messages.append(f"Student ID {student_id} added successfully.")

    db.commit()

    # Return all messages
    return "<br>".join(messages)  # Or render a template with messages

@app.route('/rooms')
def rooms():
    cursor.execute("SELECT DISTINCT room_no FROM exam_halls")
    all_rooms = cursor.fetchall()
    return render_template('rooms.html', rooms=[room[0] for room in all_rooms])

@app.route('/room/<room_no>')
def room_students(room_no):
    query = """
        SELECT eh.id, eh.seat_no, s.id, s.name, s.branch, s.register_no
        FROM exam_halls eh
        JOIN students s ON eh.student_id = s.id
        WHERE eh.room_no = %s AND eh.is_occupied = 1
    """
    cursor.execute(query, (room_no,))
    students = cursor.fetchall()
    return render_template('room_students.html', students=students, room_no=room_no)

@app.route('/remove_allotment', methods=['POST'])
def remove_allotment():
    # Replace 'other_script.py' with your script path
    result = subprocess.run(['python', 'remove_allotment.py'], capture_output=True, text=True)
    # Capture the output and return it to the user (optional)
    output = result.stdout
    return f"<h2>Script Output:</h2><pre>{output}</pre>"




if __name__=='__main__':
    app.run(debug=True)
    