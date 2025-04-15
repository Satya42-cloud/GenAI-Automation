import streamlit as st
import pandas as pd
import io
import time
from azure.storage.filedatalake import DataLakeServiceClient

# ------------------ CONFIG ------------------
ADLS_ACCOUNT_NAME = "genaiautomationsa"  # Your ADLS account name
ADLS_ACCOUNT_KEY = "vwwQ7uleP291h6A0NjsAdSAlUmlXW2qUipCvynul27mgrDjEqH7ofshn4GstabN6aj78c/DVQnLp+ASt7vdksg=="  # Your ADLS account key
FILE_SYSTEM_NAME = "vendor-rfq" # Your ADLS file system name

# --------------------------------------------
# Zone and Route Mappings
# --------------------------------------------
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

# --------------------------------------------
# Truck Types
# --------------------------------------------
TRUCK_TYPES = ["Container", "LCV", "MCV"]

def get_routes(zone):
    return ZONE_ROUTE_MAP.get(zone, [])

def get_truck_combos(route, truck_type):
    return [f"{truck_type} - {route}"]

# ------------------ ADLS FUNCTIONS ------------------

def get_adls_client():
    return DataLakeServiceClient(
        account_url=f"https://{ADLS_ACCOUNT_NAME}.dfs.core.windows.net",
        credential=ADLS_ACCOUNT_KEY
    )

def append_to_region_file(region: str, df_submission: pd.DataFrame):
    region = region.lower().replace(" ", "_")  # Normalize the filename for region
    file_path = f"{region}/submissions.csv"
    adls_client = get_adls_client()
    fs_client = adls_client.get_file_system_client(FILE_SYSTEM_NAME)
    file_client = fs_client.get_file_client(file_path)

    for attempt in range(3):
        try:
            if file_client.exists():
                existing_data = file_client.download_file().readall()
                existing_df = pd.read_csv(io.BytesIO(existing_data))
                combined_df = pd.concat([existing_df, df_submission], ignore_index=True)
            else:
                combined_df = df_submission

            buffer = io.StringIO()
            combined_df.to_csv(buffer, index=False)
            bytes_data = io.BytesIO(buffer.getvalue().encode())

            file_client.upload_data(bytes_data, overwrite=True)
            return True

        except Exception as e:
            print(f"[Attempt {attempt + 1}] ADLS append failed: {e}")
            time.sleep(1)

    raise Exception("❌ Failed to append data after 3 retries.")

# ------------------ STREAMLIT UI ------------------

# Use some custom CSS to style the app
st.markdown("""
    <style>
        .stButton>button {
            background-color: #2a9d8f;
            color: white;
            font-size: 18px;
            padding: 10px 20px;
            border-radius: 10px;
            border: none;
        }
        .stButton>button:hover {
            background-color: #264653;
        }
        .stSelectbox>div>div>input {
            font-size: 18px;
            padding: 10px;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Vendor RFQ Submission")

# Handle region change & reset dependent fields
def reset_route():
    st.session_state["route_id"] = None
    st.session_state["truck_type"] = None

region = st.selectbox("Select Region", list(ZONE_ROUTE_MAP.keys()), key="region", on_change=reset_route)

if region:
    route_options = get_routes(region)
    route_ids = st.multiselect("Select Route IDs", route_options, key="route_id")

truck_types = st.multiselect("Select Truck Types", TRUCK_TYPES, key="truck_types")

# Form fields appear when route + truck type are selected
if st.session_state.get("route_id") and st.session_state.get("truck_type"):
    st.subheader("📝 Fill Truck Details")

    combo_data = []
    for route in route_ids:
        for truck_type in truck_types:
            count = st.number_input(f"{truck_type} - {route} - Truck Count", min_value=0, key=f"{route}_{truck_type}_count")
            price = st.number_input(f"{truck_type} - {route} - Price", min_value=0.0, key=f"{route}_{truck_type}_price")
            combo_data.append({"route_id": route,
                               "truck_type": truck_type,
                               "combo": f"{truck_type} - {route}",
                               "truck_count": count,
                               "price": price})

    vendor_name = st.text_input("Your Company Name", key="vendor_name")

    if st.button("Submit Response"):
        if not vendor_name:
            st.error("Please enter your company name.")
        else:
            submission_df = pd.DataFrame(combo_data)
            submission_df["region"] = region
            submission_df["vendor_name"] = vendor_name
            submission_df["submitted_at"] = pd.Timestamp.now()

            try:
                append_to_region_file(region, submission_df)
                st.success("✅ Response submitted successfully!")
                st.balloons()  # Optional: Show balloons for fun
                st.rerun()  # Refresh the page
                st.session_state["submitted"] = True  # Track submission status
            except Exception as e:
                st.error(f"❌ Error uploading to ADLS: {e}")

# Show Thank You page if submission is successful
if "submitted" in st.session_state and st.session_state["submitted"]:
    st.header("🎉 Thank You for Your Submission!")
    st.write("Your response has been successfully submitted and will be processed.")
    st.write("You can close this window or fill another form.")
    st.session_state["submitted"] = False  # Reset submission status after showing thank you message
