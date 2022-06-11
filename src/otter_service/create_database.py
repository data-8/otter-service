import sqlite3
from sqlite3 import Error
import os


def create_connection(db_fname):
    """
    Creates connection to the database specified. Creates it if non-existent.
    :param db_fname: the file path to the db
    :return: sqlite3 connection object
    """
    try:
        conn = sqlite3.connect(db_fname)
        return conn
    except Exception as e:
        raise e

    return None


def create_table(conn):
    """
    Creates schema within the database.

    This should match the section in gofer_nb.py that writes to the database.
    Feel free to customize this if you store different metadata (e.g. section/lab).

    :param conn: the connection object to the db path
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
    except Exception as e:
        raise e


def main():
    """
    Creates the db_path, connection and table

    """
    try:
        db_path = os.getenv("VOLUME_PATH") + '/gradebook.db'
        conn = create_connection(db_path)
        create_table(conn)
        conn.close()
    except Exception as e:
        raise e


if __name__ == '__main__':
    main()
