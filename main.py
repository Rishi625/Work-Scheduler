import streamlit as st
import pandas as pd
from datetime import time
from src.ProctorSchedulingSystem import ProctorSchedulingSystem
from io import StringIO


def main():
    st.title("Proctor Scheduling System")

    # Initialize session state
    if 'lab_schedule' not in st.session_state:
        st.session_state.lab_schedule = []
    if 'proctor_df' not in st.session_state:
        st.session_state.proctor_df = None
    if 'star_proctors' not in st.session_state:
        st.session_state.star_proctors = {}
    if 'proctor_hours' not in st.session_state:
        st.session_state.proctor_hours = {}

    # Lab Schedule Input
    st.header("Lab Schedule")
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    with st.form("lab_schedule_form"):
        day = st.selectbox("Day", days_of_week)
        start_time = st.time_input("Start Time", value=time(9, 0))
        end_time = st.time_input("End Time", value=time(17, 0))
        if st.form_submit_button("Add Lab Session"):
            st.session_state.lab_schedule.append({
                "Day": day,
                "StartTime": start_time,
                "EndTime": end_time
            })

    # Display current lab schedule
    if st.session_state.lab_schedule:
        st.subheader("Current Lab Schedule")
        st.table(st.session_state.lab_schedule)

    # Proctor Availability File Upload
    st.header("Proctor Availability")
    proctor_file = st.file_uploader("Upload Proctor Availability CSV", type="csv")

    if proctor_file is not None:
        try:
            proctor_df = pd.read_csv(StringIO(proctor_file.getvalue().decode("utf-8")))
            st.success("Proctor availability file uploaded successfully.")

            # Star Proctor Selection and Hours Assignment
            st.subheader("Proctor Configuration")

            # Create columns for better layout
            col1, col2 = st.columns(2)

            with col1:
                st.write("Select Star Proctors")
                for index, row in proctor_df.iterrows():
                    proctor_name = row['Name']
                    # Use the session state to maintain selections
                    if proctor_name not in st.session_state.star_proctors:
                        st.session_state.star_proctors[proctor_name] = False

                    st.session_state.star_proctors[proctor_name] = st.checkbox(
                        f"Mark {proctor_name}",
                        value=st.session_state.star_proctors[proctor_name],
                        key=f"star_{proctor_name}"
                    )

            with col2:
                st.write("Assign Weekly Hours")
                for index, row in proctor_df.iterrows():
                    proctor_name = row['Name']
                    if proctor_name not in st.session_state.proctor_hours:
                        st.session_state.proctor_hours[proctor_name] = 4.0

                    hours = st.number_input(
                        f"Hours for {proctor_name}",
                        min_value=1.0,
                        max_value=40.0,
                        value=st.session_state.proctor_hours[proctor_name],
                        step=0.5,
                        key=f"hours_{proctor_name}"
                    )
                    st.session_state.proctor_hours[proctor_name] = hours

            # Update the DataFrame with star status and hours
            proctor_df['Star'] = proctor_df['Name'].map(
                lambda x: 1 if st.session_state.star_proctors.get(x, False) else 0)
            proctor_df['MaxHours'] = proctor_df['Name'].map(lambda x: st.session_state.proctor_hours.get(x, 4.0))

            # Display updated proctor information
            st.subheader("Updated Proctor Information")
            st.dataframe(proctor_df)

            # Store the updated DataFrame in session state
            st.session_state.proctor_df = proctor_df

            # Generate Schedule Button
            if st.button("Generate Schedule"):
                if not st.session_state.lab_schedule:
                    st.error("Please add lab schedule before generating the schedule.")
                else:
                    try:
                        # Create DataFrame from session state for lab schedule
                        lab_df = pd.DataFrame(st.session_state.lab_schedule)

                        # Initialize ProctorSchedulingSystem
                        scheduler = ProctorSchedulingSystem()
                        scheduler.proctors_df = st.session_state.proctor_df
                        scheduler.lab_schedule_df = lab_df

                        # Generate schedule
                        schedule = scheduler.generate_schedule()
                        st.success("Schedule generated successfully!")
                        st.text(schedule)

                        # Add schedule analysis
                        st.subheader("Schedule Analysis")
                        for proctor_name in st.session_state.proctor_hours:
                            hours = st.session_state.proctor_hours[proctor_name]
                            if hours <= 4:
                                st.info(f"{proctor_name}'s {hours} hours will be covered in a single shift")

                        # Option to download the schedule
                        st.download_button(
                            label="Download Schedule",
                            data=schedule,
                            file_name="generated_schedule.txt",
                            mime="text/plain"
                        )

                    except Exception as e:
                        st.error(f"An error occurred while generating the schedule: {str(e)}")

        except Exception as e:
            st.error(f"An error occurred while processing the file: {str(e)}")
    else:
        st.info("Please upload the Proctor Availability CSV file to generate the schedule.")


if __name__ == "__main__":
    main()