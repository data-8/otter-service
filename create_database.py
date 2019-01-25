import sqlite3
from sqlite3 import Error


def create_connection(db_fname):
    """Creates connection to the database specified. Creates it if non-existent."""
    try:
        conn = sqlite3.connect(db_fname)
        return conn
    except Error as e:
        print(e)

    return None

def create_table(conn):
    """Creates schema within the database.

    This should match the section in gofer_nb.py that writes to the database.
    Feel free to customize this if you store different metadata (e.g. section/lab).
    """
    create_sql_table_stmt = """ CREATE TABLE IF NOT EXISTS grades (
                                        userid text PRIMARY KEY,
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


def main():
    conn = create_connection('gradebook.db')
    create_table(conn)
    conn.close()


if __name__ == '__main__':
    main()
