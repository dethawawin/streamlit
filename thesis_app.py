import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import xlsxwriter
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Initialize session state
if "schedule_table" not in st.session_state:
    st.session_state.schedule_table = None
if "updated_stages" not in st.session_state:
    st.session_state.updated_stages = None
if "warna_aktivitas" not in st.session_state:
    st.session_state.warna_aktivitas = None
if "schedule_figure" not in st.session_state:
    st.session_state.schedule_figure = None
if "is_valid" not in st.session_state:
    st.session_state.is_valid = False

# Function to display the header
def display_header():
    st.title("PT XYZ Side Dump Truck Departure Scheduling")
    st.markdown("---")  # Adds a horizontal line for better separation

def download_excel(df, filename):
    # Create an in-memory buffer
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Schedule")  # Write DataFrame to Excel
        writer.save()  # Save the Excel writer
    output.seek(0)  # Rewind the buffer to the beginning

    # Provide a download button in Streamlit
    st.download_button(
        type='primary',
        label="Download Schedule as Excel",
        data=output,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def download_chart_as_png(fig, date, shift, filename_prefix="gantt_chart"):
    # Create an in-memory buffer
    output = BytesIO()
    fig.savefig(output, format="png", bbox_inches="tight")
    output.seek(0)  # Rewind the buffer to the beginning

    # Format the filename with the operation date and shift
    formatted_date = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date)
    sanitized_shift = shift.replace(":", "-").replace(" ", "_")  # Replace invalid characters
    filename = f"{filename_prefix}_{formatted_date}_{sanitized_shift}.png"

    # Provide a download button in Streamlit
    st.download_button(
        type='primary',
        label="Download Gantt Chart as PNG",
        data=output,
        file_name=filename,
        mime="image/png"
    )

def generate_gantt_chart(schedule_table, updated_stages, warna_aktivitas):
    # Prepare data for Gantt chart
    schedule_data = {}
    for row in schedule_table:
        truck_name = row["Truck Name"]
        if truck_name not in schedule_data:
            schedule_data[truck_name] = []
        start_time = datetime.strptime(row["Departure Time"], "%H:%M:%S")
        for stage, duration in updated_stages.items():
            end_time = start_time + timedelta(minutes=duration)
            schedule_data[truck_name].append((stage, start_time, end_time))
            start_time = end_time

    # Create Gantt chart
    fig, ax = plt.subplots(figsize=(22, 10))
    for truck, stages in schedule_data.items():
        for stage, start, end in stages:
            ax.barh(truck, (end - start).seconds / 60, left=start.hour * 60 + start.minute,
                    color=warna_aktivitas.get(stage, "gray"), edgecolor="black")

    # Add labels and legend
    ax.set_xlabel("Time (minutes)")
    ax.set_ylabel("Truck Name")
    # Add dynamic title with date and shift
    formatted_date = date.strftime("%Y-%m-%d")  # Format the date
    title = f"Gantt Chart for Truck Departure Schedule ({formatted_date}, Shift: {shift})"
    ax.set_title(title, fontsize=26)  # Set title with larger font size

    # Add legend outside the chart
    legend_patches = [mpatches.Patch(color=color, label=stage) for stage, color in warna_aktivitas.items()]
    ax.legend(
        handles=legend_patches, 
        title="Stages", 
        loc="upper left", 
        bbox_to_anchor=(1.05, 1),  # Position the legend to the right
        borderaxespad=0
    )

    # Adjust layout to make room for the legend
    plt.tight_layout(rect=[0, 0, 0.85, 1])  # Leave space on the right
    return fig

# Sidebar menu
with st.sidebar:
    selected_page = option_menu(
        menu_title="Menu",
        options=["Homepage", "Create a New Schedule"],
        icons=["house-door-fill", "calendar-plus-fill"],
        menu_icon='list',
        default_index=0
    )

if selected_page == "Homepage":
    display_header()
    st.subheader('About Application')
    st.markdown('The Side Dump Truck departure scheduling system application is designed to efficiently organize and monitor truck departure schedules for coal hauling activities.')
    st.subheader('User Guidance')
    st.markdown("""
    #### Steps to Use the Application:
    1. Navigate to the application and click on the Create Schedule menu.
    2. Enter the required date and shift for the new schedule in the provided fields.
    3. Upload the Ready for Use (RFU) Side Dump Truck data file in .xlsx format with the necessary columns: truckID and capacity.
    4. Input the planned hauling tonnage target into the designated field.
    5. The system validates the tonnage target against available truck capacity.
    6. Generate and view the departure schedule.
    """)

