import streamlit as st 
import pandas as pd
import io
import time
from azure.storage.filedatalake import DataLakeServiceClient

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Vendor RFQ", page_icon="🚛", layout="centered")

# ------------------ STYLING ------------------
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(to right, #f0f8ff, #e1f5fe);
        background-attachment: fixed;
        height: 100vh;
        padding-top: 0 !important;
        margin-top: -60px;
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
    header {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    .css-1v0mbdj {display: none;}
    .st-bm {padding-top: 0;}
    .center-img {
        display: flex;
        justify-content: center;
        margin-top: 30px;
        margin-bottom: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ CONFIG ------------------
ADLS_ACCOUNT_NAME = "genaiautomationsa"
ADLS_ACCOUNT_KEY = "vwwQ7uleP291h6A0NjsAdSAlUmlXW2qUipCvynul27mgrDjEqH7ofshn4GstabN6aj78c/DVQnLp+ASt7vdksg=="
FILE_SYSTEM_NAME = "vendor-rfq"
FILE_PATH = "truck_summary/region_vendor_summary.csv"

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

# ------------------ ADLS FUNCTIONS ------------------
def get_adls_client():
    return DataLakeServiceClient(
        account_url=f"https://{ADLS_ACCOUNT_NAME}.dfs.core.windows.net",
        credential=ADLS_ACCOUNT_KEY
    )

def read_csv_from_adls(file_path):
    adls_client = get_adls_client()
    fs_client = adls_client.get_file_system_client(FILE_SYSTEM_NAME)
    file_client = fs_client.get_file_client(file_path)
    download = file_client.download_file()
    downloaded_bytes = download.readall()
    return pd.read_csv(io.BytesIO(downloaded_bytes))

def overwrite_quotation_file(df_submission: pd.DataFrame):
    file_path = "vendor_response/quotation.csv"
    adls_client = get_adls_client()
    fs_client = adls_client.get_file_system_client(FILE_SYSTEM_NAME)
    file_client = fs_client.get_file_client(file_path)

    for _ in range(3):
        try:
            if file_client.exists():
                existing = file_client.download_file().readall()
                df_existing = pd.read_csv(io.BytesIO(existing))

                # Standardize email and route ID for comparison
                df_existing["Vendor Email"] = df_existing["Vendor Email"].str.lower()
                df_existing["Route ID"] = df_existing["Route ID"].str.upper()

                email = df_submission["Vendor Email"].iloc[0].lower()
                updated_route_ids = df_submission["Route ID"].str.upper().tolist()

                # Remove existing submissions from same email + same Route ID
                df_existing = df_existing[~(
                    (df_existing["Vendor Email"] == email) &
                    (df_existing["Route ID"].isin(updated_route_ids))
                )]

                df = pd.concat([df_existing, df_submission], ignore_index=True)
            else:
                df = df_submission

            # Standardize vendor info
            df["Vendor Name"] = df["Vendor Name"].apply(lambda x: x.strip().title())
            df["Vendor Email"] = df["Vendor Email"].apply(lambda x: x.strip().lower())

            # Save to ADLS
            buffer = io.StringIO()
            df.to_csv(buffer, index=False)
            file_client.upload_data(io.BytesIO(buffer.getvalue().encode()), overwrite=True)
            return True

        except Exception as e:
            time.sleep(1)

    raise Exception("❌ Failed to overwrite after 3 attempts.")

def reset_routes():
    st.session_state["route_id"] = []

# ------------------ THANK YOU SCREEN ------------------
if st.session_state.get("submitted"):
    st.markdown("## 🎉 Thank you for your submission!")
    st.markdown('<div class="center-img"><img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTHHjEEcoo3KwJ5PTfi2ys6nIQ7K2R8JBoYdw&s" width="300"></div>', unsafe_allow_html=True)
    st.success("Your data has been saved successfully. You may now close the tab.")
    st.stop()

# ------------------ FORM ------------------
with st.container():
    st.title("🚛 Vendor Quotation Form")

    col1, col2 = st.columns(2)
    with col1:
        vendor_name = st.text_input("🧾 Company Name", key="vendor_name")
    with col2:
        vendor_email = st.text_input("✉️ Email Address", key="vendor_email")

    if not vendor_name or not vendor_email:
        st.warning("Please enter your company name and email before continuing.")
        st.stop()

    region = st.selectbox("🌍 Select Region", list(ZONE_ROUTE_MAP.keys()), on_change=reset_routes, key="region")
    route_options = ZONE_ROUTE_MAP.get(region, [])
    route_ids = st.multiselect("🛣️ Select Route IDs", route_options, key="route_id")

    truck_types = st.multiselect("🚛 Select Truck Types", TRUCK_TYPES, default=TRUCK_TYPES, key="truck_type")

    if route_ids and truck_types:
        st.subheader("📊 Enter Truck Count and Price")
        truck_data = read_csv_from_adls(FILE_PATH)

        combo_data = []
        for route in route_ids:
            for truck in truck_types:
                row = truck_data[(truck_data["Route_ID"] == route) & (truck_data["Truck_Type"] == truck)]
                required_count = row["Required_Truck"].iloc[0] if not row.empty else 0

                col1, col2 = st.columns(2)
                with col1:
                    count = st.number_input(f"{truck} | {route} | Count", value=required_count, min_value=0, step=10, key=f"{route}_{truck}_count")
                with col2:
                    price = st.number_input(f"{truck} | {route} | Price per Truck", min_value=0.0, step=500.0, key=f"{route}_{truck}_price")

                total_cost = count * price
                st.markdown(f"**💰 Total Cost for {truck} on {route}: ₹{total_cost:,.2f}**")

                combo_data.append({
                    "Vendor Name": vendor_name.strip().title(),
                    "Vendor Email": vendor_email.strip().lower(),
                    "Region": region,
                    "Route ID": route.upper(),
                    "Truck Type": truck,
                    "Count": count,
                    "Price per Truck": price,
                    "Total Cost": total_cost,
                    "Submitted At": pd.Timestamp.now()
                })

        if st.button("✅ Submit Quotation"):
            try:
                df_submission = pd.DataFrame(combo_data)
                overwrite_quotation_file(df_submission)
                st.success("Submitted successfully!")
                st.session_state["submitted"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")
