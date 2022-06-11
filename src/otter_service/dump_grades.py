import csv
import sqlite3
import os


def main():
    """File to grab entries from gradebook.db and put them in a readable csv format"""
    db_path = os.getenv("VOLUME_PATH") + '/gradebook.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    data = cur.execute("SELECT * FROM GRADES;")
    with open(os.getenv("VOLUME_PATH") + '/grades.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['userid', 'grade', 'section', 'lab', 'timestamp'])
        writer.writerows(data)


if __name__ == '__main__':
    if "VOLUME_PATH" not in os.environ:
        print("Set VOLUME_PATH environment variable -- this is where gradebook.db lives")
    main()
