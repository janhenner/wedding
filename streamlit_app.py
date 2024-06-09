import sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd
import os

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
            image_path TEXT,
            purchased INTEGER DEFAULT 0
        )
        '''
    )
    conn.commit()


def load_data(conn):
    '''Loads the wedding gifts data from the database.'''
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wedding_gifts')
    data = cursor.fetchall()
    df = pd.DataFrame(data, columns=['id', 'item_name', 'price', 'image_path', 'purchased'])
    return df


def mark_as_purchased(conn, item_id):
    '''Marks an item as purchased in the database.'''
    cursor = conn.cursor()
    cursor.execute('UPDATE wedding_gifts SET purchased = 1 WHERE id = ?', (item_id,))
    conn.commit()


def add_product(conn, item_name, price, image_path):
    '''Adds a new product to the database.'''
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO wedding_gifts (item_name, price, image_path, purchased) VALUES (?, ?, ?, 0)',
        (item_name, price, image_path)
    )
    conn.commit()


def admin_panel(conn):
    '''Displays the admin panel for managing products.'''
    st.title('Admin Panel')

    st.header('Add New Product')
    item_name = st.text_input('Item Name')
    price = st.number_input('Price', min_value=0.0, format="%.2f")
    image = st.file_uploader('Upload Image', type=['jpg', 'jpeg', 'png'])

    if st.button('Add Product'):
        if item_name and price and image:
            images_dir = Path('images')
            if not images_dir.exists():
                images_dir.mkdir(parents=True)
                
            image_path = images_dir / image.name
            with open(image_path, 'wb') as f:
                f.write(image.getbuffer())
            add_product(conn, item_name, price, str(image_path))
            st.success('Product added successfully!')
        else:
            st.error('Please fill in all fields and upload an image.')

    st.header('Existing Products')
    df = load_data(conn)
    st.write(df)


def shop_page(conn):
    '''Displays the shopping page.'''
    st.title('Wedding Gift Shop')
    st.write('Select a gift to purchase for the wedding.')

    df = load_data(conn)

    for index, row in df.iterrows():
        if row['purchased']:
            st.write(f"~~{row['item_name']} - €{row['price']} (Purchased)~~")
        else:
            st.image(row['image_path'], width=100)
            if st.button(f"Buy {row['item_name']} for €{row['price']}", key=row['id']):
                mark_as_purchased(conn, row['id'])
                st.rerun()


# Connect to database and create table if needed
conn, db_was_just_created = connect_db()

# Initialize data if the database was just created
if db_was_just_created:
    initialize_data(conn)
    st.toast('Database initialized with some sample data.')

# Routing workaround
if 'admin' in st.query_params:
    admin_panel(conn)
else:
    shop_page(conn)
