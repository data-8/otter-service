import os
import sqlite3
from sqlite3 import Error


def create_table(conn):
    """Creates schema within the database.

    This should match the section in gofer_nb.py that writes to the database.
    Feel free to customize this if you store different metadata (e.g. section/lab).
    """
    create_sql_table_stmt = """ CREATE TABLE IF NOT EXISTS grades (
                                        userid text,
                                        grade real,
                                        section text,
                                        lab text,
                                        timestamp text
                                    ); """
    try:
        c = conn.cursor()
        c.execute(create_sql_table_stmt)
    except Error as e:
        print(e)


def create_connection(db_fname):
    """Creates connection to the database specified. Creates it if non-existent."""
    try:
        conn = sqlite3.connect(db_fname)
        return conn
    except Error as e:
        print(e)

    return None


def insert_test_record(conn):
    sql_cmd = """INSERT INTO grades(userid, grade, section, lab, timestamp)
                     VALUES(?,?,?,?,?)"""
    try:
        with conn:
            conn.execute(sql_cmd, ("TEST_USER", 3.0, "1", "lab99", "1111"))
    except Exception as e:
        raise Exception(f"Error inserting into database for the following record")


def make_db(db_fname):
    conn = create_connection(db_fname)
    create_table(conn)
    insert_test_record(conn)
    conn.close()