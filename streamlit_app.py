import streamlit as st
import pandas as pd
import boto3
import botocore
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
    '''Loads all wedding gifts data from DynamoDB, handling pagination.'''
    items = []
    last_evaluated_key = None
    
    while True:
        if last_evaluated_key:
            response = table.scan(ExclusiveStartKey=last_evaluated_key)
        else:
            response = table.scan()
        
        items.extend(response['Items'])
        
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    
    df = pd.DataFrame(items)
    st.write(f"Total items loaded from DynamoDB: {len(df)}")
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

def check_image_size(image, max_size_mb=1):
    """Check if the image size is within the limit."""
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
    return image.size <= max_size_bytes

def add_product(item_name, price, image):
    '''Adds a new product to DynamoDB with image data.'''
    item_id = str(uuid.uuid4())
    price_decimal = decimal.Decimal(str(price))
    
    # Check image size
    if not check_image_size(image):
        st.error(f"Image size exceeds the limit of 1MB. Please upload a smaller image.")
        return False

    # Convert image to base64 without compression
    img_str = base64.b64encode(image.read()).decode()

    try:
        table.put_item(
            Item={
                'id': item_id,
                'item_name': item_name,
                'price': price_decimal,
                'image_data': img_str,
                'purchased': False
            }
        )
    except botocore.exceptions.ClientError as e:
        st.error(f"An error occurred: {str(e)}")
        return False
    return True

def update_product(item_id, item_name, price, image=None):
    '''Updates an existing product in DynamoDB.'''
    update_expression = 'SET item_name = :name, price = :price'
    expression_attribute_values = {
        ':name': item_name,
        ':price': decimal.Decimal(str(price))
    }

    if image:
        # Check image size
        if not check_image_size(image):
            st.error(f"Image size exceeds the limit of 1MB. Please upload a smaller image.")
            return False

        img_str = base64.b64encode(image.read()).decode()
        update_expression += ', image_data = :image'
        expression_attribute_values[':image'] = img_str

    try:
        table.update_item(
            Key={'id': item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
    except botocore.exceptions.ClientError as e:
        st.error(f"An error occurred: {str(e)}")
        return False
    return True

def admin_panel():
    '''Displays the admin panel for managing products.'''
    st.title('Admin Panel')

    st.header('Add New Product')
    item_name = st.text_input('Item Name')
    price = st.number_input('Price', min_value=0.0, format="%.2f")
    image = st.file_uploader('Upload Image', type=['jpg', 'jpeg', 'png'])

    if st.button('Add Product'):
        if item_name and price and image:
            if add_product(item_name, price, image):
                st.success('Product added successfully!')
            else:
                st.error('Failed to add product. Please try again.')
        else:
            st.error('Please fill in all fields and upload an image.')

    df = load_data()

    with st.expander('all data'):
        df
        st.write(df[df['purchased'] == True])

    st.subheader('Bought Items')
    bought_df = df[df['purchased'] == True] if not df.empty else pd.DataFrame()
    if bought_df.empty:
        st.write("No available items.")
    else:
        for index, row in bought_df.iterrows():
            st.write(f"Item Name: {row['item_name']}")
            st.write(f"Price: ${row['price']:.2f}")

    st.subheader('Available Items')
    available_df = df[df['purchased'] == False] if not df.empty else pd.DataFrame()
    if available_df.empty:
        st.write("No available items.")
    else:
        for index, row in available_df.iterrows():
            with st.expander(f"Edit {row['item_name']}"):
                new_name = st.text_input('Item Name', value=row['item_name'], key=f"name_{row['id']}")
                new_price = st.number_input('Price', value=float(row['price']), min_value=0.0, format="%.2f", key=f"price_{row['id']}")
                new_image = st.file_uploader('Upload New Image', type=['jpg', 'jpeg', 'png'], key=f"image_{row['id']}")
                
                if st.button('Update Product', key=f"update_{row['id']}"):
                    if update_product(row['id'], new_name, new_price, new_image):
                        st.success('Product updated successfully!')
                        st.rerun()
                    else:
                        st.error('Failed to update product. Please try again.')

def shop_page():
    '''Displays the shopping page.'''

    st.markdown("""
    <style>
    .logo-image {
        border-radius: 15px;
        overflow: hidden;
    }
    .logo-image img {
        width: 100%;
        height: auto;
        display: block;
    }
    </style>
    """, unsafe_allow_html=True)

    # Create a container for the logo
    logo_container = st.container()

    with logo_container:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.image('paja.png', use_column_width=True)

    # Add some space after the logo
    st.markdown("<br>", unsafe_allow_html=True)

    df = load_data()

    st.subheader("Schon geschenkt", divider='blue')
    purchased_items = df[df['purchased'] == True] if not df.empty else pd.DataFrame()
    if purchased_items.empty:
        st.write("Sei der erste, der ein Geschenk auswählt.")
    else:
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

    st.subheader(":rainbow-background[Geschenketisch]", divider='rainbow')
    available_items = df[df['purchased'] == False] if not df.empty else pd.DataFrame()
    if available_items.empty:
        st.write("Der Geschenketisch mit Ideen ist gerade leer!")
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(available_items.iterrows()):
            with cols[i % 3]:
                with st.container(border=True):
                    image = Image.open(BytesIO(base64.b64decode(row['image_data'])))
                    st.image(image, caption=row['item_name'], use_column_width=True)
                    
                    if f"purchased_{row['id']}" not in st.session_state:
                        st.session_state[f"purchased_{row['id']}"] = False
                    
                    if not st.session_state[f"purchased_{row['id']}"]:
                        name = st.text_input("Magst Du ergänzen wer Du bist?", key=f"name_{row['id']}")
                        message = st.text_area("Möchtest Du eine Nachricht hinzufügen?", key=f"message_{row['id']}")
                        if st.button(f"Jetzt {row['item_name']} für €{row['price']} vom virtuellen Geschenketisch nehmen", key=f"buy_button_{row['id']}", type='primary'):
                            mark_as_purchased(row['id'], name, message)
                            st.session_state[f"purchased_{row['id']}"] = True
                            st.success("Das Geschenk ist jetzt entnommen und nicht mehr für andere verfügbar.")
                            st.write(f"Überweise gern €{row['price']} für {row['item_name']} auf diese Bankverbindung")
                            st.code(f"DE123", language="text")
                            if st.button("Danke, ich bin hier fertig", key=f"transfer_done_{row['id']}"):
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