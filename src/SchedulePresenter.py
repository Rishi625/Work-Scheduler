from typing import Dict, List, Any


class SchedulePresenter:
    def format_schedule(self, schedule: Dict[str, List[Any]]) -> str:
        """
        Format the optimized schedule into a human-readable string.

        :param schedule: The optimized schedule dictionary
        :return: A formatted string representation of the schedule
        """
        formatted_schedule = []

        for day, sessions in schedule.items():
            formatted_schedule.append(f"\n{day}:")

            for session in sessions:
                lab_time = session['lab_time']
                proctors = session['proctors']

                formatted_schedule.append(f"  {lab_time['start']} - {lab_time['end']}:")
                for proctor in proctors:
                    formatted_schedule.append(f"    - {proctor['Name']} ({'Star' if proctor['star'] else 'Regular'})")

        return "\n".join(formatted_schedule)