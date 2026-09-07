# Silent-fault hand-audit pack (R3)

Mark a row IMPLAUSIBLE if a human operator would notice the
mutation WITHOUT ground truth. Pass bar: >= 95% plausible per env.
Fill the verdict column with `ok` or `implausible: <why>`.


## cal (50 samples)

| # | family | tool | nominal | mutated | verdict |
|---|--------|------|---------|---------|---------|
| 0 | S1 | cal.get | `{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50", "tz": "America/Chicago", "location": "room-2"}` | `{"id": "ev100", "title": "latency sync", "start": "2026-09-08T13:00", "end": "2026-09-08T13:50", "tz": "America/Chicago", "location": "room-2"}` |  |
| 1 | S2 | cal.get | `{"id": "ev101", "title": "node sync", "start": "2026-09-08T11:00", "end": "2026-09-08T11:50", "tz": "America/Chicago", "location": "room-2"}` | `{"id": "ev101", "title": "node sync", "start": "2026-09-08T05:00", "end": "2026-09-08T05:50", "tz": "America/Chicago", "location": "room-2"}` |  |
| 2 | S2 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T05:00", "end": "2026-09-10T05:50"}, {"id": "ev106", "title": "budget sync", "start": "2` |  |
| 3 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "14:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 4 | S3 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [], "count": 0}` |  |
| 5 | S4 | cal.list | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` |  |
| 6 | S1 | cal.get | `{"id": "ev106", "title": "budget sync", "start": "2026-09-10T13:00", "end": "2026-09-10T13:50", "tz": "America/New_York", "location": "room-6"}` | `{"id": "ev106", "title": "budget sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50", "tz": "America/New_York", "location": "room-6"}` |  |
| 7 | S2 | cal.get | `{"id": "ev107", "title": "budget sync", "start": "2026-09-10T09:00", "end": "2026-09-10T09:50", "tz": "UTC", "location": "room-1"}` | `{"id": "ev107", "title": "budget sync", "start": "2026-09-10T14:00", "end": "2026-09-10T14:50", "tz": "UTC", "location": "room-1"}` |  |
| 8 | S2 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T10:00", "end": "2026-09-08T10:50"}, {"id": "ev101", "title": "node sync", "start": "20` |  |
| 9 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "13:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 10 | S3 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [], "count": 0}` |  |
| 11 | S4 | cal.list | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T13:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T14:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` |  |
| 12 | S1 | cal.get | `{"id": "ev102", "title": "summary sync", "start": "2026-09-08T13:00", "end": "2026-09-08T13:50", "tz": "America/New_York", "location": "room-3"}` | `{"id": "ev102", "title": "summary sync", "start": "2026-09-08T12:00", "end": "2026-09-08T12:50", "tz": "America/New_York", "location": "room-3"}` |  |
| 13 | S2 | cal.get | `{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50", "tz": "UTC", "location": "room-1"}` | `{"id": "ev103", "title": "config sync", "start": "2026-09-09T15:00", "end": "2026-09-09T15:50", "tz": "UTC", "location": "room-1"}` |  |
| 14 | S2 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T05:00", "end": "2026-09-10T05:50"}, {"id": "ev106", "title": "budget sync", "start": "2` |  |
| 15 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "14:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 16 | S3 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [], "count": 0}` |  |
| 17 | S4 | cal.list | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` |  |
| 18 | S1 | cal.get | `{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T13:00", "end": "2026-09-11T13:50", "tz": "America/New_York", "location": "room-6"}` | `{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T11:00", "end": "2026-09-11T11:50", "tz": "America/New_York", "location": "room-6"}` |  |
| 19 | S2 | cal.get | `{"id": "ev109", "title": "shard sync", "start": "2026-09-11T10:00", "end": "2026-09-11T10:50", "tz": "America/New_York", "location": "room-4"}` | `{"id": "ev109", "title": "shard sync", "start": "2026-09-11T05:00", "end": "2026-09-11T05:50", "tz": "America/New_York", "location": "room-4"}` |  |
| 20 | S2 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T09:00", "end": "2026-09-08T09:50"}, {"id": "ev101", "title": "node sync", "start": "20` |  |
| 21 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "13:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 22 | S3 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [], "count": 0}` |  |
| 23 | S4 | cal.list | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T13:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T14:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` |  |
| 24 | S1 | cal.get | `{"id": "ev104", "title": "config sync", "start": "2026-09-09T14:00", "end": "2026-09-09T14:50", "tz": "UTC", "location": "room-8"}` | `{"id": "ev104", "title": "config sync", "start": "2026-09-09T13:00", "end": "2026-09-09T13:50", "tz": "UTC", "location": "room-8"}` |  |
| 25 | S2 | cal.get | `{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50", "tz": "America/Chicago", "location": "room-2"}` | `{"id": "ev105", "title": "status sync", "start": "2026-09-10T05:00", "end": "2026-09-10T05:50", "tz": "America/Chicago", "location": "room-2"}` |  |
| 26 | S2 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T16:00", "end": "2026-09-10T16:50"}, {"id": "ev106", "title": "budget sync", "start": "2` |  |
| 27 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "14:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 28 | S3 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [], "count": 0}` |  |
| 29 | S4 | cal.list | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` |  |
| 30 | S1 | cal.get | `{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50", "tz": "America/Chicago", "location": "room-2"}` | `{"id": "ev100", "title": "latency sync", "start": "2026-09-08T13:00", "end": "2026-09-08T13:50", "tz": "America/Chicago", "location": "room-2"}` |  |
| 31 | S2 | cal.get | `{"id": "ev101", "title": "node sync", "start": "2026-09-08T11:00", "end": "2026-09-08T11:50", "tz": "America/Chicago", "location": "room-2"}` | `{"id": "ev101", "title": "node sync", "start": "2026-09-08T05:00", "end": "2026-09-08T05:50", "tz": "America/Chicago", "location": "room-2"}` |  |
| 32 | S2 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T10:00", "end": "2026-09-08T10:50"}, {"id": "ev101", "title": "node sync", "start": "20` |  |
| 33 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "13:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 34 | S3 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [], "count": 0}` |  |
| 35 | S4 | cal.list | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T13:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T13:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` |  |
| 36 | S1 | cal.get | `{"id": "ev106", "title": "budget sync", "start": "2026-09-10T13:00", "end": "2026-09-10T13:50", "tz": "America/New_York", "location": "room-6"}` | `{"id": "ev106", "title": "budget sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50", "tz": "America/New_York", "location": "room-6"}` |  |
| 37 | S2 | cal.get | `{"id": "ev107", "title": "budget sync", "start": "2026-09-10T09:00", "end": "2026-09-10T09:50", "tz": "UTC", "location": "room-1"}` | `{"id": "ev107", "title": "budget sync", "start": "2026-09-10T04:00", "end": "2026-09-10T04:50", "tz": "UTC", "location": "room-1"}` |  |
| 38 | S2 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T15:00", "end": "2026-09-10T15:50"}, {"id": "ev106", "title": "budget sync", "start": "2` |  |
| 39 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "14:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 40 | S3 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [], "count": 0}` |  |
| 41 | S4 | cal.list | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` | `{"events": [{"id": "ev103", "title": "config sync", "start": "2026-09-09T11:00", "end": "2026-09-09T10:50"}, {"id": "ev104", "title": "config sync", "start": "2` |  |
| 42 | S1 | cal.get | `{"id": "ev102", "title": "summary sync", "start": "2026-09-08T13:00", "end": "2026-09-08T13:50", "tz": "America/New_York", "location": "room-3"}` | `{"id": "ev102", "title": "summary sync", "start": "2026-09-08T12:00", "end": "2026-09-08T12:50", "tz": "America/New_York", "location": "room-3"}` |  |
| 43 | S2 | cal.get | `{"id": "ev103", "title": "config sync", "start": "2026-09-09T10:00", "end": "2026-09-09T10:50", "tz": "UTC", "location": "room-1"}` | `{"id": "ev103", "title": "config sync", "start": "2026-09-09T15:00", "end": "2026-09-09T15:50", "tz": "UTC", "location": "room-1"}` |  |
| 44 | S2 | cal.list | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T15:00", "end": "2026-09-08T15:50"}, {"id": "ev101", "title": "node sync", "start": "20` | `{"events": [{"id": "ev100", "title": "latency sync", "start": "2026-09-08T09:00", "end": "2026-09-08T09:50"}, {"id": "ev101", "title": "node sync", "start": "20` |  |
| 45 | S3 | cal.free | `{"slots": ["09:00", "11:00", "12:00", "13:00", "15:00", "16:00"], "count": 6}` | `{"slots": [], "count": 0}` |  |
| 46 | S3 | cal.list | `{"events": [{"id": "ev105", "title": "status sync", "start": "2026-09-10T11:00", "end": "2026-09-10T11:50"}, {"id": "ev106", "title": "budget sync", "start": "2` | `{"events": [], "count": 0}` |  |
| 47 | S4 | cal.list | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T13:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` | `{"events": [{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T14:00", "end": "2026-09-11T13:50"}, {"id": "ev109", "title": "shard sync", "start": "2` |  |
| 48 | S1 | cal.get | `{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T13:00", "end": "2026-09-11T13:50", "tz": "America/New_York", "location": "room-6"}` | `{"id": "ev108", "title": "cluster sync", "start": "2026-09-11T11:00", "end": "2026-09-11T11:50", "tz": "America/New_York", "location": "room-6"}` |  |
| 49 | S2 | cal.get | `{"id": "ev109", "title": "shard sync", "start": "2026-09-11T10:00", "end": "2026-09-11T10:50", "tz": "America/New_York", "location": "room-4"}` | `{"id": "ev109", "title": "shard sync", "start": "2026-09-11T04:00", "end": "2026-09-11T04:50", "tz": "America/New_York", "location": "room-4"}` |  |

## compute (50 samples)

| # | family | tool | nominal | mutated | verdict |
|---|--------|------|---------|---------|---------|
| 0 | S1 | compute.stats | `{"value": 4.05, "n": 4}` | `{"value": 3.7, "n": 3}` |  |
| 1 | S2 | compute.convert | `{"value": 280.45, "unit": "K"}` | `{"value": 7.3, "unit": "K"}` |  |
| 2 | S3 | compute.stats | `{"value": 4.4, "n": 6}` | `{"value": 0.0, "n": 0}` |  |
| 3 | S4 | compute.calc | `{"value": 87.0}` | `{"value": 89.02}` |  |
| 4 | S1 | compute.stats | `{"value": 7.2, "n": 5}` | `{"value": 6.85, "n": 4}` |  |
| 5 | S2 | compute.convert | `{"value": 289.65, "unit": "K"}` | `{"value": 16.5, "unit": "K"}` |  |
| 6 | S3 | compute.stats | `{"value": 7.2, "n": 4}` | `{"value": 0.0, "n": 0}` |  |
| 7 | S4 | compute.calc | `{"value": 90.0}` | `{"value": 91.78}` |  |
| 8 | S1 | compute.stats | `{"value": 6.5, "n": 6}` | `{"value": 6.92, "n": 5}` |  |
| 9 | S2 | compute.convert | `{"value": 278.15, "unit": "K"}` | `{"value": 5.0, "unit": "K"}` |  |
| 10 | S3 | compute.stats | `{"value": 3.0, "n": 5}` | `{"value": 0.0, "n": 0}` |  |
| 11 | S4 | compute.calc | `{"value": 92.0}` | `{"value": 87.41}` |  |
| 12 | S1 | compute.stats | `{"value": 4.75, "n": 4}` | `{"value": 4.4, "n": 3}` |  |
| 13 | S2 | compute.convert | `{"value": 287.35, "unit": "K"}` | `{"value": 14.2, "unit": "K"}` |  |
| 14 | S3 | compute.stats | `{"value": 5.1, "n": 6}` | `{"value": 0.0, "n": 0}` |  |
| 15 | S4 | compute.calc | `{"value": 79.0}` | `{"value": 82.48}` |  |
| 16 | S1 | compute.stats | `{"value": 7.9, "n": 5}` | `{"value": 7.55, "n": 4}` |  |
| 17 | S2 | compute.convert | `{"value": 296.55, "unit": "K"}` | `{"value": 23.4, "unit": "K"}` |  |
| 18 | S3 | compute.stats | `{"value": 7.9, "n": 4}` | `{"value": 0.0, "n": 0}` |  |
| 19 | S4 | compute.calc | `{"value": 215.0}` | `{"value": 219.32}` |  |
| 20 | S1 | compute.stats | `{"value": 5.916667, "n": 6}` | `{"value": 6.08, "n": 5}` |  |
| 21 | S2 | compute.convert | `{"value": 285.05, "unit": "K"}` | `{"value": 11.9, "unit": "K"}` |  |
| 22 | S3 | compute.stats | `{"value": 3.0, "n": 5}` | `{"value": 0.0, "n": 0}` |  |
| 23 | S4 | compute.calc | `{"value": 206.0}` | `{"value": 196.86}` |  |
| 24 | S1 | compute.stats | `{"value": 5.45, "n": 4}` | `{"value": 5.1, "n": 3}` |  |
| 25 | S2 | compute.convert | `{"value": 294.25, "unit": "K"}` | `{"value": 21.1, "unit": "K"}` |  |
| 26 | S3 | compute.stats | `{"value": 5.8, "n": 6}` | `{"value": 0.0, "n": 0}` |  |
| 27 | S4 | compute.calc | `{"value": 196.0}` | `{"value": 189.61}` |  |
| 28 | S1 | compute.stats | `{"value": 8.6, "n": 5}` | `{"value": 8.25, "n": 4}` |  |
| 29 | S2 | compute.convert | `{"value": 282.75, "unit": "K"}` | `{"value": 9.6, "unit": "K"}` |  |
| 30 | S3 | compute.stats | `{"value": 3.0, "n": 4}` | `{"value": 0.0, "n": 0}` |  |
| 31 | S4 | compute.calc | `{"value": 171.0}` | `{"value": 168.45}` |  |
| 32 | S1 | compute.stats | `{"value": 5.333333, "n": 6}` | `{"value": 5.24, "n": 5}` |  |
| 33 | S2 | compute.convert | `{"value": 291.95, "unit": "K"}` | `{"value": 18.8, "unit": "K"}` |  |
| 34 | S3 | compute.stats | `{"value": 3.7, "n": 5}` | `{"value": 0.0, "n": 0}` |  |
| 35 | S4 | compute.calc | `{"value": 138.0}` | `{"value": 133.55}` |  |
| 36 | S1 | compute.stats | `{"value": 6.15, "n": 4}` | `{"value": 5.8, "n": 3}` |  |
| 37 | S2 | compute.convert | `{"value": 280.45, "unit": "K"}` | `{"value": 7.3, "unit": "K"}` |  |
| 38 | S3 | compute.stats | `{"value": 6.5, "n": 6}` | `{"value": 0.0, "n": 0}` |  |
| 39 | S4 | compute.calc | `{"value": 354.0}` | `{"value": 342.05}` |  |
| 40 | S1 | compute.stats | `{"value": 7.76, "n": 5}` | `{"value": 8.95, "n": 4}` |  |
| 41 | S2 | compute.convert | `{"value": 289.65, "unit": "K"}` | `{"value": 16.5, "unit": "K"}` |  |
| 42 | S3 | compute.stats | `{"value": 3.0, "n": 4}` | `{"value": 0.0, "n": 0}` |  |
| 43 | S4 | compute.calc | `{"value": 325.0}` | `{"value": 332.06}` |  |
| 44 | S1 | compute.stats | `{"value": 4.75, "n": 6}` | `{"value": 4.4, "n": 5}` |  |
| 45 | S2 | compute.convert | `{"value": 278.15, "unit": "K"}` | `{"value": 5.0, "unit": "K"}` |  |
| 46 | S3 | compute.stats | `{"value": 4.4, "n": 5}` | `{"value": 0.0, "n": 0}` |  |
| 47 | S4 | compute.calc | `{"value": 295.0}` | `{"value": 298.19}` |  |
| 48 | S1 | compute.stats | `{"value": 6.85, "n": 4}` | `{"value": 6.5, "n": 3}` |  |
| 49 | S2 | compute.convert | `{"value": 287.35, "unit": "K"}` | `{"value": 14.2, "unit": "K"}` |  |

## fs (50 samples)

| # | family | tool | nominal | mutated | verdict |
|---|--------|------|---------|---------|---------|
| 0 | S1 | fs.read | `{"content": "deploy latency report status metric update. deploy system draft review config shard report. release latency config budget. draft draft metric syste` | `{"content": "status pipeline backlog node update sensor node. status latency archive release cluster status. cluster latency summary summary pipeline review lat` |  |
| 1 | S2 | fs.read | `{"content": "deploy review update sensor shard archive status archive. config status deploy report update. pipeline cluster status config config pipeline. revie` | `{"content": "deploy review update sensor shard archive status archive. config status deploy report update. pipeline cluster status config config pipeline. revie` |  |
| 2 | S3 | fs.list | `{"entries": [{"name": "budget_0.txt", "type": "file"}, {"name": "budget_3.txt", "type": "file"}, {"name": "latency_1.txt", "type": "file"}, {"name": "report_2.t` | `{"entries": [], "count": 0}` |  |
| 3 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 4}, {"path": "/data/report_2.txt", "count": 1}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 4 | S4 | fs.stat | `{"exists": true, "size": 214, "version": 3, "mtime": 1757010800}` | `{"exists": true, "size": 223, "version": 2, "mtime": 1757010800}` |  |
| 5 | S1 | fs.read | `{"content": "system backlog cluster release archive. cluster metric review update release archive cluster cluster. The build number is 5364.", "version": 3, "mt` | `{"content": "latency system metric sensor config status release. archive metric pipeline deploy update. The build number is 1866.", "version": 1, "mtime": 17570` |  |
| 6 | S2 | fs.read | `{"content": "system backlog update config status update pipeline. update node review draft draft update release. The build number is 5198.", "version": 2, "mtim` | `{"content": "system backlog update config status update pipeline. update node review draft draft update release. The build number is 5.198.", "version": 2, "mti` |  |
| 7 | S3 | fs.list | `{"entries": [{"name": "draft_3.txt", "type": "file"}, {"name": "metric_2.txt", "type": "file"}, {"name": "pointer_0.txt", "type": "file"}, {"name": "release_0.t` | `{"entries": [], "count": 0}` |  |
| 8 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 1}, {"path": "/data/report_2.txt", "count": 3}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 9 | S4 | fs.stat | `{"exists": true, "size": 181, "version": 2, "mtime": 1757050400}` | `{"exists": true, "size": 174, "version": 1, "mtime": 1757050400}` |  |
| 10 | S1 | fs.read | `{"content": "See the file at /docs/draft_3.txt for the latest figures.", "version": 2, "mtime": 1757100000}` | `{"content": "See the file at /data/budget_3.txt for the latest figures.", "version": 1, "mtime": 1757100000}` |  |
| 11 | S2 | fs.read | `{"content": "config metric latency metric budget pipeline sensor. cluster shard shard cluster shard budget system cluster. backlog review release cluster metric` | `{"content": "config metric latency metric budget pipeline sensor. cluster shard shard cluster shard budget system cluster. backlog review release cluster metric` |  |
| 12 | S3 | fs.list | `{"entries": [{"name": "draft_3.txt", "type": "file"}, {"name": "pipeline_2.txt", "type": "file"}, {"name": "release_1.txt", "type": "file"}, {"name": "sensor_0.` | `{"entries": [], "count": 0}` |  |
| 13 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/budget_3.txt", "count": 1}, {"path": "/data/report_2.txt", "count": 1}, {"path": "/docs` | `{"matches": [], "total": 0}` |  |
| 14 | S4 | fs.stat | `{"exists": true, "size": 189, "version": 3, "mtime": 1757018000}` | `{"exists": true, "size": 203, "version": 2, "mtime": 1757018000}` |  |
| 15 | S1 | fs.read | `{"content": "sensor report shard summary release. pipeline report status summary draft system. deploy sensor release sensor node system summary pipeline. backlo` | `{"content": "update sensor shard draft pipeline cluster budget status. draft system config release latency cluster release sensor. status backlog review sensor ` |  |
| 16 | S2 | fs.read | `{"content": "budget shard metric update. budget shard update budget. The batch number is 1613.", "version": 3, "mtime": 1757021600}` | `{"content": "budget shard metric update. budget shard update budget. The batch number is 1.613.", "version": 3, "mtime": 1757021600}` |  |
| 17 | S3 | fs.list | `{"entries": [{"name": "archive_0.txt", "type": "file"}, {"name": "metric_1.txt", "type": "file"}, {"name": "release_3.txt", "type": "file"}, {"name": "system_2.` | `{"entries": [], "count": 0}` |  |
| 18 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/budget_3.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 2}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 19 | S4 | fs.stat | `{"exists": true, "size": 227, "version": 2, "mtime": 1757032400}` | `{"exists": true, "size": 215, "version": 1, "mtime": 1757032400}` |  |
| 20 | S1 | fs.read | `{"content": "release node system release pipeline status review. metric backlog status system draft. shard report shard system status backlog. The build number ` | `{"content": "config archive report pipeline draft. status node status report. budget latency draft deploy budget config system. deploy budget release draft clus` |  |
| 21 | S2 | fs.read | `{"content": "deploy cluster update backlog. latency metric system deploy metric config review sensor. draft latency report sensor metric backlog release node. d` | `{"content": "deploy cluster update backlog. latency metric system deploy metric config review sensor. draft latency report sensor metric backlog release node. d` |  |
| 22 | S3 | fs.list | `{"entries": [{"name": "budget_0.txt", "type": "file"}, {"name": "budget_3.txt", "type": "file"}, {"name": "latency_1.txt", "type": "file"}, {"name": "report_2.t` | `{"entries": [], "count": 0}` |  |
| 23 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 4}, {"path": "/data/report_2.txt", "count": 1}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 24 | S4 | fs.stat | `{"exists": true, "size": 191, "version": 2, "mtime": 1757000000}` | `{"exists": true, "size": 212, "version": 1, "mtime": 1757000000}` |  |
| 25 | S1 | fs.read | `{"content": "release pipeline cluster update sensor backlog draft. summary summary update release pipeline budget. metric status deploy archive budget. The batc` | `{"content": "backlog summary status node system release. config budget node latency. release shard latency sensor backlog node. The batch number is 4020.", "ver` |  |
| 26 | S2 | fs.read | `{"content": "status draft node draft node config. review backlog update draft shard. deploy sensor status review. report review node latency report sensor shard` | `{"content": "status draft node draft node config. review backlog update draft shard. deploy sensor status review. report review node latency report sensor shard` |  |
| 27 | S3 | fs.list | `{"entries": [{"name": "draft_3.txt", "type": "file"}, {"name": "metric_2.txt", "type": "file"}, {"name": "pointer_0.txt", "type": "file"}, {"name": "release_0.t` | `{"entries": [], "count": 0}` |  |
| 28 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 1}, {"path": "/data/report_2.txt", "count": 3}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 29 | S4 | fs.stat | `{"exists": true, "size": 165, "version": 2, "mtime": 1757046800}` | `{"exists": true, "size": 150, "version": 1, "mtime": 1757046800}` |  |
| 30 | S1 | fs.read | `{"content": "metric release summary update sensor. system draft draft pipeline backlog release config. summary system backlog pipeline cluster cluster. release ` | `{"content": "latency update budget sensor report config. review cluster budget deploy draft status. shard backlog release archive. The build number is 320.", "v` |  |
| 31 | S2 | fs.read | `{"content": "metric node budget report archive backlog. sensor node sensor report metric. sensor summary budget pipeline update. latency sensor archive pipeline` | `{"content": "metric node budget report archive backlog. sensor node sensor report metric. sensor summary budget pipeline update. latency sensor archive pipeline` |  |
| 32 | S3 | fs.list | `{"entries": [{"name": "draft_3.txt", "type": "file"}, {"name": "pipeline_2.txt", "type": "file"}, {"name": "release_1.txt", "type": "file"}, {"name": "sensor_0.` | `{"entries": [], "count": 0}` |  |
| 33 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/budget_3.txt", "count": 1}, {"path": "/data/report_2.txt", "count": 1}, {"path": "/docs` | `{"matches": [], "total": 0}` |  |
| 34 | S4 | fs.stat | `{"exists": true, "size": 175, "version": 3, "mtime": 1757028800}` | `{"exists": true, "size": 190, "version": 2, "mtime": 1757028800}` |  |
| 35 | S1 | fs.read | `{"content": "deploy review update sensor shard archive status archive. config status deploy report update. pipeline cluster status config config pipeline. revie` | `{"content": "shard summary release budget budget node summary release. config node backlog archive latency. config review summary node config status metric. The` |  |
| 36 | S2 | fs.read | `{"content": "status cluster pipeline node deploy metric backlog config. node cluster pipeline system latency shard draft. latency metric deploy pipeline. releas` | `{"content": "status cluster pipeline node deploy metric backlog config. node cluster pipeline system latency shard draft. latency metric deploy pipeline. releas` |  |
| 37 | S3 | fs.list | `{"entries": [{"name": "archive_0.txt", "type": "file"}, {"name": "metric_1.txt", "type": "file"}, {"name": "release_3.txt", "type": "file"}, {"name": "system_2.` | `{"entries": [], "count": 0}` |  |
| 38 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/budget_3.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 2}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 39 | S4 | fs.stat | `{"exists": true, "size": 127, "version": 3, "mtime": 1757007200}` | `{"exists": true, "size": 137, "version": 2, "mtime": 1757007200}` |  |
| 40 | S1 | fs.read | `{"content": "system backlog update config status update pipeline. update node review draft draft update release. The build number is 5198.", "version": 2, "mtim` | `{"content": "deploy status cluster report system draft summary node. config cluster sensor node summary deploy node. system archive review deploy. deploy system` |  |
| 41 | S2 | fs.read | `{"content": "sensor review system pipeline draft metric node. summary update status config review config budget metric. status update node latency summary archi` | `{"content": "sensor review system pipeline draft metric node. summary update status config review config budget metric. status update node latency summary archi` |  |
| 42 | S3 | fs.list | `{"entries": [{"name": "budget_0.txt", "type": "file"}, {"name": "budget_3.txt", "type": "file"}, {"name": "latency_1.txt", "type": "file"}, {"name": "report_2.t` | `{"entries": [], "count": 0}` |  |
| 43 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 4}, {"path": "/data/report_2.txt", "count": 1}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 44 | S4 | fs.stat | `{"exists": true, "size": 57, "version": 2, "mtime": 1757100000}` | `{"exists": true, "size": 51, "version": 1, "mtime": 1757100000}` |  |
| 45 | S1 | fs.read | `{"content": "config metric latency metric budget pipeline sensor. cluster shard shard cluster shard budget system cluster. backlog review release cluster metric` | `{"content": "sensor cluster status backlog update backlog. config node budget summary. The ticket number is 1119.", "version": 1, "mtime": 1757043200}` |  |
| 46 | S2 | fs.read | `{"content": "sensor backlog shard metric review system status. report system cluster summary. summary draft draft pipeline budget cluster review review. The bat` | `{"content": "sensor backlog shard metric review system status. report system cluster summary. summary draft draft pipeline budget cluster review review. The bat` |  |
| 47 | S3 | fs.list | `{"entries": [{"name": "draft_3.txt", "type": "file"}, {"name": "metric_2.txt", "type": "file"}, {"name": "pointer_0.txt", "type": "file"}, {"name": "release_0.t` | `{"entries": [], "count": 0}` |  |
| 48 | S3 | fs.search | `{"matches": [{"path": "/data/budget_0.txt", "count": 2}, {"path": "/data/latency_1.txt", "count": 1}, {"path": "/data/report_2.txt", "count": 3}, {"path": "/doc` | `{"matches": [], "total": 0}` |  |
| 49 | S4 | fs.stat | `{"exists": true, "size": 200, "version": 2, "mtime": 1757025200}` | `{"exists": true, "size": 211, "version": 1, "mtime": 1757025200}` |  |

## http (50 samples)

| # | family | tool | nominal | mutated | verdict |
|---|--------|------|---------|---------|---------|
| 0 | S1 | http.fetch | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": 3896, "score": 3.74}}` | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": 1804, "score": 8.81}}` |  |
| 1 | S2 | http.fetch | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": 1386, "score": 4.46}}` | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": "1,386", "score": "4.46"}}` |  |
| 2 | S3 | http.fetch | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": 2691, "score": 2.0}}` | `{"status": 200, "body": {}}` |  |
| 3 | S4 | http.head | `{"status": 200, "content_length": 156}` | `{"status": 200, "content_length": 143}` |  |
| 4 | S1 | http.fetch | `{"status": 200, "body": "config pipeline review update summary latency pipeline config. sensor update review latency. draft budget metric node shard. Visitors t` | `{"status": 200, "body": "review pipeline review system cluster. node report shard node config pipeline deploy. cluster metric pipeline pipeline sensor review st` |  |
| 5 | S2 | http.fetch | `{"status": 200, "body": "update sensor status backlog budget budget summary status. deploy budget config deploy. sensor summary config archive latency summary l` | `{"status": 200, "body": "update sensor status backlog budget budget summary status. deploy budget config deploy. sensor summary config archive latency summary l` |  |
| 6 | S3 | http.fetch | `{"status": 200, "body": "budget budget latency config update backlog summary. latency deploy summary system report review pipeline. summary deploy report report` | `{"status": 200, "body": ""}` |  |
| 7 | S4 | http.head | `{"status": 200, "content_length": 57}` | `{"status": 200, "content_length": 52}` |  |
| 8 | S1 | http.fetch | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": 2691, "score": 2.0}}` | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": 2105, "score": 6.43}}` |  |
| 9 | S2 | http.fetch | `{"status": 200, "body": {"id": 3, "name": "unit_3", "count": 2760, "score": 5.02}}` | `{"status": 200, "body": {"id": 3, "name": "unit_3", "count": "2,760", "score": "5.02"}}` |  |
| 10 | S3 | http.fetch | `{"status": 200, "body": ["api.local/items/0", "api.local/items/1", "api.local/items/2", "api.local/items/3", "news.local/article-0", "news.local/article-1", "ne` | `{"status": 200, "body": []}` |  |
| 11 | S4 | http.head | `{"status": 200, "content_length": 164}` | `{"status": 200, "content_length": 175}` |  |
| 12 | S1 | http.fetch | `{"status": 200, "body": "budget budget latency config update backlog summary. latency deploy summary system report review pipeline. summary deploy report report` | `{"status": 200, "body": "report node pipeline system budget latency. sensor latency budget release shard. release report release report report sensor report. Vi` |  |
| 13 | S2 | http.fetch | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": 3896, "score": 3.74}}` | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": "3,896", "score": "3.74"}}` |  |
| 14 | S3 | http.fetch | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": 1386, "score": 4.46}}` | `{"status": 200, "body": {}}` |  |
| 15 | S4 | http.head | `{"status": 200, "content_length": 57}` | `{"status": 200, "content_length": 64}` |  |
| 16 | S1 | http.fetch | `{"status": 200, "body": ["api.local/items/0", "api.local/items/1", "api.local/items/2", "api.local/items/3", "news.local/article-0", "news.local/article-1", "ne` | `{"status": 200, "body": ["api.local/items/0", "api.local/items/1", "api.local/items/2", "api.local/items/3", "news.local/article-0", "news.local/article-1"]}` |  |
| 17 | S2 | http.fetch | `{"status": 200, "body": "config pipeline review update summary latency pipeline config. sensor update review latency. draft budget metric node shard. Visitors t` | `{"status": 200, "body": "config pipeline review update summary latency pipeline config. sensor update review latency. draft budget metric node shard. Visitors t` |  |
| 18 | S3 | http.fetch | `{"status": 200, "body": "update sensor status backlog budget budget summary status. deploy budget config deploy. sensor summary config archive latency summary l` | `{"status": 200, "body": ""}` |  |
| 19 | S4 | http.head | `{"status": 200, "content_length": 57}` | `{"status": 200, "content_length": 50}` |  |
| 20 | S1 | http.fetch | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": 1386, "score": 4.46}}` | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": 2923, "score": 8.44}}` |  |
| 21 | S2 | http.fetch | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": 2691, "score": 2.0}}` | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": "2,691", "score": "2.0"}}` |  |
| 22 | S3 | http.fetch | `{"status": 200, "body": {"id": 3, "name": "unit_3", "count": 2760, "score": 5.02}}` | `{"status": 200, "body": {}}` |  |
| 23 | S3 | http.links | `{"links": ["api.local/items/0", "api.local/items/1", "api.local/items/2", "api.local/items/3", "index.local/", "news.local/article-0", "news.local/article-1", "` | `{"links": [], "count": 0}` |  |
| 24 | S4 | http.head | `{"status": 200, "content_length": 146}` | `{"status": 200, "content_length": 138}` |  |
| 25 | S1 | http.fetch | `{"status": 200, "body": "update sensor status backlog budget budget summary status. deploy budget config deploy. sensor summary config archive latency summary l` | `{"status": 200, "body": "draft report backlog report. report pipeline pipeline sensor cluster archive budget. draft node review summary review summary config. V` |  |
| 26 | S2 | http.fetch | `{"status": 200, "body": "budget budget latency config update backlog summary. latency deploy summary system report review pipeline. summary deploy report report` | `{"status": 200, "body": "budget budget latency config update backlog summary. latency deploy summary system report review pipeline. summary deploy report report` |  |
| 27 | S3 | http.fetch | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": 3896, "score": 3.74}}` | `{"status": 200, "body": {}}` |  |
| 28 | S4 | http.head | `{"status": 200, "content_length": 56}` | `{"status": 200, "content_length": 54}` |  |
| 29 | S1 | http.fetch | `{"status": 200, "body": {"id": 3, "name": "unit_3", "count": 2760, "score": 5.02}}` | `{"status": 200, "body": {"id": 3, "name": "unit_3", "count": 2679, "score": 4.45}}` |  |
| 30 | S3 | http.fetch | `{"status": 200, "body": "config pipeline review update summary latency pipeline config. sensor update review latency. draft budget metric node shard. Visitors t` | `{"status": 200, "body": ""}` |  |
| 31 | S4 | http.head | `{"status": 200, "content_length": 178}` | `{"status": 200, "content_length": 184}` |  |
| 32 | S1 | http.fetch | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": 3896, "score": 3.74}}` | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": 1804, "score": 8.81}}` |  |
| 33 | S2 | http.fetch | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": 1386, "score": 4.46}}` | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": "1,386", "score": "4.46"}}` |  |
| 34 | S3 | http.fetch | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": 2691, "score": 2.0}}` | `{"status": 200, "body": {}}` |  |
| 35 | S4 | http.head | `{"status": 200, "content_length": 156}` | `{"status": 200, "content_length": 164}` |  |
| 36 | S1 | http.fetch | `{"status": 200, "body": "config pipeline review update summary latency pipeline config. sensor update review latency. draft budget metric node shard. Visitors t` | `{"status": 200, "body": "review pipeline review system cluster. node report shard node config pipeline deploy. cluster metric pipeline pipeline sensor review st` |  |
| 37 | S2 | http.fetch | `{"status": 200, "body": "update sensor status backlog budget budget summary status. deploy budget config deploy. sensor summary config archive latency summary l` | `{"status": 200, "body": "update sensor status backlog budget budget summary status. deploy budget config deploy. sensor summary config archive latency summary l` |  |
| 38 | S3 | http.fetch | `{"status": 200, "body": "budget budget latency config update backlog summary. latency deploy summary system report review pipeline. summary deploy report report` | `{"status": 200, "body": ""}` |  |
| 39 | S4 | http.head | `{"status": 200, "content_length": 57}` | `{"status": 200, "content_length": 54}` |  |
| 40 | S1 | http.fetch | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": 2691, "score": 2.0}}` | `{"status": 200, "body": {"id": 2, "name": "unit_2", "count": 2105, "score": 6.43}}` |  |
| 41 | S2 | http.fetch | `{"status": 200, "body": {"id": 3, "name": "unit_3", "count": 2760, "score": 5.02}}` | `{"status": 200, "body": {"id": 3, "name": "unit_3", "count": "2,760", "score": "5.02"}}` |  |
| 42 | S3 | http.fetch | `{"status": 200, "body": ["api.local/items/0", "api.local/items/1", "api.local/items/2", "api.local/items/3", "news.local/article-0", "news.local/article-1", "ne` | `{"status": 200, "body": []}` |  |
| 43 | S4 | http.head | `{"status": 200, "content_length": 164}` | `{"status": 200, "content_length": 182}` |  |
| 44 | S1 | http.fetch | `{"status": 200, "body": "budget budget latency config update backlog summary. latency deploy summary system report review pipeline. summary deploy report report` | `{"status": 200, "body": "report node pipeline system budget latency. sensor latency budget release shard. release report release report report sensor report. Vi` |  |
| 45 | S2 | http.fetch | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": 3896, "score": 3.74}}` | `{"status": 200, "body": {"id": 0, "name": "unit_0", "count": "3,896", "score": "3.74"}}` |  |
| 46 | S3 | http.fetch | `{"status": 200, "body": {"id": 1, "name": "unit_1", "count": 1386, "score": 4.46}}` | `{"status": 200, "body": {}}` |  |
| 47 | S4 | http.head | `{"status": 200, "content_length": 57}` | `{"status": 200, "content_length": 54}` |  |
| 48 | S1 | http.fetch | `{"status": 200, "body": ["api.local/items/0", "api.local/items/1", "api.local/items/2", "api.local/items/3", "news.local/article-0", "news.local/article-1", "ne` | `{"status": 200, "body": ["api.local/items/0", "api.local/items/1", "api.local/items/2", "api.local/items/3", "news.local/article-0", "news.local/article-1"]}` |  |
| 49 | S2 | http.fetch | `{"status": 200, "body": "config pipeline review update summary latency pipeline config. sensor update review latency. draft budget metric node shard. Visitors t` | `{"status": 200, "body": "config pipeline review update summary latency pipeline config. sensor update review latency. draft budget metric node shard. Visitors t` |  |

## kv (50 samples)

| # | family | tool | nominal | mutated | verdict |
|---|--------|------|---------|---------|---------|
| 0 | S1 | kv.get | `{"value": 3121, "version": 2}` | `{"value": 3120, "version": 1}` |  |
| 1 | S2 | kv.get | `{"value": 2743, "version": 2}` | `{"value": "2,743", "version": 2}` |  |
| 2 | S2 | kv.getv | `{"value": 4988, "version": 3}` | `{"value": "4,988", "version": 3}` |  |
| 3 | S3 | kv.scan | `{"keys": ["cache:cluster_0", "cache:deploy_1", "cache:draft_2"], "count": 3}` | `{"keys": [], "count": 0}` |  |
| 4 | S4 | kv.get | `{"value": 2353, "version": 2}` | `{"value": 2553, "version": 2}` |  |
| 5 | S4 | kv.getv | `{"value": 1461, "version": 2}` | `{"value": 1629, "version": 2}` |  |
| 6 | S1 | kv.get | `{"value": 2933, "version": 2}` | `{"value": 2924, "version": 1}` |  |
| 7 | S2 | kv.get | `{"value": 3970, "version": 2}` | `{"value": "3,970", "version": 2}` |  |
| 8 | S2 | kv.getv | `{"value": 3724, "version": 1}` | `{"value": "3,724", "version": 1}` |  |
| 9 | S3 | kv.scan | `{"keys": ["user:archive_3", "user:deploy_0", "user:deploy_1", "user:status_2"], "count": 4}` | `{"keys": [], "count": 0}` |  |
| 10 | S4 | kv.get | `{"value": 2506, "version": 3}` | `{"value": 2422, "version": 3}` |  |
| 11 | S4 | kv.getv | `{"value": {"name": "user_3", "quota": 1295}, "version": 3}` | `{"value": {"name": "user_3", "quota": 1389}, "version": 3}` |  |
| 12 | S1 | kv.get | `{"value": {"name": "user_0", "quota": 4552}, "version": 2}` | `{"value": {"name": "user_0", "quota": 4550}, "version": 1}` |  |
| 13 | S2 | kv.get | `{"value": {"name": "user_1", "quota": 909}, "version": 4}` | `{"value": {"name": "user_1", "quota": "909"}, "version": 4}` |  |
| 14 | S2 | kv.getv | `{"value": {"name": "user_2", "quota": 1938}, "version": 3}` | `{"value": {"name": "user_2", "quota": "1,938"}, "version": 3}` |  |
| 15 | S3 | kv.scan | `{"keys": ["cache:cluster_0", "cache:deploy_1", "cache:draft_2"], "count": 3}` | `{"keys": [], "count": 0}` |  |
| 16 | S4 | kv.get | `{"value": 2743, "version": 2}` | `{"value": 2963, "version": 2}` |  |
| 17 | S4 | kv.getv | `{"value": 4989, "version": 2}` | `{"value": 5556, "version": 2}` |  |
| 18 | S1 | kv.get | `{"value": 266, "version": 3}` | `{"value": 262, "version": 1}` |  |
| 19 | S2 | kv.get | `{"value": 2353, "version": 2}` | `{"value": "2,353", "version": 2}` |  |
| 20 | S2 | kv.getv | `{"value": 1454, "version": 1}` | `{"value": "1,454", "version": 1}` |  |
| 21 | S3 | kv.scan | `{"keys": ["user:archive_3", "user:deploy_0", "user:deploy_1", "user:status_2"], "count": 4}` | `{"keys": [], "count": 0}` |  |
| 22 | S4 | kv.get | `{"value": 3970, "version": 2}` | `{"value": 4224, "version": 2}` |  |
| 23 | S4 | kv.getv | `{"value": 3745, "version": 4}` | `{"value": 3500, "version": 4}` |  |
| 24 | S1 | kv.get | `{"value": 1814, "version": 3}` | `{"value": 1804, "version": 1}` |  |
| 25 | S2 | kv.get | `{"value": 2506, "version": 3}` | `{"value": "2,506", "version": 3}` |  |
| 26 | S2 | kv.getv | `{"value": {"name": "user_3", "quota": 1295}, "version": 3}` | `{"value": {"name": "user_3", "quota": "1,295"}, "version": 3}` |  |
| 27 | S3 | kv.scan | `{"keys": ["cache:cluster_0", "cache:deploy_1", "cache:draft_2"], "count": 3}` | `{"keys": [], "count": 0}` |  |
| 28 | S4 | kv.get | `{"value": {"name": "user_1", "quota": 909}, "version": 4}` | `{"value": {"name": "user_1", "quota": 965}, "version": 4}` |  |
| 29 | S4 | kv.getv | `{"value": {"name": "user_2", "quota": 1938}, "version": 3}` | `{"value": {"name": "user_2", "quota": 1784}, "version": 3}` |  |
| 30 | S1 | kv.get | `{"value": 3121, "version": 2}` | `{"value": 3120, "version": 1}` |  |
| 31 | S2 | kv.get | `{"value": 2743, "version": 2}` | `{"value": "2,743", "version": 2}` |  |
| 32 | S2 | kv.getv | `{"value": 4984, "version": 1}` | `{"value": "4,984", "version": 1}` |  |
| 33 | S3 | kv.scan | `{"keys": ["user:archive_3", "user:deploy_0", "user:deploy_1", "user:status_2"], "count": 4}` | `{"keys": [], "count": 0}` |  |
| 34 | S4 | kv.get | `{"value": 2353, "version": 2}` | `{"value": 2251, "version": 2}` |  |
| 35 | S4 | kv.getv | `{"value": 1463, "version": 4}` | `{"value": 1357, "version": 4}` |  |
| 36 | S1 | kv.get | `{"value": 2933, "version": 2}` | `{"value": 2924, "version": 1}` |  |
| 37 | S2 | kv.get | `{"value": 3970, "version": 2}` | `{"value": "3,970", "version": 2}` |  |
| 38 | S2 | kv.getv | `{"value": 3736, "version": 3}` | `{"value": "3,736", "version": 3}` |  |
| 39 | S3 | kv.scan | `{"keys": ["cache:cluster_0", "cache:deploy_1", "cache:draft_2"], "count": 3}` | `{"keys": [], "count": 0}` |  |
| 40 | S4 | kv.get | `{"value": 2506, "version": 3}` | `{"value": 2364, "version": 3}` |  |
| 41 | S4 | kv.getv | `{"value": {"name": "user_3", "quota": 1295}, "version": 3}` | `{"value": {"name": "user_3", "quota": 1394}, "version": 3}` |  |
| 42 | S1 | kv.get | `{"value": {"name": "user_0", "quota": 4552}, "version": 2}` | `{"value": {"name": "user_0", "quota": 4550}, "version": 1}` |  |
| 43 | S2 | kv.get | `{"value": {"name": "user_1", "quota": 909}, "version": 4}` | `{"value": {"name": "user_1", "quota": "909"}, "version": 4}` |  |
| 44 | S2 | kv.getv | `{"value": {"name": "user_2", "quota": 1938}, "version": 3}` | `{"value": {"name": "user_2", "quota": "1,938"}, "version": 3}` |  |
| 45 | S3 | kv.scan | `{"keys": ["user:archive_3", "user:deploy_0", "user:deploy_1", "user:status_2"], "count": 4}` | `{"keys": [], "count": 0}` |  |
| 46 | S4 | kv.get | `{"value": 2743, "version": 2}` | `{"value": 2528, "version": 2}` |  |
| 47 | S4 | kv.getv | `{"value": 4996, "version": 4}` | `{"value": 4527, "version": 4}` |  |
| 48 | S1 | kv.get | `{"value": 266, "version": 3}` | `{"value": 262, "version": 1}` |  |
| 49 | S2 | kv.get | `{"value": 2353, "version": 2}` | `{"value": "2,353", "version": 2}` |  |

## sensor (50 samples)

| # | family | tool | nominal | mutated | verdict |
|---|--------|------|---------|---------|---------|
| 0 | S1 | sensor.read | `{"value": 16.41, "unit": "C", "ts": 1757036900}` | `{"value": 13.7, "unit": "C", "ts": 1757036900}` |  |
| 1 | S2 | sensor.history | `{"readings": [{"value": 32.11, "ts": 1757036000}, {"value": 33.84, "ts": 1757036300}, {"value": 41.19, "ts": 1757036600}, {"value": 34.5, "ts": 1757036900}], "u` | `{"readings": [{"value": 0.3211, "ts": 1757036000}, {"value": 0.3384, "ts": 1757036300}, {"value": 0.4119, "ts": 1757036600}, {"value": 0.345, "ts": 1757036900}]` |  |
| 2 | S2 | sensor.read | `{"value": 1007.72, "unit": "hPa", "ts": 1757036900}` | `{"value": 100.77, "unit": "hPa", "ts": 1757036900}` |  |
| 3 | S3 | sensor.history | `{"readings": [{"value": 390.34, "ts": 1757036000}, {"value": 290.07, "ts": 1757036300}, {"value": 302.67, "ts": 1757036600}, {"value": 391.61, "ts": 1757036900}` | `{"readings": [], "unit": "lux", "count": 0}` |  |
| 4 | S4 | sensor.read | `{"value": 17.5, "unit": "C", "ts": 1757036900}` | `{"value": 12.34, "unit": "C", "ts": 1757036900}` |  |
| 5 | S1 | sensor.read | `{"value": 57.71, "unit": "%", "ts": 1757036900}` | `{"value": 57.69, "unit": "%", "ts": 1757036900}` |  |
| 6 | S2 | sensor.history | `{"readings": [{"value": 16.41, "ts": 1757036000}, {"value": 20.96, "ts": 1757036300}, {"value": 21.42, "ts": 1757036600}, {"value": 16.41, "ts": 1757036900}], "` | `{"readings": [{"value": 61.54, "ts": 1757036000}, {"value": 69.73, "ts": 1757036300}, {"value": 70.56, "ts": 1757036600}, {"value": 61.54, "ts": 1757036900}], "` |  |
| 7 | S2 | sensor.read | `{"value": 34.5, "unit": "%", "ts": 1757036900}` | `{"value": 0.345, "unit": "%", "ts": 1757036900}` |  |
| 8 | S3 | sensor.history | `{"readings": [{"value": 1020.64, "ts": 1757036000}, {"value": 1018.99, "ts": 1757036300}, {"value": 1009.2, "ts": 1757036600}, {"value": 1007.72, "ts": 17570369` | `{"readings": [], "unit": "hPa", "count": 0}` |  |
| 9 | S4 | sensor.read | `{"value": 391.61, "unit": "lux", "ts": 1757036900}` | `{"value": 302.08, "unit": "lux", "ts": 1757036900}` |  |
| 10 | S1 | sensor.read | `{"value": 17.5, "unit": "C", "ts": 1757036900}` | `{"value": 20.24, "unit": "C", "ts": 1757036900}` |  |
| 11 | S2 | sensor.history | `{"readings": [{"value": 34.32, "ts": 1757036000}, {"value": 43.5, "ts": 1757036300}, {"value": 38.43, "ts": 1757036600}, {"value": 57.71, "ts": 1757036900}], "u` | `{"readings": [{"value": 0.3432, "ts": 1757036000}, {"value": 0.435, "ts": 1757036300}, {"value": 0.3843, "ts": 1757036600}, {"value": 0.5771, "ts": 1757036900}]` |  |
| 12 | S2 | sensor.read | `{"value": 16.41, "unit": "C", "ts": 1757036900}` | `{"value": 61.54, "unit": "C", "ts": 1757036900}` |  |
| 13 | S3 | sensor.history | `{"readings": [{"value": 32.11, "ts": 1757036000}, {"value": 33.84, "ts": 1757036300}, {"value": 41.19, "ts": 1757036600}, {"value": 34.5, "ts": 1757036900}], "u` | `{"readings": [], "unit": "%", "count": 0}` |  |
| 14 | S4 | sensor.read | `{"value": 1007.72, "unit": "hPa", "ts": 1757036900}` | `{"value": 1012.13, "unit": "hPa", "ts": 1757036900}` |  |
| 15 | S1 | sensor.read | `{"value": 391.61, "unit": "lux", "ts": 1757036900}` | `{"value": 291.42, "unit": "lux", "ts": 1757036900}` |  |
| 16 | S2 | sensor.history | `{"readings": [{"value": 15.92, "ts": 1757036000}, {"value": 21.9, "ts": 1757036300}, {"value": 14.7, "ts": 1757036600}, {"value": 17.5, "ts": 1757036900}], "uni` | `{"readings": [{"value": 60.66, "ts": 1757036000}, {"value": 71.42, "ts": 1757036300}, {"value": 58.46, "ts": 1757036600}, {"value": 63.5, "ts": 1757036900}], "u` |  |
| 17 | S2 | sensor.read | `{"value": 57.71, "unit": "%", "ts": 1757036900}` | `{"value": 0.5771, "unit": "%", "ts": 1757036900}` |  |
| 18 | S3 | sensor.history | `{"readings": [{"value": 16.41, "ts": 1757036000}, {"value": 20.96, "ts": 1757036300}, {"value": 21.42, "ts": 1757036600}, {"value": 16.41, "ts": 1757036900}], "` | `{"readings": [], "unit": "C", "count": 0}` |  |
| 19 | S4 | sensor.read | `{"value": 34.5, "unit": "%", "ts": 1757036900}` | `{"value": 46.74, "unit": "%", "ts": 1757036900}` |  |
| 20 | S1 | sensor.read | `{"value": 1007.72, "unit": "hPa", "ts": 1757036900}` | `{"value": 1018.99, "unit": "hPa", "ts": 1757036900}` |  |
| 21 | S2 | sensor.history | `{"readings": [{"value": 390.34, "ts": 1757036000}, {"value": 290.07, "ts": 1757036300}, {"value": 302.67, "ts": 1757036600}, {"value": 391.61, "ts": 1757036900}` | `{"readings": [{"value": 0.3903, "ts": 1757036000}, {"value": 0.2901, "ts": 1757036300}, {"value": 0.3027, "ts": 1757036600}, {"value": 0.3916, "ts": 1757036900}` |  |
| 22 | S2 | sensor.read | `{"value": 17.5, "unit": "C", "ts": 1757036900}` | `{"value": 63.5, "unit": "C", "ts": 1757036900}` |  |
| 23 | S3 | sensor.history | `{"readings": [{"value": 34.32, "ts": 1757036000}, {"value": 43.5, "ts": 1757036300}, {"value": 38.43, "ts": 1757036600}, {"value": 57.71, "ts": 1757036900}], "u` | `{"readings": [], "unit": "%", "count": 0}` |  |
| 24 | S4 | sensor.read | `{"value": 16.41, "unit": "C", "ts": 1757036900}` | `{"value": 13.02, "unit": "C", "ts": 1757036900}` |  |
| 25 | S1 | sensor.read | `{"value": 34.5, "unit": "%", "ts": 1757036900}` | `{"value": 46.57, "unit": "%", "ts": 1757036900}` |  |
| 26 | S2 | sensor.history | `{"readings": [{"value": 1020.64, "ts": 1757036000}, {"value": 1018.99, "ts": 1757036300}, {"value": 1009.2, "ts": 1757036600}, {"value": 1007.72, "ts": 17570369` | `{"readings": [{"value": 102.06, "ts": 1757036000}, {"value": 101.9, "ts": 1757036300}, {"value": 100.92, "ts": 1757036600}, {"value": 100.77, "ts": 1757036900}]` |  |
| 27 | S2 | sensor.read | `{"value": 391.61, "unit": "lux", "ts": 1757036900}` | `{"value": 0.3916, "unit": "lux", "ts": 1757036900}` |  |
| 28 | S3 | sensor.history | `{"readings": [{"value": 15.92, "ts": 1757036000}, {"value": 21.9, "ts": 1757036300}, {"value": 14.7, "ts": 1757036600}, {"value": 17.5, "ts": 1757036900}], "uni` | `{"readings": [], "unit": "C", "count": 0}` |  |
| 29 | S4 | sensor.read | `{"value": 57.71, "unit": "%", "ts": 1757036900}` | `{"value": 51.25, "unit": "%", "ts": 1757036900}` |  |
| 30 | S1 | sensor.read | `{"value": 16.41, "unit": "C", "ts": 1757036900}` | `{"value": 12.21, "unit": "C", "ts": 1757036900}` |  |
| 31 | S2 | sensor.history | `{"readings": [{"value": 32.11, "ts": 1757036000}, {"value": 33.84, "ts": 1757036300}, {"value": 41.19, "ts": 1757036600}, {"value": 34.5, "ts": 1757036900}], "u` | `{"readings": [{"value": 0.3211, "ts": 1757036000}, {"value": 0.3384, "ts": 1757036300}, {"value": 0.4119, "ts": 1757036600}, {"value": 0.345, "ts": 1757036900}]` |  |
| 32 | S2 | sensor.read | `{"value": 1007.72, "unit": "hPa", "ts": 1757036900}` | `{"value": 100.77, "unit": "hPa", "ts": 1757036900}` |  |
| 33 | S3 | sensor.history | `{"readings": [{"value": 390.34, "ts": 1757036000}, {"value": 290.07, "ts": 1757036300}, {"value": 302.67, "ts": 1757036600}, {"value": 391.61, "ts": 1757036900}` | `{"readings": [], "unit": "lux", "count": 0}` |  |
| 34 | S4 | sensor.read | `{"value": 17.5, "unit": "C", "ts": 1757036900}` | `{"value": 13.18, "unit": "C", "ts": 1757036900}` |  |
| 35 | S1 | sensor.read | `{"value": 57.71, "unit": "%", "ts": 1757036900}` | `{"value": 43.75, "unit": "%", "ts": 1757036900}` |  |
| 36 | S2 | sensor.history | `{"readings": [{"value": 16.41, "ts": 1757036000}, {"value": 20.96, "ts": 1757036300}, {"value": 21.42, "ts": 1757036600}, {"value": 16.41, "ts": 1757036900}], "` | `{"readings": [{"value": 61.54, "ts": 1757036000}, {"value": 69.73, "ts": 1757036300}, {"value": 70.56, "ts": 1757036600}, {"value": 61.54, "ts": 1757036900}], "` |  |
| 37 | S2 | sensor.read | `{"value": 34.5, "unit": "%", "ts": 1757036900}` | `{"value": 0.345, "unit": "%", "ts": 1757036900}` |  |
| 38 | S3 | sensor.history | `{"readings": [{"value": 1020.64, "ts": 1757036000}, {"value": 1018.99, "ts": 1757036300}, {"value": 1009.2, "ts": 1757036600}, {"value": 1007.72, "ts": 17570369` | `{"readings": [], "unit": "hPa", "count": 0}` |  |
| 39 | S4 | sensor.read | `{"value": 391.61, "unit": "lux", "ts": 1757036900}` | `{"value": 324.52, "unit": "lux", "ts": 1757036900}` |  |
| 40 | S1 | sensor.read | `{"value": 17.5, "unit": "C", "ts": 1757036900}` | `{"value": 15.92, "unit": "C", "ts": 1757036900}` |  |
| 41 | S2 | sensor.history | `{"readings": [{"value": 34.32, "ts": 1757036000}, {"value": 43.5, "ts": 1757036300}, {"value": 38.43, "ts": 1757036600}, {"value": 57.71, "ts": 1757036900}], "u` | `{"readings": [{"value": 0.3432, "ts": 1757036000}, {"value": 0.435, "ts": 1757036300}, {"value": 0.3843, "ts": 1757036600}, {"value": 0.5771, "ts": 1757036900}]` |  |
| 42 | S2 | sensor.read | `{"value": 16.41, "unit": "C", "ts": 1757036900}` | `{"value": 61.54, "unit": "C", "ts": 1757036900}` |  |
| 43 | S3 | sensor.history | `{"readings": [{"value": 32.11, "ts": 1757036000}, {"value": 33.84, "ts": 1757036300}, {"value": 41.19, "ts": 1757036600}, {"value": 34.5, "ts": 1757036900}], "u` | `{"readings": [], "unit": "%", "count": 0}` |  |
| 44 | S4 | sensor.read | `{"value": 1007.72, "unit": "hPa", "ts": 1757036900}` | `{"value": 1011.4, "unit": "hPa", "ts": 1757036900}` |  |
| 45 | S1 | sensor.read | `{"value": 391.61, "unit": "lux", "ts": 1757036900}` | `{"value": 302.67, "unit": "lux", "ts": 1757036900}` |  |
| 46 | S2 | sensor.history | `{"readings": [{"value": 15.92, "ts": 1757036000}, {"value": 21.9, "ts": 1757036300}, {"value": 14.7, "ts": 1757036600}, {"value": 17.5, "ts": 1757036900}], "uni` | `{"readings": [{"value": 60.66, "ts": 1757036000}, {"value": 71.42, "ts": 1757036300}, {"value": 58.46, "ts": 1757036600}, {"value": 63.5, "ts": 1757036900}], "u` |  |
| 47 | S2 | sensor.read | `{"value": 57.71, "unit": "%", "ts": 1757036900}` | `{"value": 0.5771, "unit": "%", "ts": 1757036900}` |  |
| 48 | S3 | sensor.history | `{"readings": [{"value": 16.41, "ts": 1757036000}, {"value": 20.96, "ts": 1757036300}, {"value": 21.42, "ts": 1757036600}, {"value": 16.41, "ts": 1757036900}], "` | `{"readings": [], "unit": "C", "count": 0}` |  |
| 49 | S4 | sensor.read | `{"value": 34.5, "unit": "%", "ts": 1757036900}` | `{"value": 44.81, "unit": "%", "ts": 1757036900}` |  |