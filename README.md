# 🎓 IoT-Based Automated Exam Hall and Seat Allotment System

> **Semester 3 MCA Project**  
> Department of Computer Applications

---

## 👩‍💻 Team Members
- **Nandhu Krishna**
- **Abhimanyu S**
- **Adithya A J**
- **Shahala Thasni**

---

## 💡 Project Overview

The **IoT-Based Automated Exam Hall and Seat Allotment System** is an innovative solution designed to **digitize and automate the traditional exam seating process** using IoT technology and web integration.

The system efficiently manages student identification, exam hall allocation, and seat assignment in real-time using **RFID technology** and **Raspberry Pi** microcontrollers. It eliminates manual errors, saves time, and provides faculty with instantly downloadable reports of student distribution across rooms.

---

## 🚀 Features

- **RFID-Based Identification**: Instant student verification using RFID cards.
- **Automated Seat Allocation**: Dynamic allocation of exam halls and seats based on availability and branch constraints.
- **Real-Time Web Dashboard**: Faculty can monitor allocations, manage students, and view room status in real-time.
- **Duplicate Prevention**: Prevents double allocation for the same student.
- **Database Integration**: Robust MySQL database to store student records and allocation data.
- **LCD Feedback**: Visual feedback on the hardware unit (Student Name, Room, Seat No).

---

## ⚙️ Technologies Used

### 🧠 Software
- **Python 3**: Core programming language.
- **Flask**: Web framework for the management dashboard.
- **MySQL**: Database for storing student and exam hall data.
- **HTML/CSS/JavaScript**: Frontend for the web interface.

### 🔌 Hardware
- **Raspberry Pi 3 Model B+** (or compatible)
- **RC522 RFID Reader** (13.56 MHz)
- **16x2 LCD Display** (with potentiometer for contrast)
- **Jumper Wires & Breadboard**

---

## 🛠️ Hardware Setup & Pin Connections

### RFID Reader (RC522) to Raspberry Pi
| RC522 Pin | Raspberry Pi Pin (Board / BCM) |
|-----------|--------------------------------|
| SDA (SS)  | Pin 24 / GPIO 8 (CE0)          |
| SCK       | Pin 23 / GPIO 11 (SCLK)        |
| MOSI      | Pin 19 / GPIO 10 (MOSI)        |
| MISO      | Pin 21 / GPIO 9 (MISO)         |
| IRQ       | Not Connected                  |
| GND       | Pin 6 (GND)                    |
| RST       | Pin 22 / GPIO 25               |
| 3.3V      | Pin 1 (3.3V)                   |

### LCD (16x2) to Raspberry Pi
| LCD Pin | Raspberry Pi Pin (Board / BCM) |
|---------|--------------------------------|
| RS      | GPIO 4                         |
| E       | GPIO 17                        |
| D4      | GPIO 22                        |
| D5      | GPIO 27                        |
| D6      | GPIO 23                        |
| D7      | GPIO 7                         |
| VSS     | GND                            |
| VDD     | 5V                             |
| V0      | Potentiometer (Contrast)       |
| RW      | GND                            |
| A (LED+)| 5V (via resistor)              |
| K (LED-)| GND                            |

---

## 📥 Installation Guide

### 1. Clone the Repository
```bash
git clone <repository-url>
cd AutomatedExamHallAllotment
```

### 2. Install System Dependencies
Ensure your Raspberry Pi is up to date and has Python 3 installed.
```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip libmysqlclient-dev
```

### 3. Install Python Libraries
Install the required Python packages:
```bash
pip3 install flask pymysql mysql-connector-python RPi.GPIO spidev mfrc522 Adafruit_CharLCD
```
*Note: You may need to enable SPI on your Raspberry Pi (`sudo raspi-config` > Interface Options > SPI).*

### 4. Database Setup
1. Install MySQL Server:
   ```bash
   sudo apt-get install mariadb-server
   ```
2. Log in to MySQL and create the database and user:
   ```sql
   sudo mysql -u root -p
   ```
   ```sql
   CREATE DATABASE exam_allotment;
   CREATE USER 'rpi'@'localhost' IDENTIFIED BY ''; -- Password is empty in config
   GRANT ALL PRIVILEGES ON exam_allotment.* TO 'rpi'@'localhost';
   FLUSH PRIVILEGES;
   USE exam_allotment;
   ```
3. Create the required tables:
   ```sql
   CREATE TABLE students (
       id VARCHAR(50) PRIMARY KEY,
       name VARCHAR(100),
       branch VARCHAR(50),
       register_no VARCHAR(50),
       photo_path VARCHAR(255),
       rfid_uid VARCHAR(50)
   );

   CREATE TABLE exam_halls (
       id INT AUTO_INCREMENT PRIMARY KEY,
       room_no VARCHAR(50),
       seat_no VARCHAR(50),
       is_occupied BOOLEAN DEFAULT 0,
       student_id VARCHAR(50),
       FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
   );
   ```

---

## 🖥️ Usage

### 1. Start the Web Application
Run the Flask app to manage the system:
```bash
python3 app.py
```
Access the dashboard at `http://<raspberry-pi-ip>:5000` or `http://localhost:5000`.

### 2. Configure the System
1. **Add Students**: Go to the **Students** tab and upload a CSV or manually add student details (ID, Name, Branch, Reg No, Photo). *Note: You need to map RFID UIDs to students in the database manually or via a registration script (not included).*
2. **Create Exam Halls**: Go to the **Exam Halls** tab and define rooms and the number of seats available.

### 3. Run the Allotment System
- On the **Home** page, set the "Gate Close Time" and click **Start System**.
- The `system.py` script will start running in the background.
- Students can now tap their RFID cards on the reader.
- The LCD will display their allotted Room and Seat Number.
- The Web Dashboard will update in real-time to show occupied seats.

---

## 📂 Project Structure

```
AutomatedExamHallAllotment/
├── app.py              # Main Flask application for the web interface
├── system.py           # Core logic for RFID reading and LCD display (runs on RPi)
├── templates/          # HTML templates for the web interface
├── static/             # CSS, JS, and uploaded student photos
├── README.md           # Project documentation
└── .gitignore          # Git ignore file
```

---

## 🔮 Future Enhancements

- 🔒 **Fingerprint authentication** for additional security.
- 🧠 **Image recognition** using AI for identity verification.
- 📱 **Mobile application integration** for real-time updates.
- 📊 **Dashboard analytics** for monitoring student attendance.

---
