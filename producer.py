# ══════════════════════════════════════════════════════════════════
#  STAGE-3 | PRODUCER — Real-Time Smart City Analytics
#  Streams Traffic, Energy & Pollution records to Kafka (2026 →)
#
#  STREAM CONTINUITY DESIGN
#  ─────────────────────────
#  Generate_data.py maintains stream_state.txt which holds the ISO
#  timestamp of the last emitted record.  On every batch:
#    1. generate_traffic_record() reads stream_state.txt, advances
#       the stream clock by STREAM_INTERVAL_SECS, and writes it back.
#    2. generate_energy_record() and generate_pollution_record()
#       return records from the same batch cache, sharing the same
#       timestamp — all three topics are always in sync.
#  On crash/restart: the producer resumes exactly from the next
#  timestamp, no duplicate or missing records.
#
#  Run:  python producer.py
#  Stop: Ctrl+C  (final flush happens in `finally` block)
# ══════════════════════════════════════════════════════════════════
import os
import json
import time
import itertools
import logging
from datetime import datetime
 
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
 
from Generate_data import (
    generate_traffic_record,
    generate_energy_record,
    generate_pollution_record,
    STREAM_STATE_FILE,
    STREAM_START,
    STREAM_INTERVAL_SECS
)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("SmartCityProducer")

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'localhost:9092')
DELAY = 30  # Delay in seconds between sending messages (must match STREAM_INTERVAL_SECS in Generate_data)

if DELAY != STREAM_INTERVAL_SECS:
    raise ValueError(
        f"DELAY ({DELAY}) must match STREAM_INTERVAL_SECS ({STREAM_INTERVAL_SECS})"
    )

TOTAL_BATCHES = 0  # Total number of batches to send
LOG_INTERVAL = 10  # Log interval in seconds
MAX_RETRIES = 5  # Maximum number of retries for sending messages
RETRY_DELAY = 5  # Delay in seconds between retries

# Function to send data to Kafka topic
TOPICS: dict[str, str] = {
    "traffic" : "traffic_topic",
    "energy"   : "energy_topic",
    "pollution": "pollution_topic"
}

# ══════════════════════════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════════════════════════
def on_send_error(exc: Exception) -> None:
    """Called when a message fails to deliver."""
    log.error(f"Message delivery failed: {exc}")

def on_send_success(record_metadata) -> None:
    """Optional success callback — enabled in verbose mode."""
    pass  # Suppress per-message logs to avoid flooding the console

# ══════════════════════════════════════════════════════════════════
#  PRODUCER FACTORY WITH RETRY
# ══════════════════════════════════════════════════════════════════
def create_producer(retries: int = MAX_RETRIES) -> KafkaProducer:
    """
    Create a KafkaProducer with production-grade settings.
    Retries on NoBrokersAvailable up to `retries` times.
    Raises RuntimeError if the broker is still unreachable after all attempts.
    """
    for attempt in range(1, retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None, 
                # Reliability
                acks="all",                  # wait for all ISR replicas
                retries=5,                   # broker-level retry on transient failure
                retry_backoff_ms=300,        # back-off between retries
                # Throughput
                linger_ms=10,                # batch messages for 10 ms before sending
                batch_size=32_768,           # 32 KB batch size
                compression_type="gzip",     # compress payloads
                # Stability
                max_block_ms=15_000,         # wait up to 15 s if buffer is full
                request_timeout_ms=30_000,   # broker request timeout
                max_in_flight_requests_per_connection=1,  # preserve ordering with retries
            )
            log.info(f"Connected to Kafka broker at {KAFKA_BROKER} (attempt {attempt}/{retries})")
            return producer
        except NoBrokersAvailable:
            log.warning(
                f"Broker unavailable (attempt {attempt}/{retries}). "
                f"Retrying in {RETRY_DELAY}s..."
            )
            time.sleep(RETRY_DELAY)

    raise RuntimeError(
        f"Could not connect to Kafka broker at {KAFKA_BROKER} after {retries} attempts. "
        f"Ensure Kafka is running before starting the producer."
    )

# ══════════════════════════════════════════════════════════════════
#  SEND HELPER
# ══════════════════════════════════════════════════════════════════
def send_records(producer: KafkaProducer, topic: str, records: list) -> int:
    """
    Enqueue a list of record dicts to the given Kafka topic.
    Partitioning key = area so records for the same area always go
    to the same partition, preserving per-area ordering.
    Returns the number of successfully enqueued messages.
    """
    sent = 0
    for record in records:
        try:
            key = str(record.get("area", ""))
            (
                producer
                .send(topic, key=key, value=record)
                .add_callback(on_send_success)
                .add_errback(on_send_error)
            )
            sent += 1
        except KafkaError as exc:
            log.error(f"Failed to enqueue record to {topic}: {exc}")
    return sent

# ══════════════════════════════════════════════════════════════════
#  STREAM STATE HELPER
# ══════════════════════════════════════════════════════════════════
def _read_stream_ts() -> str:
    """Return the current stream clock timestamp string, or '—' if none."""
    if os.path.exists(STREAM_STATE_FILE):
        with open(STREAM_STATE_FILE) as f:
            return f.read().strip()
    return "—"

