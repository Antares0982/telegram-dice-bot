import sqlite3


def createBlacklist(blacklistdatabase:str):
    conn = sqlite3.connect(blacklistdatabase)
    c = conn.cursor()

    c.execute('''CREATE TABLE BLACKLIST
                (TGID    INT     NOT NULL    PRIMARY KEY);''')
    print("Table created successfully")

    conn.commit()
    c.close()
