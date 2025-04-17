# ------------------ IMPORTS ------------------
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

# ------------------ TRUCK REQUIREMENT LOADER ------------------
@st.cache_data
def load_truck_requirements():
    file_path = "abfss://vendor-rfq@genaiautomationsa.dfs.core.windows.net/truck_summary/region_vendor_summary.csv"  # 🔹 Fill your file path here
    return pd.read_csv(file_path)

truck_req_df = load_truck_requirements()

# ------------------ ADLS FUNCTIONS ------------------
def get_adls_client():
    return DataLakeServiceClient(
        account_url=f"https://{ADLS_ACCOUNT_NAME}.dfs.core.windows.net",
        credential=ADLS_ACCOUNT_KEY
    )

def append_to_quotation_file(df_submission: pd.DataFrame):
    file_path = "vendor_response/quotation.csv"
    adls_client = get_adls_client()
    fs_client = adls_client.get_file_system_client(FILE_SYSTEM_NAME)
    file_client = fs_client.get_file_client(file_path)

    for _ in range(3):
        try:
            if file_client.exists():
                existing = file_client.download_file().readall()
                df_existing = pd.read_csv(io.BytesIO(existing))
                df_existing = df_existing[~(
                    (df_existing["Vendor Name"].str.lower() == df_submission["Vendor Name"].iloc[0].lower()) &
                    (df_existing["Vendor Email"].str.lower() == df_submission["Vendor Email"].iloc[0].lower())
                )]
                df = pd.concat([df_existing, df_submission], ignore_index=True)
            else:
                df = df_submission

            df = df.applymap(lambda x: x.lower() if isinstance(x, str) else x)
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
    st.markdown('<div class="center-img"><img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTHHjEEcoo3KwJ5PTfi2ys6nIQ7K2R8JBoYdw&s" width="300"></div>', unsafe_allow_html=True)
    st.success("Your data has been saved successfully. You may now close the tab.")
    st.stop()

# ------------------ FORM ------------------
with st.container():
    st.title("🚛 Vendor Quotation Form")

    col1, col2 = st.columns(2)
    with col1:
        vendor_name = st.text_input("📟 Company Name", key="vendor_name")
    with col2:
        vendor_email = st.text_input("✉️ Email Address", key="vendor_email")

    if not vendor_name or not vendor_email:
        st.warning("Please enter your company name and email before continuing.")
        st.stop()

    region = st.selectbox("🌍 Select Region", list(ZONE_ROUTE_MAP.keys()), on_change=reset_routes, key="region")
    route_options = ZONE_ROUTE_MAP.get(region, [])
    route_ids = st.multiselect("🚣️ Select Route IDs", route_options, key="route_id")

    if route_ids:
        truck_types = TRUCK_TYPES
        st.multiselect("🚛 Truck Types", truck_types, default=truck_types, disabled=True, key="truck_type")

        st.subheader("📊 Enter Truck Count and Price")
        combo_data = []
        for route in route_ids:
            for truck in truck_types:
                default_count = truck_req_df.query("`Route ID` == @route and `Truck Type` == @truck")['Count'].values
                default_count = int(default_count[0]) if len(default_count) else 0

                col1, col2 = st.columns(2)
                with col1:
                    count = st.number_input(f"{truck} | {route} | Count", min_value=0, step=10, value=default_count, key=f"{route}_{truck}_count")
                with col2:
                    price = st.number_input(f"{truck} | {route} | Price per Truck", min_value=0.0, step=500.0, key=f"{route}_{truck}_price")
                total_cost = count * price
                st.markdown(f"**💰 Total Cost for {truck} on {route}: ₹{total_cost:,.2f}**")

                combo_data.append({
                    "Vendor Name": vendor_name,
                    "Vendor Email": vendor_email,
                    "Region": region,
                    "Route ID": route,
                    "Truck Type": truck,
                    "Count": count,
                    "Price per Truck": price,
                    "Total Cost": total_cost,
                    "Submitted At": pd.Timestamp.now()
                })

        if st.button("✅ Submit Quotation"):
            try:
                df_submission = pd.DataFrame(combo_data)
                append_to_quotation_file(df_submission)
                st.success("Submitted successfully!")
                st.session_state["submitted"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Upload failed: {e}")













