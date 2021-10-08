

import parser from "cron-parser";
import moment from "moment";

export function toISOStringLocalTz({ date }) {
    // Convert a Date object to an ISO 8601 compliant string, in local time (e.g. suffix -04:00)
    return moment(date).format();
}

export function nextDueDate({ schedule }) {
    // Get the next due date for a task, based on the schedule string
    const options = {
        tz: "EST",
    };
    const interval = parser.parseExpression(schedule, options);
    return { next: interval.next() }
}