# system.py - updated to handle SIGTERM/SIGINT and always cleanup LCD/GPIO/DB

import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import random
import time
import Adafruit_CharLCD as LCD
import mysql.connector
import pymysql
import signal
import sys
import threading

# Using pymysql as connection platform
mysql.connector.connect = pymysql.connect

# === LCD Setup ===
GPIO.setmode(GPIO.BCM)

RS = 4      # Pin 7
E = 17      # Pin 11
D4 = 22     # Pin 15
D5 = 27     # Pin 13
D6 = 23     # Pin 16
D7 = 7      # Pin 26

lcd = LCD.Adafruit_CharLCD(RS, E, D4, D5, D6, D7, 16, 2)

# === RFID Reader Setup ===
reader = SimpleMFRC522()

# === MySQL Connection ===
db = mysql.connector.connect(
  host="localhost",
  user="rpi",
  password="",
  database="exam_allotment",
  ssl_disabled=True
)
cursor = db.cursor()

# Global flag used by signal handler and main loop
stop_requested = False
stop_lock = threading.Lock()

def set_stop_flag():
    global stop_requested
    with stop_lock:
        stop_requested = True

def is_stop_requested():
    with stop_lock:
        return stop_requested

def safe_clear_lcd_and_cleanup(message=None):
    """
    Attempt to clear the LCD and perform GPIO cleanup.
    This is safe to call from the signal handler.
    """
    try:
        # Try to clear LCD display
        try:
            lcd.clear()
            if message:
                # short message then clear
                lcd.message(message)
                time.sleep(1)
                lcd.clear()
        except Exception as e:
            # If the LCD driver fails, just log (printing is okay)
            print(f"[cleanup] LCD clear failed: {e}")

        # Cleanup GPIO (safe to call multiple times)
        try:
            GPIO.cleanup()
        except Exception as e:
            print(f"[cleanup] GPIO.cleanup() failed: {e}")

        # Close DB connection if open
        try:
            if db:
                db.close()
        except Exception as e:
            print(f"[cleanup] DB close failed: {e}")
    except Exception as e:
        print(f"[cleanup] Unexpected cleanup error: {e}")


# Signal handler for SIGTERM and SIGINT
def handle_terminate(signum, frame):
    """
    Signal handler that requests shutdown and performs minimal cleanup.
    It does not assume heavy operations are safe in a signal handler, but
    we do attempt to clear the LCD and set the stop flag so the main loop can exit.
    """
    print(f"[signal] Received signal {signum}, requesting stop...")
    # set the stop flag so main loop can break promptly
    set_stop_flag()

    # Attempt to clear LCD immediately so user sees feedback
    try:
        lcd.clear()
        # optional short message to indicate stop
        lcd.message("Shutting down")
        time.sleep(0.5)
        lcd.clear()
    except Exception:
        # ignore hardware errors here
        pass

    # Note: do not call sys.exit() here — allow main thread to exit cleanly.
    # But if signal delivered in main thread while blocked, we still set the flag.


# Register signal handlers
signal.signal(signal.SIGTERM, handle_terminate)
signal.signal(signal.SIGINT, handle_terminate)


#Function to check existing seat allotment
def get_existing_seat(student_id):
    """Checks if the student is already assigned a seat."""
    cursor.execute("""
                 SELECT e.room_no, e.seat_no
                 FROM exam_halls e
                 WHERE e.student_id = %s
                 """, (student_id,))
    result = cursor.fetchone()
    # Returns (room_no, seat_no) or None
    return result

# === Seat Assignment Logic (Unchanged) ===
def assign_seat(student_id, branch):
  cursor.execute("""
                 SELECT id, room_no, seat_no FROM exam_halls
                 WHERE is_occupied=0 AND id NOT IN (
                   SELECT e.id FROM exam_halls e
                                      JOIN students s ON e.student_id = s.id
                   WHERE s.branch = %s
                 )
                 """, (branch,))
  available = cursor.fetchall()
  if not available:
    return None

  seat = random.choice(available)
  seat_id, room, seat_no = seat
  cursor.execute(
    "UPDATE exam_halls SET is_occupied=1, student_id=%s WHERE id=%s",
    (student_id, seat_id)
  )
  db.commit()
  return (room, seat_no)


def main_loop():
    try:
      lcd.clear()
      print("Starting Execution")
      lcd.message("Place your card\non reader...")
      print()
      print("Students can now get their seats")
      # Main loop: break out if stop_requested
      while not is_stop_requested():
        try:
          # reader.read() is blocking; we rely on signal to set the stop flag
          # and interrupt system calls — in practice this works on most
          # platforms. If reader.read() does not get interrupted by signals
          # in your environment, consider replacing this with a non-blocking
          # method or running reading in a separate thread.
          id, text = reader.read()
        except (KeyboardInterrupt, SystemExit):
          # capture keyboard interrupt cleanly
          set_stop_flag()
          break
        except Exception as e:
          # If the reader raises an error, print and continue (or short sleep)
          print(f"[reader] read error: {e}")
          time.sleep(0.2)
          continue

        # If we've been asked to stop after interruption, break
        if is_stop_requested():
            break

        try:
          uid = format(id, 'X')
          print(f"Card detected: {uid}")
          # --- 1. Find Student ---
          cursor.execute("SELECT id, name, branch FROM students WHERE rfid_uid=%s", (uid,))
          student = cursor.fetchone()
          if student:
            sid, name, branch = student
            # --- 2. CHECK: Does student already have a seat? ---
            seat = get_existing_seat(sid)
            if seat:
              # Student HAS a seat -> Display existing seat
              room, seat_no = seat
              lcd.clear()
              lcd.message(f"ACTD-{name}\n{room} Seat {seat_no}")
              print(f"Already Allocated: {name} - {room} Seat {seat_no}")
            else:
              # Student has NO seat yet -> Assign a new one
              seat = assign_seat(sid, branch)
              if seat:
                room, seat_no = seat
                lcd.clear()
                lcd.message(f"{name}\n{room} Seat {seat_no}")
                print(f"Assigned: {name} - {room} Seat {seat_no}")
              else:
                lcd.clear()
                lcd.message("No seats left!")
                print("No seats left for this branch.")
          else:
            lcd.clear()
            lcd.message("Unknown card!")
            print("Unknown card detected.")
        except Exception as e:
          # protect main loop from unexpected DB/LCD errors
          print(f"[main] unexpected error while processing card: {e}")

        # brief pause so user can read LCD; also allows checking stop flag
        for _ in range(30):
            if is_stop_requested():
                break
            time.sleep(0.1)

        # update prompt again if not stopping
        if not is_stop_requested():
            lcd.clear()
            lcd.message("Place your card")
    finally:
      # Always run cleanup here (this runs on normal exit, KeyboardInterrupt, or after setting stop flag)
      print("[shutdown] cleaning up: clearing LCD, GPIO, and closing DB")
      try:
          safe_clear_lcd_and_cleanup()
      except Exception as e:
          print(f"[shutdown] cleanup error: {e}")
      # ensure DB closed
      try:
          if db:
              db.close()
      except Exception:
          pass


if __name__ == "__main__":
    main_loop()