# ══════════════════════════════════════════════════════════════════
#  MAIN PRODUCE LOOP
# ══════════════════════════════════════════════════════════════════
def run() -> None:
    # ── Startup banner ────────────────────────────────────────────
    if os.path.exists(STREAM_STATE_FILE):
        resume_info = f"resuming after {_read_stream_ts()}"
    else:
        resume_info = f"starting from {STREAM_START.isoformat()}"

    log.info("=" * 60)
    log.info("  Smart City Producer  —  Starting")
    log.info("=" * 60)
    log.info(f"  Kafka broker  : {KAFKA_BROKER}")
    log.info(f"  Total batches : {TOTAL_BATCHES if TOTAL_BATCHES else '∞ (infinite - Ctrl+C to stop)'}")
    log.info(f"  Delay/batch   : {DELAY}s")
    log.info(f"  Topics        : {' | '.join(TOPICS.values())}")
    log.info(f"  Stream clock   : {resume_info}")
    log.info(f"  State file     : {STREAM_STATE_FILE}")
    log.info("=" * 60)
 
    producer = create_producer()
 
    # Counters
    sent_t = sent_e = sent_p = 0
    failed = 0
    start_time = time.time()

    batch_source = itertools.count() 
    if TOTAL_BATCHES > 0:
        batch_source = itertools.islice(batch_source, TOTAL_BATCHES)
 
    try:
        for batch_idx in batch_source:
            batch_start = time.time()
            ts = datetime.now()   # wall-clock time passed to generator (informational only)
 
            # ── Traffic ──────────────────────────────────────────
            # NOTE: generate_traffic_record() MUST be called FIRST per batch.
            #       It advances the stream clock and populates the batch cache.
            #       generate_energy_record() and generate_pollution_record()
            #       read from that cache — order matters here.
            try:
                traffic_records = generate_traffic_record(ts)
                if not traffic_records:
                    log.warning(f"Empty traffic batch (batch {batch_idx})")
                else:
                    sent_t += send_records(
                    producer, TOPICS["traffic"], traffic_records
                )
            except Exception as exc:
                log.error(f"Traffic generator error (batch {batch_idx}): {exc}")
                failed += 1
 
            # ── Generate & send Energy Data ────────────────────────────
            try:
                energy_records = generate_energy_record(ts)
                if not energy_records:
                    log.warning(f"Empty energy batch (batch {batch_idx})")
                else:
                    sent_e += send_records(
                    producer, TOPICS["energy"], energy_records
                )
            except Exception as exc:
                log.error(f"Energy generator error (batch {batch_idx}): {exc}")
                failed += 1
 
            # ── Generate & send Pollution Data ─────────────────────────
            try:
                pollution_records = generate_pollution_record(ts)
                if not pollution_records:
                    log.warning(f"Empty pollution batch (batch {batch_idx})")
                else:
                    sent_p += send_records(
                    producer, TOPICS["pollution"], pollution_records
                )
            except Exception as exc:
                log.error(f"Pollution generator error (batch {batch_idx}): {exc}")
                failed += 1

            producer.flush()
 
            # ── Progress log ──────────────────────────────────────
            if batch_idx == 0 or (batch_idx + 1) % LOG_INTERVAL == 0:
                elapsed = time.time() - start_time
                total_sent = sent_t + sent_e + sent_p
                throughput = total_sent / max(elapsed, 1)
                log.info(
                    f"Batch {batch_idx+1:>4} | "
                    f"T:{sent_t:>5} E:{sent_e:>5} P:{sent_p:>5} | "
                    f"Errors:{failed:>3} | "
                    f"{throughput:.1f} msg/s | "
                    f"Stream clock: {_read_stream_ts()}"
                )

            # ── Adaptive sleep ────────────────────────────────────
            # Subtract the time already spent generating & sending so the
            # interval between batches stays exactly DELAY seconds.
            batch_elapsed = time.time() - batch_start
            sleep_time = max(0.0, DELAY - batch_elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)
 
    except KeyboardInterrupt:
        log.info("Producer interrupted by user (Ctrl+C).")
 
    except Exception as exc:
        log.exception(f"Unexpected error in producer loop: {exc}")
 
    finally:
        # Flush any remaining buffered messages before closing
        log.info("Flushing remaining messages before shutting down...")
        producer.flush(timeout=30)
        producer.close(timeout=10)
 
        elapsed_total = time.time() - start_time
        total_sent    = sent_t + sent_e + sent_p
 
        log.info("\n" + "=" * 60)
        log.info("  PRODUCER FINAL SUMMARY")
        log.info("=" * 60)
        log.info(f"  Traffic records sent   : {sent_t:>6}")
        log.info(f"  Energy records sent    : {sent_e:>6}")
        log.info(f"  Pollution records sent : {sent_p:>6}")
        log.info(f"  Total records sent     : {total_sent:>6}")
        log.info(f"  Failed enqueues        : {failed:>6}")
        log.info(f"  Total elapsed time     : {elapsed_total:.1f}s")
        log.info(f"  Avg throughput         : {total_sent / max(elapsed_total, 1):.1f} msg/s")
        log.info(f"  Stream clock stopped at: {_read_stream_ts()}")
        log.info("  Producer closed cleanly.")
        log.info("=" * 60)
 
if __name__ == "__main__":
    run()