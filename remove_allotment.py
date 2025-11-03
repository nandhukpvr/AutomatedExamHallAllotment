import mysql.connector
import RPi.GPIO as GPIO
import time
import Adafruit_CharLCD as LCD
# Import pymysql and patch the connector for reliability
import pymysql
mysql.connector.connect = pymysql.connect

# === LCD Setup ===
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

RS = 4
E = 17
D4 = 22
D5 = 27
D6 = 23
D7 = 7

try:
  lcd = LCD.Adafruit_CharLCD(RS, E, D4, D5, D6, D7, 16, 2)
except Exception:
  print("Warning: Could not initialize LCD.")
  lcd = None

# === MySQL Connection Configuration ===
DB_CONFIG = {
  "host": "localhost",
  "user": "rpi",
  "password": "",
  "database": "exam_allotment",
  "ssl_disabled": True
}

# ==========================================================
# === CORE RESET FUNCTION (Simplified and Corrected) ===
# ==========================================================
def remove_all_allotments():
  """
  Connects to the database, resets all seats to is_occupied=0
  and student_id=NULL, and displays the status on the LCD.
  """
  conn = None
  try:
    if lcd:
      lcd.clear()
      lcd.message("Resetting Seats...")
    print("\n--- Starting Allotment Removal ---")

    # 1. Establish connection (Localized, clean connection)
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 2. Reset Exam Halls: Clear student_id and set is_occupied to 0
    halls_sql = """
                UPDATE exam_halls
                SET student_id = NULL, is_occupied = 0
                WHERE is_occupied = 1 OR is_occupied = 0 \
                """
    cursor.execute(halls_sql)
    halls_count = cursor.rowcount
    conn.commit()

    print(f"âœ… Successfully cleared {halls_count} seat records.")

    if lcd:
      lcd.clear()
      lcd.message("ALLOTMENT CLEARED!\nSeats Free: " + str(halls_count))

    print("--- RESET COMPLETE ---")
    print("All seats are now available.")

  except mysql.connector.Error as err:
    error_msg = f"DB ERROR: {err.errno}"
    if lcd:
      lcd.clear()
      lcd.message(error_msg + "\nCheck Terminal")
    print(f"\nâŒ Database Error: {err}")
    if conn:
      conn.rollback()

  except Exception as e:
    if lcd:
      lcd.clear()
      lcd.message("Fatal Error\nCheck Terminal")
    print(f"\nâŒ A critical error occurred: {e}")

  finally:
    # Corrected connection closure logic
    if conn:
      conn.close()
      print("Database connection closed.")

    # Final LCD/GPIO cleanup
    if lcd:
      time.sleep(4)
      lcd.clear()
    GPIO.cleanup()
    print("GPIO cleanup complete. Script exiting.")


if __name__ == "__main__":
  try:
    remove_all_allotments()
  except KeyboardInterrupt:
    print("\nProcess interrupted by user.")
    GPIO.cleanup()

