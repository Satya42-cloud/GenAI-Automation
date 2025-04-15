import streamlit as st
import pandas as pd
import io
import time
from azure.storage.filedatalake import DataLakeServiceClient

# ------------------ CONFIG ------------------
ADLS_ACCOUNT_NAME = "genaiautomationsa"
ADLS_ACCOUNT_KEY = "vwwQ7uleP291h6A0NjsAdSAlUmlXW2qUipCvynul27mgrDjEqH7ofshn4GstabN6aj78c/DVQnLp+ASt7vdksg=="
FILE_SYSTEM_NAME = "vendor-rfq"

ZONE_ROUTE_MAP = {
    "Andhra Region": [f"R{i:03d}" for i in range(1, 16)],
    "Bihar Plateau": [f"R{i:03d}" for i in range(16, 46)],
    "Capital Belt": [f"R{i:03d}" for i in range(46, 71)],
    "Deccan West": [f"R{i:03d}" for i in range(71, 91)],
    "Eastern Seaboard": [f"R{i:03d}" for i in range(91, 131)],
    "Ganga Plains": [f"R{i:03d}" for i in range(131, 161)],
    "Himalayan North": [f"R{i:03d}" for i in range(161, 171)],
    "Konkan South": [f"R{i:03d}" for i in range(171, 186)],
    "Malabar Coast": [f"R{i:03d}" for i in range(186, 206)],
    "North East": [f"R{i:03d}" for i in range(206, 221)],
    "Northwest Heartland": [f"R{i:03d}" for i in range(221, 236)],
    "Telangana Region": [f"R{i:03d}" for i in range(236, 246)],
    "Uttarakhand Highlands": [f"R{i:03d}" for i in range(246, 256)],
    "Vindhya Plateau": [f"R{i:03d}" for i in range(256, 286)],
    "Western Frontier": [f"R{i:03d}" for i in range(286, 301)],
}

TRUCK_TYPES = ["Container", "LCV", "MCV"]

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Vendor RFQ", page_icon="🚛", layout="centered")

# ------------------ STYLING ------------------
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to right, #f0f8ff, #e1f5fe);
        background-attachment: fixed;
        height: 100vh;
    }
    .main {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin-top: 40px;
    }
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div > select,
    .stMultiSelect > div > div > div > select {
        border-radius: 8px;
        padding: 10px;
    }
    .stButton > button {
        background-color: #009688;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 12px 25px;
    }
    header {visibility: hidden;}  /* This hides the default Streamlit header completely */
    .stApp > header {visibility: hidden;}  /* Ensures it's hidden on mobile too */
    .css-1v0mbdj {display: none;}  /* Hides any additional patches or spaces */
    .st-bm {padding-top: 0;}  /* Adjusting padding for no extra space at the top */
    </style>
""", unsafe_allow_html=True)

# ------------------ ADLS FUNCTIONS ------------------
def get_adls_client():
    return DataLakeServiceClient(
        account_url=f"https://{ADLS_ACCOUNT_NAME}.dfs.core.windows.net",
        credential=ADLS_ACCOUNT_KEY
    )

def append_to_region_file(region: str, df_submission: pd.DataFrame):
    region = region.lower().replace(" ", "_")
    file_path = f"{region}/submissions.csv"
    adls_client = get_adls_client()
    fs_client = adls_client.get_file_system_client(FILE_SYSTEM_NAME)
    file_client = fs_client.get_file_client(file_path)

    for _ in range(3):
        try:
            if file_client.exists():
                existing = file_client.download_file().readall()
                df_existing = pd.read_csv(io.BytesIO(existing))
                df = pd.concat([df_existing, df_submission], ignore_index=True)
            else:
                df = df_submission

            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            file_client.upload_data(io.BytesIO(buffer.getvalue().encode()), overwrite=True)
            return True
        except Exception as e:
            time.sleep(1)
    raise Exception("❌ Failed to append after 3 attempts.")

def reset_routes():
    st.session_state["route_id"] = []

# ------------------ THANK YOU SCREEN ------------------
if st.session_state.get("submitted"):
    st.markdown("## 🎉 Thank you for your submission!")
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTHHjEEcoo3KwJ5PTfi2ys6nIQ7K2R8JBoYdw&s", width=300)
    st.success("Your data has been saved successfully. You may now close the tab.")
    st.stop()

# ------------------ FORM ------------------
with st.container():
    st.markdown('<div class="main">', unsafe_allow_html=True)
    st.title("📦 Vendor Quotation Form")

    col1, col2 = st.columns(2)
    with col1:
        vendor_name = st.text_input("🧾 Company Name", key="vendor_name")
    with col2:
        vendor_email = st.text_input("✉️ Email Address", key="vendor_email")

    if not vendor_name or not vendor_email:
        st.warning("Please enter your company name and email before continuing.")
        st.markdown('</div>', unsafe_allow_html=True)
        st.stop()

    region = st.selectbox("🌍 Select Region", list(ZONE_ROUTE_MAP.keys()), on_change=reset_routes, key="region")
    route_options = ZONE_ROUTE_MAP.get(region, [])
    route_ids = st.multiselect("🛣️ Select Route IDs", route_options, key="route_id")
    truck_types = st.multiselect("🚛 Select Truck Types", TRUCK_TYPES, key="truck_type")

    if route_ids and truck_types:
        st.subheader("📊 Enter Truck Count and Price")
        combo_data = []
        for route in route_ids:
            for truck in truck_types:
                col1, col2 = st.columns(2)
                with col1:
                    count = st.number_input(f"{truck} | {route} | Count", min_value=0, key=f"{route}_{truck}_count")
                with col2:
                    price = st.number_input(f"{truck} | {route} | Price", min_value=0.0, key=f"{route}_{truck}_price")
                combo_data.append({
                    "vendor_name": vendor_name,
                    "vendor_email": vendor_email,
                    "region": region,
                    "route_id": route,
                    "truck_type": truck,
                    "truck_count": count,
                    "price": price,
                    "submitted_at": pd.Timestamp.now()
                })

        if st.button("✅ Submit Quotation"):
            try:
                df_submission = pd.DataFrame(combo_data)
                append_to_region_file(region, df_submission)
                st.success("Submitted successfully!")
                st.session_state["submitted"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")
    st.markdown('</div>', unsafe_allow_html=True)



