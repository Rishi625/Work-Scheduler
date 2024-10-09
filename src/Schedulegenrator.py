from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import heapq


@dataclass
class TimeSlot:
    start: datetime.time
    end: datetime.time

    def duration_hours(self) -> float:
        return ((datetime.combine(datetime.min, self.end) -
                 datetime.combine(datetime.min, self.start)).seconds / 3600)

    def overlaps_with(self, other: 'TimeSlot') -> bool:
        return (self.start <= other.end and self.end >= other.start)

    def get_overlap(self, other: 'TimeSlot') -> 'TimeSlot':
        if not self.overlaps_with(other):
            return None
        return TimeSlot(
            start=max(self.start, other.start),
            end=min(self.end, other.end)
        )


class ScheduleGenerator:
    def __init__(self, min_shift_duration: float = 2.5,
                 max_shift_duration: float = 4,
                 max_weekly_hours: float = 15):
        self.min_shift_duration = min_shift_duration
        self.max_shift_duration = max_shift_duration
        self.max_weekly_hours = max_weekly_hours
        self.proctor_weekly_hours = {}

    def generate_schedule(self,
                          proctor_availabilities: List[Dict],
                          lab_times: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        # Initialize schedule and proctor tracking
        schedule = {day: [] for day in lab_times.keys()}
        self._initialize_proctor_hours(proctor_availabilities)

        # Process each day's lab sessions
        for day, lab_sessions in lab_times.items():
            day_schedule = self._generate_day_schedule(
                day, lab_sessions, proctor_availabilities)
            schedule[day] = day_schedule

        return schedule

    def _initialize_proctor_hours(self, proctor_availabilities: List[Dict]):
        self.proctor_weekly_hours = {
            proctor['Name']: 0 for proctor in proctor_availabilities
        }

    def _generate_day_schedule(self,
                               day: str,
                               lab_sessions: List[Dict],
                               proctor_availabilities: List[Dict]) -> List[Dict]:
        day_schedule = []

        # Sort lab sessions by start time
        sorted_sessions = sorted(lab_sessions,
                                 key=lambda x: x['start'])

        for lab_session in sorted_sessions:
            lab_slot = TimeSlot(start=lab_session['start'],
                                end=lab_session['end'])

            if lab_slot.duration_hours() < self.min_shift_duration:
                continue  # Skip sessions that are too short

            assigned_proctors = self._assign_proctors_to_session(
                lab_slot, proctor_availabilities, day)

            if assigned_proctors:
                day_schedule.append({
                    'lab_time': lab_session,
                    'proctors': assigned_proctors
                })

        return day_schedule

    def _assign_proctors_to_session(self,
                                    lab_slot: TimeSlot,
                                    proctor_availabilities: List[Dict],
                                    day: str) -> List[Dict]:
        # Priority queue to select best proctors
        proctor_candidates = []

        for proctor in proctor_availabilities:
            if day not in proctor['availability']:
                continue

            for avail_slot in map(lambda x: TimeSlot(**x),
                                  proctor['availability'][day]):
                overlap = lab_slot.get_overlap(avail_slot)

                if overlap and self._is_valid_assignment(
                        proctor['Name'], overlap.duration_hours()):
                    priority_score = self._calculate_priority_score(
                        proctor, overlap.duration_hours())

                    heapq.heappush(
                        proctor_candidates,
                        (-priority_score, proctor, overlap)  # Negative for max-heap
                    )

        return self._select_best_proctors(proctor_candidates, lab_slot)

    def _is_valid_assignment(self, proctor_name: str, duration: float) -> bool:
        current_hours = self.proctor_weekly_hours[proctor_name]
        return (duration >= self.min_shift_duration and
                duration <= self.max_shift_duration and
                current_hours + duration <= self.max_weekly_hours)

    def _calculate_priority_score(self,
                                  proctor: Dict,
                                  duration: float) -> float:
        # Factors to consider:
        # 1. Star status (highest priority)
        # 2. Current weekly hours (to balance workload)
        # 3. Total availability (prefer those with more availability)

        star_factor = 1000 if proctor['star'] else 0
        hours_factor = self.max_weekly_hours - self.proctor_weekly_hours[proctor['Name']]
        availability_factor = sum(len(slots) for slots in
                                  proctor['availability'].values())

        return star_factor + hours_factor + (availability_factor * 0.1)

    def _select_best_proctors(self,
                              candidates: List[Tuple],
                              lab_slot: TimeSlot) -> List[Dict]:
        selected_proctors = []
        target_proctors = 2  # We want 2 proctors per session if possible

        while candidates and len(selected_proctors) < target_proctors:
            _, proctor, overlap = heapq.heappop(candidates)

            # Update proctor's weekly hours
            self.proctor_weekly_hours[proctor['Name']] += overlap.duration_hours()

            selected_proctors.append({
                'Name': proctor['Name'],
                'star': proctor['star'],
                'assigned_time': {
                    'start': overlap.start,
                    'end': overlap.end
                }
            })

        return selected_proctors
