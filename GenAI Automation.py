import streamlit as st
import pandas as pd
import io
import time
from azure.storage.filedatalake import DataLakeServiceClient

# ------------------ ADLS CONFIG ------------------
ADLS_ACCOUNT_NAME = "genaiautomationsa"
ADLS_ACCOUNT_KEY = "vwwQ7uleP291h6A0NjsAdSAlUmlXW2qUipCvynul27mgrDjEqH7ofshn4GstabN6aj78c/DVQnLp+ASt7vdksg=="
FILE_SYSTEM_NAME = "vendor-rfq"

# ------------------ ZONE MAPPING ------------------
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

# ------------------ CSS STYLING ------------------
st.markdown("""
    <style>
        .stApp {
            background-color: #f8f9fa;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .stButton>button {
            background-color: #1abc9c;
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 8px;
        }
        .stTextInput>div>div>input {
            border-radius: 6px;
        }
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

    for _ in range(3):  # retry logic
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
            print("Retry append due to:", e)
            time.sleep(1)
    raise Exception("❌ Failed to append after 3 attempts.")

# ------------------ STREAMLIT UI ------------------
st.title("📦 Vendor RFQ Form")

# 1️⃣ Vendor Info
vendor_name = st.text_input("🧾 Company Name", key="vendor_name")
vendor_email = st.text_input("✉️ Email Address", key="vendor_email")

if not vendor_name or not vendor_email:
    st.warning("Please fill out your company name and email to continue.")
    st.stop()

# 2️⃣ Region Selection & Dynamic Route Reset
def reset_routes():
    st.session_state["route_id"] = []

region = st.selectbox("🌍 Select Region", list(ZONE_ROUTE_MAP.keys()), key="region", on_change=reset_routes)
route_options = ZONE_ROUTE_MAP.get(region, [])

# 3️⃣ Route ID & Truck Type Selection
route_ids = st.multiselect("🚚 Select Route IDs", route_options, key="route_id")
truck_types = st.multiselect("🛻 Select Truck Types", TRUCK_TYPES, key="truck_type")

# 4️⃣ Truck Count & Price Entry
if route_ids and truck_types:
    st.subheader("📄 Enter Truck Details")
    combo_data = []
    for route in route_ids:
        for truck in truck_types:
            count = st.number_input(f"{truck} - {route} | Truck Count", min_value=0, key=f"{route}_{truck}_count")
            price = st.number_input(f"{truck} - {route} | Price", min_value=0.0, key=f"{route}_{truck}_price")
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

    # 5️⃣ Submit
    if st.button("📨 Submit Response"):
        try:
            df_submission = pd.DataFrame(combo_data)
            append_to_region_file(region, df_submission)
            st.success("✅ Your response has been submitted successfully!")
            st.balloons()
            st.session_state["submitted"] = True
            st.rerun()
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")

# 6️⃣ Thank You Message
if st.session_state.get("submitted"):
    st.header("🎉 Thank You!")
    st.write("Your data has been received and stored securely.")
    st.session_state["submitted"] = False
