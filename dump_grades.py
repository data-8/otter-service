"""File to grab entries from gradebook.db and put them in a readable csv format"""
import csv
import sqlite3


def main():
    db_fname = "gradebook.db"
    conn = sqlite3.connect(db_fname)
    cur = conn.cursor()
    data = cur.execute("SELECT * FROM GRADES;")
    with open('grades.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['userid', 'grade', 'section', 'lab', 'timestamp'])
        writer.writerows(data)


if __name__ == '__main__':
    main()
