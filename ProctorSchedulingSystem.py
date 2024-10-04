import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from ScheduleOptimizer import ScheduleOptimizer
from SchedulePresenter import SchedulePresenter
from Schedulegenrator import ScheduleGenerator


@dataclass
class TimeRange:
    start: datetime.time
    end: datetime.time

    @classmethod
    def from_string(cls, time_range_str: str) -> 'TimeRange':
        try:
            start_str, end_str = time_range_str.split('-')
            return cls(
                start=datetime.strptime(start_str.strip(), '%H:%M').time(),
                end=datetime.strptime(end_str.strip(), '%H:%M').time()
            )
        except ValueError as e:
            raise ValueError(f"Invalid time range format: {time_range_str}. Expected format: HH:MM-HH:MM") from e


class ProctorSchedulingSystem:
    def __init__(self):
        self.proctors_df: Optional[pd.DataFrame] = None
        self.lab_schedule_df: Optional[pd.DataFrame] = None
        self.generator = ScheduleGenerator()
        self.optimizer = ScheduleOptimizer()
        self.presenter = SchedulePresenter()

        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def load_data(self, proctors_file: str, lab_schedule_file: str) -> None:
        """Load and validate proctor and lab schedule data from CSV files."""
        try:
            self.proctors_df = pd.read_csv(proctors_file)
            self.lab_schedule_df = pd.read_csv(lab_schedule_file)
            self._validate_data()
            self.logger.info("Data loaded successfully")
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {e.filename}")
            raise
        except pd.errors.EmptyDataError:
            self.logger.error("One or both CSV files are empty")
            raise ValueError("CSV files must contain data")
        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            raise

    def _validate_data(self) -> None:
        """Validate the structure and content of loaded data."""
        required_proctor_columns = ['Name', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Star', 'MaxHours']
        required_lab_columns = ['Day', 'StartTime', 'EndTime']

        self._check_required_columns(self.proctors_df, required_proctor_columns, "Proctor")
        self._check_required_columns(self.lab_schedule_df, required_lab_columns, "Lab schedule")

        self._validate_time_formats()
        self._validate_star_values()
        self._validate_max_hours()

    def _check_required_columns(self, df: pd.DataFrame, required_columns: List[str], df_name: str) -> None:
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            error_msg = f"{df_name} CSV missing required columns: {missing_columns}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

    def _validate_time_formats(self) -> None:
        """Validate time formats in both dataframes."""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

        # Validate proctor availability times
        for day in days:
            valid_times = self.proctors_df[day].apply(
                lambda x: self._validate_time_ranges(x) if pd.notna(x) else True
            )
            if not all(valid_times):
                invalid_rows = self.proctors_df[~valid_times]['Name'].tolist()
                raise ValueError(f"Invalid time format for {day} in rows: {invalid_rows}")

        # Validate lab schedule times
        for col in ['StartTime', 'EndTime']:
            try:
                self.lab_schedule_df[col] = pd.to_datetime(
                    self.lab_schedule_df[col], format='%H:%M'
                ).dt.time
            except ValueError as e:
                raise ValueError(f"Invalid time format in lab schedule {col}") from e

    def _validate_time_ranges(self, time_ranges: str) -> bool:
        """Validate individual time ranges in proctor availability."""
        if pd.isna(time_ranges):
            return True

        try:
            for time_range in str(time_ranges).split(';'):
                TimeRange.from_string(time_range.strip())
            return True
        except ValueError:
            return False

    def _validate_star_values(self) -> None:
        """Validate that Star column contains only 0 or 1."""
        invalid_stars = ~self.proctors_df['Star'].isin([0, 1])
        if any(invalid_stars):
            invalid_rows = self.proctors_df[invalid_stars]['Name'].tolist()
            raise ValueError(f"Star column must contain only 0 or 1. Invalid rows: {invalid_rows}")

    def _validate_max_hours(self) -> None:
        """Validate that MaxHours contains reasonable values."""
        invalid_hours = ~self.proctors_df['MaxHours'].between(1, 40)
        if any(invalid_hours):
            invalid_rows = self.proctors_df[invalid_hours]['Name'].tolist()
            raise ValueError(f"MaxHours must be between 1 and 40. Invalid rows: {invalid_rows}")

    def generate_schedule(self) -> str:
        """Generate an optimized schedule based on loaded data."""
        if self.proctors_df is None or self.lab_schedule_df is None:
            raise ValueError("Data must be loaded before generating schedule")

        try:
            proctor_availabilities = self._process_proctor_availabilities()
            lab_times = self._process_lab_times()

            initial_schedule = self.generator.generate_schedule(
                proctor_availabilities,
                lab_times
            )

            optimized_schedule = self.optimizer.optimize_schedule(
                initial_schedule,
                max_hours_per_week=15,
                min_shift_duration=2.5,
                max_shift_duration=4
            )

            return self.presenter.format_schedule(optimized_schedule)
        except Exception as e:
            self.logger.error(f"Error generating schedule: {str(e)}")
            raise

    def _process_proctor_availabilities(self) -> List[Dict[str, Any]]:
        """Process proctor availabilities from dataframe into required format."""
        availabilities = []
        for _, row in self.proctors_df.iterrows():
            availability = {
                'name': row['Name'],
                'star': bool(row['Star']),
                'max_hours': float(row['MaxHours']),
                'availability': {}
            }

            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                if pd.notna(row[day]):
                    time_ranges = str(row[day]).split(';')
                    availability['availability'][day] = [
                        self._parse_time_range(time_range.strip())
                        for time_range in time_ranges
                    ]

            availabilities.append(availability)
        return availabilities

    def _process_lab_times(self) -> Dict[str, List[Dict[str, datetime.time]]]:
        """Process lab times from dataframe into required format."""
        lab_times = {}
        for _, row in self.lab_schedule_df.iterrows():
            day = row['Day']
            if day not in lab_times:
                lab_times[day] = []
            lab_times[day].append({
                'start': row['StartTime'],
                'end': row['EndTime']
            })
        return lab_times

    def _parse_time_range(self, time_range_str: str) -> Dict[str, datetime.time]:
        """Parse a time range string into a dictionary with start and end times."""
        time_range = TimeRange.from_string(time_range_str)
        return {
            'start': time_range.start,
            'end': time_range.end
        }


