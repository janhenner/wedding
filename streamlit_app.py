import sqlite3
from pathlib import Path

import streamlit as st
import pandas as pd

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Wedding Gift Shop',
    page_icon=':shopping_bags:',
)


def connect_db():
    '''Connects to the sqlite database.'''
    DB_FILENAME = Path(__file__).parent / 'wedding_gifts.db'
    db_already_exists = DB_FILENAME.exists()

    conn = sqlite3.connect(DB_FILENAME)
    db_was_just_created = not db_already_exists

    return conn, db_was_just_created


def initialize_data(conn):
    '''Initializes the wedding_gifts table with some data.'''
    cursor = conn.cursor()
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS wedding_gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            price REAL,
            purchased INTEGER DEFAULT 0
        )
        '''
    )

    cursor.execute(
        '''
        INSERT INTO wedding_gifts (item_name, price, purchased) VALUES
        ('Breakfast in Hotel', 25.0, 0),
        ('Night in Hotel', 75.0, 0)
        '''
    )
    conn.commit()


def load_data(conn):
    '''Loads the wedding gifts data from the database.'''
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wedding_gifts')
    data = cursor.fetchall()
    df = pd.DataFrame(data, columns=['id', 'item_name', 'price', 'purchased'])
    return df


def mark_as_purchased(conn, item_id):
    '''Marks an item as purchased in the database.'''
    cursor = conn.cursor()
    cursor.execute('UPDATE wedding_gifts SET purchased = 1 WHERE id = ?', (item_id,))
    conn.commit()


# Connect to database and create table if needed
conn, db_was_just_created = connect_db()

# Initialize data if the database was just created
if db_was_just_created:
    initialize_data(conn)
    st.toast('Database initialized with some sample data.')

# Load data from database
df = load_data(conn)

# Display the wedding gifts
st.title('Wedding Gift Shop')
st.write('Select a gift to purchase for the wedding.')

for index, row in df.iterrows():
    if row['purchased']:
        st.write(f"~~{row['item_name']} - €{row['price']} (Purchased)~~")
    else:
        if st.button(f"Buy {row['item_name']} for €{row['price']}", key=row['id']):
            mark_as_purchased(conn, row['id'])
            st.experimental_rerun()

st.write("Refresh the page to see updates.")