if selected_page == "Create a New Schedule":

    st.title("Create a New Schedule")
    st.write("Fill in the details below to create a new schedule for the Side Dump Truck.")
    date = st.date_input("Select Date:")
    shift = st.radio("Select Shift:", ["A (07:00:00 - 18:59:59)", "B (19:00:00 - 06:59:59)"])
    uploaded_file = st.file_uploader(
        "Ensure the file is in Excel format (.xlsx) and includes 'truckID' and 'capacity' columns.",
        type=["xlsx"]
    )

    if uploaded_file:
        try:
            data = pd.read_excel(uploaded_file)
            required_columns = {"truckID", "capacity"}
            if not required_columns.issubset(data.columns):
                st.error(f"Error: Missing required columns {required_columns - set(data.columns)} in the uploaded file.")
                st.session_state.is_valid = False
            else:
                st.write("Uploaded RFU Data Preview:")
                st.dataframe(data.head(5))
                capacities = data['capacity']
                truck_ids = data['truckID'].tolist()
                max_trips_per_truck = 2
                max_capacity = sum(capacities * max_trips_per_truck)

                # Input hauling target with validation
                hauling_target = st.number_input(
                    f"Enter Planned Hauling Tonnage Target (maximum {max_capacity:.2f} tons):",
                    min_value=0,
                    max_value=max_capacity
                )

                if hauling_target > max_capacity:
                    st.error(f"Error: Hauling target exceeds maximum capacity of {max_capacity:.2f} tons.")
                    st.session_state.is_valid = False
                elif hauling_target <= 0:
                    st.error("Error: Hauling target must be greater than 0.")
                    st.session_state.is_valid = False
                else:
                    st.session_state.is_valid = True

                # Generate Schedule and Gantt Chart
                if st.button("Generate Schedule", type="primary") and st.session_state.is_valid:
                    updated_stages = {
                        "Travelling to Stockpile": 68.5,
                        "Loading": 9.2,
                        "Hauling": 141.4,
                        "Timbang Kotor": 3.08,
                        "Dumping": 5.07,
                        "Timbang Kosong": 1.82,
                        "Travelling to Workshop": 42.5,
                        "Istirahat": 30
                    }
                    warna_aktivitas = {
                        "Travelling to Stockpile": "gold",
                        "Loading": "steelblue",
                        "Hauling": "forestgreen",
                        "Timbang Kotor": "blueviolet",
                        "Dumping": "red",
                        "Timbang Kosong": "orange",
                        "Travelling to Workshop": "coral",
                        "Istirahat": "gray"
                    }

                    schedule_table = []
                    total_hauling = 0
                    num_trips_per_truck = {truck: 0 for truck in truck_ids}
                    trip_index = 0
                    base_departure_time = datetime.strptime("07:00:00", "%H:%M:%S")
                    last_trip_end_time = {truck: base_departure_time for truck in truck_ids}

                    while total_hauling < hauling_target:
                        current_truck = truck_ids[trip_index % len(truck_ids)]
                        capacity = capacities[truck_ids.index(current_truck)]

                        if num_trips_per_truck[current_truck] >= max_trips_per_truck:
                            trip_index += 1
                            continue

                        if num_trips_per_truck[current_truck] == 0:
                            departure_time = base_departure_time + timedelta(minutes=trip_index * 10)
                        else:
                            departure_time = last_trip_end_time[current_truck] + timedelta(minutes=updated_stages["Istirahat"])

                        eta_stockpile = departure_time + timedelta(minutes=updated_stages["Travelling to Stockpile"])
                        eta_crusher = eta_stockpile + timedelta(minutes=updated_stages["Hauling"] + updated_stages["Timbang Kotor"])
                        eta_workshop = eta_crusher + timedelta(minutes=updated_stages["Dumping"] + updated_stages["Timbang Kosong"] + updated_stages["Travelling to Workshop"])

                        schedule_table.append({
                            "Truck Name": current_truck,
                            "Departure Time": departure_time.strftime("%H:%M:%S"),
                            "ETA Stockpile": eta_stockpile.strftime("%H:%M:%S"),
                            "ETA Crusher": eta_crusher.strftime("%H:%M:%S"),
                            "ETA Workshop": eta_workshop.strftime("%H:%M:%S"),
                            "Tonnage Plan (ton)": capacity
                        })

                        total_hauling += capacity
                        num_trips_per_truck[current_truck] += 1
                        last_trip_end_time[current_truck] = eta_workshop
                        trip_index += 1

                        if total_hauling >= hauling_target:
                            break

                    st.session_state.schedule_table = pd.DataFrame(schedule_table)
                    st.session_state.updated_stages = updated_stages
                    st.session_state.warna_aktivitas = warna_aktivitas
                    st.session_state.schedule_figure = generate_gantt_chart(schedule_table, updated_stages, warna_aktivitas)

        except Exception as e:
            st.error(f"Error reading the uploaded file. Please check the file format. Details: {str(e)}")

    # Display results only if valid
    if st.session_state.is_valid and st.session_state.schedule_table is not None:
        st.markdown("---")
        st.subheader("PT XYZ - Coal Hauling SDT Departure Schedule")
        st.dataframe(st.session_state.schedule_table)
        download_excel(st.session_state.schedule_table, f"Schedule_{date.strftime('%Y-%m-%d')}.xlsx")

    if st.session_state.is_valid and st.session_state.schedule_figure is not None:
        st.pyplot(st.session_state.schedule_figure)
        download_chart_as_png(st.session_state.schedule_figure, date, shift)

# Show "Clear Results" button only if results exist
   # Show "Clear Results" button only if results exist
if st.session_state.schedule_table is not None and st.session_state.schedule_figure is not None:
    if st.button("Clear Schedule"):
        # Reset all session state variables
        st.session_state.schedule_table = None
        st.session_state.updated_stages = None
        st.session_state.warna_aktivitas = None
        st.session_state.schedule_figure = None

        # Reset user input fields
        st.session_state.date = None
        st.session_state.shift = None
        st.session_state.uploaded_file = None
        st.session_state.hauling_target = 0
        st.session_state.is_valid = False
