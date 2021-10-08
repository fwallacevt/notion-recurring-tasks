

import { existsSync, readFileSync, statSync, writeFileSync } from "fs";

export function get_last_execution_time_utc(fname) {
    // If the file exists, check when it was last modified
    if (existsSync(fname)) {
        // File exists = get timestamp of last modification
        const stats = statSync(fname);
        return { timestamp: stats.mtime };
    } else {
        // January 1st, 2000
        return { timestamp: new Date(2000, 0, 1) };
    }
}


export function update_last_execution_time_utc(fname) {
    // If the file exists, check when it was last modified
    let data = { num_executions: 1 }
    if (existsSync(fname)) {
        // File exists = get timestamp of last modification
        data = JSON.parse(readFileSync(fname));
        data.num_executions += 1;
    }

    // Write the data to our file
    writeFileSync(fname, JSON.stringify(data));
}