import gradio as gr
import sqlite3

# 创建数据库
conn = sqlite3.connect('pufa-sqlite.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Project(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_Id INTEGER,
        project_Name TEXT,
        knowledge_Id INTEGER,
        cluster_Id INTEGER,
        group_Id TEXT,
        prompt_Id TEXT,
        history_Id INTEGER   
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Cluster (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cluster_Id INTEGER,
        cluster_Ask TEXT,
        cluster_Answer TEXT,
        FOREIGN KEY (cluster_Id) REFERENCES Project (cluster_Id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Knowledge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        knowledge_Id INTEGER,
        knowledge_Name TEXT,
        FOREIGN KEY (knowledge_Id) REFERENCES Project (knowledge_Id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Prompt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prompt_Id TEXT,
        Prompt_Ask TEXT,
        Prompt_Answer TEXT,
        FOREIGN KEY (prompt_Id) REFERENCES Project (prompt_Id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS History (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        history_Id INTEGER,
        history_Ask TEXT,
        history_Answer TEXT,
        FOREIGN KEY (history_Id) REFERENCES Project (history_Id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Mapping (
        id INTEGER,
        type TEXT,
        name TEXT
    )
''')

conn.commit()
conn.close()