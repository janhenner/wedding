import streamlit as st
import pandas as pd
import boto3
from boto3.dynamodb.conditions import Key
import decimal
import uuid
import hmac
import base64
from io import BytesIO
from PIL import Image

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
    df = pd.DataFrame(data)
    return df

def mark_as_purchased(item_id, buyer_name, message):
    '''Marks an item as purchased in DynamoDB and adds buyer info.'''
    table.update_item(
        Key={'id': item_id},
        UpdateExpression='SET purchased = :val1, buyer_name = :val2, buyer_message = :val3',
        ExpressionAttributeValues={
            ':val1': True,
            ':val2': buyer_name,
            ':val3': message
        }
    )

def add_product(item_name, price, image):
    '''Adds a new product to DynamoDB with image data.'''
    item_id = str(uuid.uuid4())
    price_decimal = decimal.Decimal(str(price))
    
    # Convert image to base64
    buffered = BytesIO()
    Image.open(image).save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    table.put_item(
        Item={
            'id': item_id,
            'item_name': item_name,
            'price': price_decimal,
            'image_data': img_str,
            'purchased': False
        }
    )

def update_product(item_id, item_name, price, image=None):
    '''Updates an existing product in DynamoDB.'''
    update_expression = 'SET item_name = :name, price = :price'
    expression_attribute_values = {
        ':name': item_name,
        ':price': decimal.Decimal(str(price))
    }

    if image:
        buffered = BytesIO()
        Image.open(image).save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        update_expression += ', image_data = :image'
        expression_attribute_values[':image'] = img_str

    table.update_item(
        Key={'id': item_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values
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
            add_product(item_name, price, image)
            st.success('Product added successfully!')
        else:
            st.error('Please fill in all fields and upload an image.')

    st.header('Existing Products')
    df = load_data()
    
    st.subheader('Purchased Items')
    purchased_df = df[df['purchased'] == True]
    for _, row in purchased_df.iterrows():
        st.write(f"Item: {row['item_name']}")
        st.write(f"Price: €{row['price']}")
        st.write(f"Bought by: {row.get('buyer_name', 'Unknown')}")
        st.write(f"Message: {row.get('buyer_message', 'No message')}")
        st.write("---")

    st.subheader('Available Items')
    available_df = df[df['purchased'] == False]
    for index, row in available_df.iterrows():
        with st.expander(f"Edit {row['item_name']}"):
            new_name = st.text_input('Item Name', value=row['item_name'], key=f"name_{row['id']}")
            new_price = st.number_input('Price', value=float(row['price']), min_value=0.0, format="%.2f", key=f"price_{row['id']}")
            new_image = st.file_uploader('Upload New Image', type=['jpg', 'jpeg', 'png'], key=f"image_{row['id']}")
            
            if st.button('Update Product', key=f"update_{row['id']}"):
                update_product(row['id'], new_name, new_price, new_image)
                st.success('Product updated successfully!')
                st.rerun()

background_image = """
<style>
[data-testid="stAppViewContainer"] > .main {
    background-image: url("paja.png");
    background-size: 100vw 100vh;
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

    st.subheader("Schon geschenkt", divider='blue')
    purchased_items = df[df['purchased'] == True]
    cols = st.columns(3)
    for i, (_, row) in enumerate(purchased_items.iterrows()):
        with cols[i % 3]:
            image = Image.open(BytesIO(base64.b64decode(row['image_data'])))
            st.image(image, width=200, caption=f"{row['item_name']} (€{row['price']})")
    
    if len(purchased_items) > 6:
        if st.button("Show more purchased items"):
            for i, (_, row) in enumerate(purchased_items[6:].iterrows()):
                with cols[i % 3]:
                    image = Image.open(BytesIO(base64.b64decode(row['image_data'])))
                    st.image(image, width=200, caption=f"{row['item_name']} (€{row['price']})")

    st.subheader(":grey-background[Geschenketisch]", divider='rainbow')
    available_items = df[df['purchased'] == False]
    cols = st.columns(3)
    for i, (_, row) in enumerate(available_items.iterrows()):
        with cols[i % 3]:
            with st.container(border=True):
                image = Image.open(BytesIO(base64.b64decode(row['image_data'])))
                st.image(image, caption=row['item_name'], use_column_width=True)
                with st.popover('Buy this item for Pauline and Jan'):
                    name = st.text_input("Magst Du ergänzen wer Du bist?", key=f"name_{row['id']}")
                    message = st.text_area("Möchtest Du eine Nachricht hinzufügen?", key=f"message_{row['id']}")
                    if st.button(f"Buy {row['item_name']} for €{row['price']}", key=f"buy_button_{row['id']}", type='primary'):
                        mark_as_purchased(row['id'], name, message)
                        st.success("Item purchased successfully!")
                        st.write(f"Überweise gern €{row['price']} für {row['item_name']} auf `DE123`")
                        st.code(f"DE123", language="text")
                        if st.button("I've made the transfer", key=f"transfer_done_{row['id']}"):
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