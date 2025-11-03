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

## ⚙️ Technologies Used

### 🧠 Software
- **Python Flask** — Backend web framework  
- **HTML / CSS / JavaScript** — Frontend web interface  
- **MySQL** — Database management and storage  

### 🔌 Hardware
- **Raspberry Pi 2 Model B** — Central IoT controller  
- **13.56 MHz RFID Scanner** — Student identification device  

---

## 🧩 System Workflow

1. Each student is assigned a unique RFID ID card linked to their profile in the **MySQL database**.  
2. When the student scans the RFID card on the **scanner connected to Raspberry Pi**, the system verifies their identity.  
3. The backend (Python Flask) dynamically **allocates an exam room and seat** based on availability and predefined rules.  
4. The allocation details are updated in the database and displayed on the web interface for faculty monitoring.  
5. Faculty members can **download reports** of student seating arrangements for each exam hall.

---

## 🧱 Database Overview

- Contains student details such as:
  - Name  
  - Roll Number  
  - Batch  
  - RFID Tag ID  
  - Room & Seat Number  
- Allocation data is stored and updated automatically upon each RFID scan.

---

## 🚀 Future Enhancements

This project serves as a **base model** for future expansion.  
Planned advanced features include:
- 🔒 **Fingerprint authentication** for additional security  
- 🧠 **Image recognition** using AI for identity verification  
- 📱 **Mobile application integration** for real-time updates  
- 📊 **Dashboard analytics** for monitoring student attendance and seating patterns

---

## 🌐 Project Objectives

- To automate exam hall and seat allotment using IoT technology  
- To minimize manual intervention and reduce administrative workload  
- To ensure transparency and accuracy in student seat allocation  
- To provide real-time data access to faculty members  

---

## 🛠️ System Architecture (Simplified)


