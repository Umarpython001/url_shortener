# URL Shortener — Iteration 1 Architecture Analysis

## Current Tech Stack

- Backend Framework: FastAPI (Python)
- Database: SQLite
- ORM: SQLAlchemy

## Core System Functionality

**1. Write Path (URL Shortening):**
Users submit a long URL via an endpoint, and the system generates and stores a corresponding short URL in the SQLite database.

**2. Read Path (Redirection):**
Users hit a short URL endpoint, and the system queries the database to look up the original long URL, returning an HTTP 307/302 Redirect.

## Concurrency & Performance Bottlenecks

### 1. Write Bottleneck: Database Locking & Queue Delays:
Under default settings, SQLite enforces file-level database locking during write operations. SQLAlchemy serializes incoming write operations, executing them sequentially one by one.

### The Issue with High Write Concurrency (e.g., 500 Concurrent Writes)

- Sequential Queueing: When 500 concurrent shortening requests hit the application, SQLite handles them sequentially rather than in parallel.

- Busy Timeout Expiration: Each pending write request waits in a queue for the preceding database locks to release. Each request operates under a execution timeout threshold.

- Error Cascade: As queue latency increases, requests towards the back of the queue exceed their timeout limit. SQLite raises an OperationalError: database is locked, returning 500 Internal Server Error responses to clients.

### 2. Read Bottleneck: Read Starvation During Heavy Write Traffic
In default SQLite rollback-journal mode, a write operation locks the entire database file.

- Exclusive Locks: While a write is executing, read access to the database is completely blocked.

- Read Delays: If 500 write operations arrive simultaneously, incoming redirection (read) requests must wait until the write lock queue clears.

- Degraded User Experience: Users trying to access existing short links experience increased latency or time out entirely while waiting for pending write operations to complete.


## Key Takeaways for Future Iterations

### 1. Short-Term Mitigations (SQLite):

- Enable Write-Ahead Logging (PRAGMA journal_mode=WAL;) to allow concurrent reads while a write takes place.

- Adjust database busy timeout settings (PRAGMA busy_timeout = 30000;).

### 2. Long-Term Architectural Solutions:

- Database Upgrade: Migrate to a client-server RDBMS like PostgreSQL to support row-level locking and concurrent write operations.

- Caching Strategy: Implement an in-memory caching layer (e.g., Redis) for the read path to serve redirects without touching the primary database.

- Asynchronous Ingestion: Use a message queue (e.g., Redis/Celery) to decouple API write requests from database persistence under high load.

---

# Added After Load Testing

## Test Setup

