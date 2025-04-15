import streamlit as st
import pandas as pd
from datetime import datetime
from azure.storage.filedatalake import DataLakeServiceClient

# -------------------------
# ADLS CONFIG (👇 update this)
# -------------------------
ACCOUNT_NAME = "genaiautomationsa"
ACCESS_KEY = "vwwQ7uleP291h6A0NjsAdSAlUmlXW2qUipCvynul27mgrDjEqH7ofshn4GstabN6aj78c/DVQnLp+ASt7vdksg=="
FILE_SYSTEM = "vendor-rfq"
FILE_PATH = "rfq-submissions/rfq_data.csv"  # Folder + file inside ADLS

# -------------------------
# Zone/Route Setup
# -------------------------
zone_route_map = {
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

truck_types = ["Container", "MCV", "LCV"]

# -------------------------
# ADLS Upload Logic
# -------------------------
def upload_row_to_adls(row_df):
    service_client = DataLakeServiceClient(account_url=f"https://{ACCOUNT_NAME}.dfs.core.windows.net", credential=ACCESS_KEY)
    file_system_client = service_client.get_file_system_client(file_system=FILE_SYSTEM)

    try:
        file_client = file_system_client.get_file_client(FILE_PATH)
        download = file_client.download_file().readall()
        existing_df = pd.read_csv(pd.compat.StringIO(download.decode()))
    except:
        existing_df = pd.DataFrame()

    combined_df = pd.concat([existing_df, row_df], ignore_index=True)

    file_client = file_system_client.get_file_client(FILE_PATH)
    file_client.create_file()
    file_client.append_data(data=combined_df.to_csv(index=False), offset=0, length=len(combined_df.to_csv(index=False)))
    file_client.flush_data(len(combined_df.to_csv(index=False)))

# -------------------------
# UI Starts Here
# -------------------------
st.set_page_config(page_title="Vendor RFQ Form", layout="centered")
st.title("🚚 Vendor RFQ Submission")

with st.form("rfq_form"):
    zone = st.selectbox("Zone", list(zone_route_map.keys()))
    route = st.selectbox("Route ID", zone_route_map[zone])
    truck = st.selectbox("Truck Type", truck_types)
    count = st.number_input("Truck Count", min_value=1)
    price = st.number_input("Proposed Price (₹)", min_value=1000)
    contact_name = st.text_input("Contact Name")
    contact_email = st.text_input("Contact Email")
    submitted = st.form_submit_button("Submit Quote")

if submitted:
    row_df = pd.DataFrame([{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Zone": zone,
        "Route ID": route,
        "Truck Type": truck,
        "Truck Count": count,
        "Price": price,
        "Contact Name": contact_name,
        "Contact Email": contact_email
    }])

    try:
        upload_row_to_adls(row_df)
        st.success("✅ Submission uploaded to ADLS Gen2 successfully!")
    except Exception as e:
        st.error(f"❌ Upload failed: {e}")
