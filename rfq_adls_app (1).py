import streamlit as st
import pandas as pd
import datetime
from azure.storage.filedatalake import DataLakeServiceClient
from azure.core.exceptions import ResourceNotFoundError

# ------------------------
# Azure ADLS Gen2 Credentials
# ------------------------
ACCOUNT_NAME = "genaiautomationsa"
ACCESS_KEY = "vwwQ7uleP291h6A0NjsAdSAlUmlXW2qUipCvynul27mgrDjEqH7ofshn4GstabN6aj78c/DVQnLp+ASt7vdksg=="
FILE_SYSTEM = "vendor-rfq"

# ------------------------
# Zone to Route ID Mapping
# ------------------------
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

# ------------------------
# Upload CSV to Azure ADLS Gen2
# ------------------------
def upload_csv_to_adls(region, df):
    try:
        service_client = DataLakeServiceClient(
            account_url=f"https://{ACCOUNT_NAME}.dfs.core.windows.net",
            credential=ACCESS_KEY
        )

        fs_client = service_client.get_file_system_client(FILE_SYSTEM)
        file_path = f"{region.replace(' ', '_')}.csv"
        file_client = fs_client.get_file_client(file_path)

        # Download existing CSV if available
        try:
            download = file_client.download_file()
            existing_data = pd.read_csv(download.readall())
            df = pd.concat([existing_data, df], ignore_index=True)
        except ResourceNotFoundError:
            pass  # First time writing this file

        # Convert DataFrame to CSV
        csv_content = df.to_csv(index=False).encode('utf-8')

        # Upload full content (overwrite for simplicity)
        file_client.upload_data(csv_content, overwrite=True)

    except Exception as e:
        st.error(f"❌ Error uploading to ADLS: {str(e)}")


# ------------------------
# Streamlit UI
# ------------------------
st.set_page_config(page_title="Vendor RFQ Form", page_icon="📦", layout="wide")

if "submitted" not in st.session_state:
    st.session_state["submitted"] = False

# ------------------------
# Thank You Page
# ------------------------
if st.session_state["submitted"]:
    st.success("🎉 Thank you for your submission!")
    st.balloons()
    st.markdown("## 📨 Your response has been saved successfully.")
    st.markdown("Feel free to close this tab or submit another response.")
    if st.button("🔁 Submit Another Response"):
        st.session_state["submitted"] = False
        st.experimental_rerun()

# ------------------------
# Main Form Page
# ------------------------
else:
    st.title("📝 Vendor Route Submission Form")
    st.markdown("#### Please fill in the form. Route IDs are filtered based on Zone.")

    with st.form("vendor_form"):
        vendor_name = st.text_input("👤 Vendor Name")
        email = st.text_input("📧 Email Address")
        zone = st.selectbox("🌍 Select Zone", list(ZONE_ROUTE_MAP.keys()))

        route_ids = st.multiselect("🛣️ Select Route IDs", options=ZONE_ROUTE_MAP[zone])
        truck_types = st.multiselect("🚛 Select Truck Types", options=TRUCK_TYPES)

        submission_data = []

        if route_ids and truck_types:
            st.markdown("### 📦 Enter Truck Count and Price")
            st.caption("Fill in values for each selected Route ID and Truck Type.")

            for route in route_ids:
                for truck in truck_types:
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{route} — {truck}**")
                    with col2:
                        count = st.number_input(f"Count ({route}-{truck})", min_value=0, key=f"{route}_{truck}_count")
                    with col3:
                        price = st.number_input(f"Price ({route}-{truck})", min_value=0.0, key=f"{route}_{truck}_price")

                    if count > 0:
                        submission_data.append({
                            "vendor_name": vendor_name,
                            "email": email,
                            "zone": zone,
                            "route_id": route,
                            "truck_type": truck,
                            "truck_count": count,
                            "price": price,
                            "submitted_at": datetime.datetime.utcnow().isoformat()
                        })
        else:
            st.info("👆 Select both Route IDs and Truck Types to continue.")

        st.markdown("### 🔍 Preview Submission")

        if st.form_submit_button("👁️ Preview"):
            if submission_data:
                df_preview = pd.DataFrame(submission_data)
                st.dataframe(df_preview)
            else:
                st.warning("Please add truck data to preview.")

        if st.form_submit_button("🚀 Submit"):
            if not vendor_name or not email or not zone or not submission_data:
                st.error("⚠️ Please complete all required fields.")
            else:
                df = pd.DataFrame(submission_data)
                upload_csv_to_adls(zone, df)
                st.session_state["submitted"] = True
                st.experimental_rerun()
