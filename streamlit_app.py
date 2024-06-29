import streamlit as st
import pandas as pd
import boto3
from boto3.dynamodb.conditions import Key
import decimal
from pathlib import Path
import uuid  # For generating unique IDs for new items
import hmac

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Wedding Gift Shop',
    page_icon=':shopping_bags:',
    layout='wide'
)

# Initialize the DynamoDB resource using credentials from secrets
dynamodb = boto3.resource(
    'dynamodb',
    region_name=st.secrets["aws"]["aws_region"],
    aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
    aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"]
)

# Reference to the DynamoDB table
table = dynamodb.Table(st.secrets["aws"]["dynamodb_table"])

def load_data():
    '''Loads the wedding gifts data from DynamoDB.'''
    response = table.scan()
    data = response['Items']
    df = pd.DataFrame(data, columns=['id', 'item_name', 'price', 'image_path', 'purchased'])
    return df

def mark_as_purchased(item_id):
    '''Marks an item as purchased in DynamoDB.'''
    table.update_item(
        Key={'id': item_id},
        UpdateExpression='SET purchased = :val1',
        ExpressionAttributeValues={':val1': True}
    )

def add_product(item_name, price, image_path):
    '''Adds a new product to DynamoDB.'''
    item_id = str(uuid.uuid4())  # Generate a unique ID
    # Convert price to the correct DynamoDB numeric format (Decimal)
    price_decimal = decimal.Decimal(str(price))
    # Convert image_path to string if it's a Path object
    if isinstance(image_path, Path):
        image_path = str(image_path)

    table.put_item(
        Item={
            'id': item_id,
            'item_name': item_name,
            'price': price_decimal,
            'image_path': image_path,
            'purchased': False
        }
    )

def admin_panel():
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
            add_product(item_name, price, str(image_path))
            st.success('Product added successfully!')
        else:
            st.error('Please fill in all fields and upload an image.')

    st.header('Existing Products')
    df = load_data()
    st.write(df)

background_image = """
<style>
[data-testid="stAppViewContainer"] > .main {
    background-image: url("paja.png");
    background-size: 100vw 100vh;  # This sets the size to cover 100% of the viewport width and height
    background-position: center;
    background-repeat: no-repeat;
}
</style>
"""
st.markdown(background_image, unsafe_allow_html=True)

def shop_page():
    '''Displays the shopping page.'''
    st.image('paja.png', width=400)

    df = load_data()

    col1, col2 = st.columns(2) 

    @st.experimental_dialog("Überweisung")
    def info_ueberweisung():
        st.write(f"Überweise gern €{row['price']} für {row['item_name']} auf `DE123`")

    # Initialize flags to track whether sections have been shown
    schon_geschenkt_shown = False
    geschenketisch_shown = False

    for index, row in df.iterrows():
        if row['purchased']:
            if not schon_geschenkt_shown:
                st.subheader("Schon geschenkt", divider='blue')
                schon_geschenkt_shown = True
            
            st.image(
                row['image_path'],
                width=200,
                caption=f"{row['item_name']} (€{row['price']})"
            )

        else:
            if not geschenketisch_shown:
                st.subheader(":grey-background[Geschenketisch]", divider='rainbow')
                geschenketisch_shown = True
            
            with st.container(border=True):
                st.image(
                    row['image_path'],
                    caption=row['item_name'],
                    use_column_width=True
                )
                with st.popover('Buy this item for Pauline and Jan'):
                    name = st.text_input("Magst Du ergänzen wer Du bist?")
                    message = st.text_area("Möchtest Du eine Nachricht hinzufügen?")
                    if st.button(f"Buy {row['item_name']} for €{row['price']}", key=f"buy_button_{row['id']}", type='primary'):
                        mark_as_purchased(row['id'])
                        info_ueberweisung()
                        st.rerun()

def check_password(password_key):
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets[password_key]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Passwort", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

st.title('💒 Hochzeitsgeschenke Vorjohann', anchor=False)

# Check if 'secretadmin' parameter is in query params
if 'secretadmin' in st.query_params:
    # Check admin password for admin panel access
    if not check_password("password_admin"):
        st.stop()
    admin_panel()
else:
    # Check general password for access
    if not check_password("password"):
        st.stop()
    shop_page()
