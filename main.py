import streamlit as st
import pandas as pd
from datetime import time
from src.ProctorSchedulingSystem import ProctorSchedulingSystem
from io import StringIO


def validate_proctor_df(df):
    required_columns = ['Name', 'MaxHours', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
                        'Sunday']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        return False, f"Missing columns in proctor availability file: {', '.join(missing_columns)}"

    return True, "Proctor availability file is valid"


def main():
    st.title("Proctor Scheduling System")

    # Initialize session state
    if 'lab_schedule' not in st.session_state:
        st.session_state.lab_schedule = []
    if 'proctor_df' not in st.session_state:
        st.session_state.proctor_df = None

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
            is_valid, message = validate_proctor_df(proctor_df)

            if is_valid:
                st.success(message)
                st.session_state.proctor_df = proctor_df
                st.subheader("Uploaded Proctor Availability")
                st.dataframe(proctor_df)

                # Star Proctor Selection
                star_proctor = st.selectbox("Select a Star Proctor", ['None'] + list(proctor_df['Name']))
                if star_proctor != 'None':
                    max_hours = st.number_input("Enter maximum hours for the Star Proctor", min_value=1, max_value=40,
                                                value=20)
                    st.session_state.proctor_df.loc[st.session_state.proctor_df['Name'] == star_proctor, 'Star'] = True
                    st.session_state.proctor_df.loc[
                        st.session_state.proctor_df['Name'] == star_proctor, 'MaxHours'] = max_hours

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

                            # Option to download the schedule
                            st.download_button(
                                label="Download Schedule",
                                data=schedule,
                                file_name="generated_schedule.txt",
                                mime="text/plain"
                            )

                        except Exception as e:
                            st.error(f"An error occurred while generating the schedule: {str(e)}")
            else:
                st.error(message)

        except pd.errors.EmptyDataError:
            st.error("The uploaded file is empty. Please upload a valid CSV file.")
        except pd.errors.ParserError:
            st.error("Unable to parse the CSV file. Please ensure it's a valid CSV format.")
        except Exception as e:
            st.error(f"An error occurred while processing the file: {str(e)}")
    else:
        st.info("Please upload the Proctor Availability CSV file to generate the schedule.")


if __name__ == "__main__":
    main()