Locust ran on the same machine as the FastAPI server (http://localhost:8000), so the load generator and the app shared CPU. Machine specs and the uvicorn worker count were not recorded, and should be added here because every number below depends on them.

Each simulated user creates 5 short URLs when it starts, then loops: 95% redirects (GET /shortener/{code}) and 5% creates (POST /shorten), sleeping 0.1 to 0.5 seconds between requests. Redirects were sent with allow_redirects=False so Locust did not follow them to example.com.

Because of those 5 creates per user at startup, creates made up about 14% of all requests in the stepped run (14,775 of 103,102), not 5%. The write load was heavier than intended.

## Results

### Run 1: 50 users, 10 users/s

21,208 requests, 0 failures, 151 requests/s. Redirects: median 9 ms, p95 42 ms, p99 170 ms. Creates: median 19 ms, p95 230 ms, p99 2.4 s, max 2.7 s.

The 151 requests/s was set by the number of users and their sleep time, not by the server, so it says nothing about capacity. The write tail was already visible (p99 about 125x the median), though it may partly come from the burst of creates when users start.

### Run 2: 105,000 users, 5,000 users/s

45,704 requests, 1,987 failures (4.3%): 1,529 of 14,308 creates (10.7%) and 458 of 31,396 redirects (1.5%). Median 3.6 s, p95 23 s, and only 77 requests/s, lower than run 1.

This run is not a usable capacity measurement. The jump was too large to show where degradation started, Locust itself was probably overloaded on the same machine, and the startup creates distorted the mix (at the moment of the screenshot, creates were at 59 requests/s against 18.5 for redirects). The cause of the failures was not inspected. Redirects did fail here, unlike in run 3.

### Run 3: stepped ramp, 100 to 3,500 users, 6 min 49 s

103,102 requests, 33 failures (0.03%), 252 requests/s on average. Approximate steady values at each step, read from the report's time series:

| Users | Requests/s | Median | p95 |
|---|---|---|---|
| 100 | 260-320 | 10-45 ms | 60-200 ms |
| 200 | 280-320 | ~220 ms | ~440 ms |
| 300 | ~270 | ~520 ms | ~800 ms |
| 500 | 180-360 | 1-2 s | 2-3 s |
| 1,000 | 230-320 | ~3 s | 3.6-5 s |
| 1,500 | 185-240 | ~7.7 s | 8-17 s |
| 3,000-3,500 | 150-245 | 7-18 s | 16-20 s |

Per endpoint over the whole run:

| | Requests | Median | p95 | p99 | Max | Failures |
|---|---|---|---|---|---|---|
| GET /shortener/[code] | 88,327 | 790 ms | 7.4 s | 14 s | 21.8 s | 0 |
| POST /shorten | 14,775 | 3.2 s | 19 s | 41 s | 56 s | 33 |

All 33 failures were on POST /shorten: 21 HTTP 500 errors, 9 ConnectionResetError (10054) and 3 ConnectionAbortedError (10053). They came in short bursts shortly after each increase in user count. The server log showed `sqlalchemy.exc.OperationalError: database is locked` on an `INSERT INTO urls`. Only one traceback was checked, so the other 500s are not individually confirmed, and the connection reset and abort errors are unexplained.

## What the Results Say About the Predictions

Write bottleneck: held up. Creates were about 4x slower than redirects at the median, had all the failures in the stepped run, and the server log shows SQLite's `database is locked` error on an INSERT. The exact scenario described above (500 concurrent writes) was not run. The test used mixed traffic, so a write-only test is still needed.

Read starvation: partly. No redirect failed in the stepped run (0 of 88,327), so reads did not time out entirely as predicted. Redirect latency did climb under load (median 790 ms, p95 7.4 s overall), so reads degraded without erroring. The results cannot say why. Writes holding locks, the single Python process running out of CPU or threads, and Locust competing for the same CPU are all still possible. Nothing was measured to separate them.

Throughput ceiling (not predicted): requests per second stayed around 250 to 300 from roughly 100 to 200 users upward. Beyond that, more users did not add throughput, they only made requests wait longer. Whether the ceiling belongs to the app or to Locust is unknown, because CPU per process was not recorded.

Where it broke: by error count it barely broke (0.03%). By latency it broke early. p95 stayed under about 1 s up to roughly 300 users and passed 2 s by 500. The baseline to improve on is about 270 requests/s, with p95 around 800 ms at 300 users.

## Corrections to the Analysis Above

1. SQLite, not SQLAlchemy, serializes writes. SQLAlchemy passes the INSERT to SQLite, which allows one writer at a time. A connection that cannot get the lock waits, then gives up. In Python's sqlite3 that wait defaults to 5 seconds. So the timeout is a lock wait, not a per-request execution timeout, and the failure reaches the app as an OperationalError.

2. In rollback-journal mode, a write does not block readers for its whole duration. Readers are blocked while the writer holds the exclusive lock, which happens at commit. With many queued writes this still adds up, but "completely blocked" overstates it. The read latency seen in run 3 is not evidence for either explanation until it is compared against a WAL run.

3. Raising the busy timeout is not a fix. It turns "database is locked" errors into longer waits. Writes were already at a 3.2 s median, so a 30 s timeout should mean fewer 500s and a worse p99, not faster writes. This is expected, not yet tested.

## Revised Next Steps

1. Fix the test: reduce on_start to one create per user (or seed codes once), and record machine specs and uvicorn worker count.
2. Record a baseline: `locust -f locustfile.py --host http://localhost:8000 --headless -u 300 -r 20 -t 2m`. Note requests/s, median and p95 for each endpoint.
3. During the run, watch CPU for the uvicorn process and the Locust process, to see which one hits its ceiling first.
4. Enable WAL with `synchronous=NORMAL`, rerun, and compare against the baseline.
5. Test the 30 s busy timeout separately, with WAL on, to check the prediction in correction 3.
6. Run uvicorn with `--workers 4` and rerun. Expected: redirects improve, creates do not, since SQLite still allows one writer.
7. Run a write-only test to check the original 500 concurrent writes scenario.
8. Only after that, move to PostgreSQL and add a Redis cache for redirects.