import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('countertops_and_accessories.db')
cursor = conn.cursor()

# Create the countertop table with the material and level combined
cursor.execute('''
CREATE TABLE IF NOT EXISTS countertop (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_level TEXT,
    price INTEGER
)
''')

# Create the accessories table with accessory and model combined
cursor.execute('''
CREATE TABLE IF NOT EXISTS accessories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accessory_model TEXT,
    price INTEGER
)
''')

# Insert data into the countertop table (material_level combined)
countertop_data = [
    ('granite level 1', 10),
    ('granite level 2', 20),
    ('granite level 3', 30),
    ('quartz level 1', 50),
    ('quartz level 2', 60),
    ('quartz level 3', 70)
]

cursor.executemany('''
INSERT INTO countertop (material_level, price)
VALUES (?, ?)
''', countertop_data)

# Insert data into the accessories table (accessory_model combined)
accessories_data = [
    ('sink 1', 10),
    ('sink 2', 20),
    ('sink 3', 30)
]

cursor.executemany('''
INSERT INTO accessories (accessory_model, price)
VALUES (?, ?)
''', accessories_data)

# Commit changes and close the connection
conn.commit()