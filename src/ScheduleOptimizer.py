from datetime import datetime, timedelta
from typing import Dict, List, Any
import heapq

class ScheduleOptimizer:
    def optimize_schedule(self,
                          schedule: Dict[str, List[Any]],
                          max_hours_per_week: float = 15,
                          min_shift_duration: float = 2.5,
                          max_shift_duration: float = 4) -> Dict[str, List[Any]]:

        # Initialize tracking of proctor hours and priorities
        proctor_stats = self._initialize_proctor_stats(schedule)

        # Create a new optimized schedule
        optimized_schedule = {day: [] for day in schedule.keys()}

        # Sort sessions by time and process them
        sorted_sessions = self._sort_sessions(schedule)

        for day, session, original_proctors in sorted_sessions:
            # Find the best proctors for this session
            best_proctors = self._find_best_proctors(
                session,
                original_proctors,
                proctor_stats,
                max_hours_per_week,
                min_shift_duration,
                max_shift_duration
            )

            if best_proctors:
                # Update the optimized schedule
                optimized_schedule[day].append({
                    'lab_time': session['lab_time'],
                    'proctors': best_proctors
                })

                # Update proctor hours
                self._update_proctor_hours(best_proctors, proctor_stats)

        return optimized_schedule

    def _initialize_proctor_stats(self, schedule: Dict[str, List[Any]]) -> Dict[str, Dict]:
        stats = {}

        for day_schedule in schedule.values():
            for session in day_schedule:
                for proctor in session['proctors']:
                    Name = proctor['Name']  # Changed from 'Name' to 'name'
                    if Name not in stats:
                        stats[Name] = {
                            'hours': 0,
                            'star': proctor['star'],
                            'availability': 0  # Will be counted
                        }
                    stats[Name]['availability'] += 1

        return stats

    def _sort_sessions(self, schedule: Dict[str, List[Any]]) -> List[tuple]:
        sorted_sessions = []

        for day, day_schedule in schedule.items():
            for session in day_schedule:
                # Convert session time to comparable format for sorting
                start_time = datetime.combine(
                    datetime.today(),
                    session['lab_time']['start']
                )
                sorted_sessions.append((day, session, session['proctors']))

        # Sort by day and start time
        return sorted(sorted_sessions,
                      key=lambda x: (x[0], x[1]['lab_time']['start']))

    def _find_best_proctors(self,
                            session: Dict,
                            original_proctors: List[Dict],
                            proctor_stats: Dict[str, Dict],
                            max_hours_per_week: float,
                            min_shift_duration: float,
                            max_shift_duration: float) -> List[Dict]:

        # Calculate session duration
        session_start = session['lab_time']['start']
        session_end = session['lab_time']['end']
        session_duration = (datetime.combine(datetime.min, session_end) -
                            datetime.combine(datetime.min, session_start)).seconds / 3600

        # Skip if session duration is outside bounds
        if session_duration < min_shift_duration or session_duration > max_shift_duration:
            return []

        # Priority queue for selecting best proctors
        proctor_queue = []

        for proctor in original_proctors:
            Name = proctor['Name']  # Changed from 'Name' to 'name'
            stats = proctor_stats[Name]

            # Skip if adding this session would exceed max hours
            if stats['hours'] + session_duration > max_hours_per_week:
                continue

            # Calculate priority score
            priority_score = self._calculate_priority_score(stats, session_duration)

            heapq.heappush(proctor_queue,
                           (-priority_score, Name, proctor))  # Negative for max-heap

        # Select best proctors
        selected_proctors = []
        while proctor_queue and len(selected_proctors) < 2:  # Limit to 2 proctors per session
            _, _, proctor = heapq.heappop(proctor_queue)
            selected_proctors.append(proctor)

        return selected_proctors

    def _calculate_priority_score(self,
                                  stats: Dict[str, Any],
                                  session_duration: float) -> float:
        # Priorities:
        # 1. Star status (highest priority)
        # 2. Higher availability
        # 3. Lower current hours (to balance hours among proctors)

        star_factor = 1000 if stats['star'] else 0
        availability_factor = stats['availability'] * 10
        hours_factor = 15 - stats['hours']  # Inverse of current hours

        return star_factor + availability_factor + hours_factor

    def _update_proctor_hours(self,
                              proctors: List[Dict],
                              proctor_stats: Dict[str, Dict]):
        for proctor in proctors:
            Name = proctor['Name']  # Changed from 'Name' to 'name'
            assigned_time = proctor['assigned_time']
            duration = (datetime.combine(datetime.min, assigned_time['end']) -
                        datetime.combine(datetime.min, assigned_time['start'])).seconds / 3600
            proctor_stats[Name]['hours'] += duration