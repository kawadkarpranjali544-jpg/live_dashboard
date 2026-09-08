import base64
import csv
import os
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from io import BytesIO

from pyrtcm import RTCMReader


# ============================================================
# CLOUD / GITHUB SETTINGS
# ============================================================

NTRIP_HOST = os.getenv(
    "NTRIP_HOST",
    "caster.in-staging-all-freq-01.ce.swiftnav.com"
)
NTRIP_PORT = int(os.getenv("NTRIP_PORT", "2101"))
MOUNTPOINT = os.getenv("MOUNTPOINT", "MSM5")

# Credentials are intentionally read from environment variables.
# NEVER put the real username/password directly in this file.
USERNAME = os.getenv("NTRIP_USERNAME", "")
PASSWORD = os.getenv("NTRIP_PASSWORD", "")

GGA_FILE = os.getenv("GGA_FILE", "gga_log.csv")
RTCM_FILE = os.getenv("RTCM_FILE", "rtcm_live_log.csv")

GGA_INTERVAL = float(os.getenv("GGA_INTERVAL", "1.0"))
PUBLISH_INTERVAL = int(os.getenv("PUBLISH_INTERVAL", "60"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "1000"))
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "10"))


# ============================================================
# 20 RTCM MESSAGE TYPES FOR THE DASHBOARD
# ============================================================

TARGET_MESSAGES = {
    1005: "Reference Station ARP",
    1006: "Reference Station ARP + Antenna Height",
    1008: "Antenna Descriptor & Serial Number",
    1013: "System Parameters",
    1019: "GPS Satellite Ephemeris",
    1020: "GLONASS Satellite Ephemeris",
    1029: "Unicode Text String",
    1032: "Physical Reference Station",
    1033: "Receiver & Antenna Descriptor",
    1042: "BeiDou Satellite Ephemeris",
    1044: "QZSS Satellite Ephemeris",
    1045: "Galileo F/NAV Ephemeris",
    1046: "Galileo I/NAV Ephemeris",
    1075: "GPS MSM5 Observation",
    1085: "GLONASS MSM5 Observation",
    1095: "Galileo MSM5 Observation",
    1115: "QZSS MSM5 Observation",
    1125: "BeiDou MSM5 Observation",
    1135: "NavIC/IRNSS MSM5 Observation",
    1230: "GLONASS Code-Phase Biases",
}


CSV_HEADER = [
    "Timestamp",
    "RTCM_Message_ID",
    "Description",
    "Count",
    "Message_Length",
    "Status",
]

running = True
message_counts = {}
total_bytes = 0
counts_lock = threading.Lock()


# ============================================================
# LOAD RECORDED GGA
# ============================================================

def load_gga_messages():
    if not os.path.exists(GGA_FILE):
        print("ERROR: GGA file not found:")
        print(os.path.abspath(GGA_FILE))
        return []

    messages = []

    try:
        with open(
            GGA_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:
            reader = csv.reader(file)

            for row in reader:
                if not row:
                    continue

                for item in row:
                    item = item.strip()

                    if (
                        item.startswith("$GNGGA")
                        or item.startswith("$GPGGA")
                    ):
                        messages.append(
                            item.rstrip("\r\n") + "\r\n"
                        )
                        break

        print("Recorded GGA messages loaded:", len(messages))
        return messages

    except Exception as exc:
        print("ERROR reading GGA file:", exc)
        return []


# ============================================================
# CREATE / PREPARE RTCM CSV
# ============================================================

def ensure_csv():
    if (
        not os.path.exists(RTCM_FILE)
        or os.path.getsize(RTCM_FILE) == 0
    ):
        with open(
            RTCM_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:
            csv.writer(file).writerow(CSV_HEADER)


def trim_csv():
    if not os.path.exists(RTCM_FILE):
        return

    try:
        with open(
            RTCM_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:
            rows = list(csv.reader(file))

        if len(rows) <= MAX_ROWS + 1:
            return

        with open(
            RTCM_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADER)
            writer.writerows(rows[-MAX_ROWS:])

    except Exception as exc:
        print("CSV trim warning:", exc)


# ============================================================
# SAVE ONE RTCM MESSAGE
# ============================================================

def save_message(
    timestamp,
    message_id,
    count,
    message_length
):
    description = TARGET_MESSAGES.get(
        message_id,
        "Other RTCM Message"
    )

    status = (
        "TARGET"
        if message_id in TARGET_MESSAGES
        else "OTHER"
    )

    with open(
        RTCM_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            timestamp,
            message_id,
            description,
            count,
            message_length,
            status,
        ])


# ============================================================
# EXTRACT RTCM3 FRAMES
# ============================================================

def extract_rtcm_frames(buffer):
    frames = []

    while True:
        start = buffer.find(b"\xD3")

        if start == -1:
            return b"", frames

        buffer = buffer[start:]

        if len(buffer) < 3:
            return buffer, frames

        payload_length = (
            ((buffer[1] & 0x03) << 8)
            | buffer[2]
        )

        frame_length = (
            3
            + payload_length
            + 3
        )

        if len(buffer) < frame_length:
            return buffer, frames

        frame = buffer[:frame_length]
        frames.append(frame)

        buffer = buffer[frame_length:]


# ============================================================
# DECODE RTCM FRAME
# ============================================================

def decode_rtcm_frame(frame):
    try:
        stream = BytesIO(frame)
        reader = RTCMReader(stream)

        raw_data, parsed_data = next(reader)

        identity = str(
            parsed_data.identity
        ).replace("RTCM", "").strip()

        return int(identity)

    except Exception:
        return None


# ============================================================
# SEND RECORDED GGA
# ============================================================

def gga_sender(
    sock,
    gga_messages,
    stop_event
):
    if not gga_messages:
        print("ERROR: No recorded GGA messages.")
        return

    index = 0

    while not stop_event.is_set():
        try:
            gga = gga_messages[index]

            sock.sendall(
                gga.encode(
                    "ascii",
                    errors="ignore"
                )
            )

            index += 1

            if index >= len(gga_messages):
                index = 0

            stop_event.wait(GGA_INTERVAL)

        except (
            BrokenPipeError,
            ConnectionResetError,
            OSError
        ):
            return


# ============================================================
# CONNECT TO NTRIP CASTER
# ============================================================

def connect_to_ntrip():
    if not USERNAME or not PASSWORD:
        raise RuntimeError(
            "NTRIP_USERNAME and NTRIP_PASSWORD "
            "environment variables are not set."
        )

    sock = socket.create_connection(
        (
            NTRIP_HOST,
            NTRIP_PORT
        ),
        timeout=15
    )

    credentials = (
        f"{USERNAME}:{PASSWORD}"
    ).encode("utf-8")

    auth = base64.b64encode(
        credentials
    ).decode("ascii")

    request = (
        f"GET /{MOUNTPOINT} HTTP/1.0\r\n"
        f"Host: {NTRIP_HOST}\r\n"
        "User-Agent: NTRIP Python RTCM Monitor/1.0\r\n"
        f"Authorization: Basic {auth}\r\n"
        "Ntrip-Version: Ntrip/2.0\r\n"
        "Accept: */*\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    sock.sendall(
        request.encode("ascii")
    )

    response = sock.recv(4096)

    print(
        "NTRIP server response:",
        response[:200]
    )

    if b"200 OK" not in response:
        sock.close()

        raise RuntimeError(
            f"NTRIP connection failed: "
            f"{response[:200]!r}"
        )

    header_end = response.find(
        b"\r\n\r\n"
    )

    if header_end != -1:
        initial_data = response[
            header_end + 4:
        ]
    else:
        initial_data = b""

    sock.settimeout(2.0)

    return sock, initial_data


# ============================================================
# PUBLISH CSV TO GITHUB
# ============================================================

def publish_to_github():
    try:
        trim_csv()

        subprocess.run(
            [
                "git",
                "config",
                "user.name",
                "github-actions[bot]"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        subprocess.run(
            [
                "git",
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        subprocess.run(
            [
                "git",
                "add",
                RTCM_FILE
            ],
            check=True,
            capture_output=True,
            text=True
        )

        status = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--",
                RTCM_FILE
            ],
            check=True,
            capture_output=True,
            text=True
        )

        if not status.stdout.strip():
            return

        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "Update live RTCM data"
            ],
            check=True,
            capture_output=True,
            text=True
        )

        subprocess.run(
            ["git", "push"],
            check=True,
            capture_output=True,
            text=True
        )

        print(
            "Latest RTCM data published to GitHub."
        )

    except subprocess.CalledProcessError as exc:
        print(
            "GitHub publish warning:",
            exc.stderr.strip()
            if exc.stderr
            else str(exc)
        )


# ============================================================
# MONITOR ONE NTRIP CONNECTION
# ============================================================

def monitor_connection(gga_messages):
    global running
    global total_bytes

    sock, buffer = connect_to_ntrip()

    stop_gga = threading.Event()

    gga_thread = threading.Thread(
        target=gga_sender,
        args=(
            sock,
            gga_messages,
            stop_gga
        ),
        daemon=True
    )

    gga_thread.start()

    last_publish = time.monotonic()

    try:
        while running:

            try:
                data = sock.recv(4096)

                if not data:
                    raise ConnectionError(
                        "NTRIP caster closed the connection."
                    )

                buffer += data
                total_bytes += len(data)

                buffer, frames = (
                    extract_rtcm_frames(buffer)
                )

                for frame in frames:

                    message_id = (
                        decode_rtcm_frame(frame)
                    )

                    if message_id is None:
                        continue

                    with counts_lock:
                        message_counts[
                            message_id
                        ] = (
                            message_counts.get(
                                message_id,
                                0
                            ) + 1
                        )

                        count = message_counts[
                            message_id
                        ]

                    timestamp = (
                        datetime.now(
                            timezone.utc
                        ).strftime(
                            "%Y-%m-%d %H:%M:%S.%f"
                        )[:-3]
                    )

                    save_message(
                        timestamp,
                        message_id,
                        count,
                        len(frame)
                    )

                    label = (
                        "TARGET"
                        if message_id
                        in TARGET_MESSAGES
                        else "OTHER"
                    )

                    print(
                        f"[{label}] "
                        f"{timestamp} | "
                        f"RTCM {message_id} | "
                        f"Count: {count}"
                    )

                if (
                    time.monotonic()
                    - last_publish
                    >= PUBLISH_INTERVAL
                ):
                    publish_to_github()
                    last_publish = (
                        time.monotonic()
                    )

            except socket.timeout:

                if (
                    time.monotonic()
                    - last_publish
                    >= PUBLISH_INTERVAL
                ):
                    publish_to_github()
                    last_publish = (
                        time.monotonic()
                    )

                continue

    finally:
        stop_gga.set()

        try:
            sock.close()
        except OSError:
            pass

        publish_to_github()


# ============================================================
# MAIN
# ============================================================

def main():
    global running

    print()
    print("==========================================")
    print("       GNSS RTCM CLOUD MONITOR")
    print("==========================================")
    print()
    print(
        "Recorded GGA -> NTRIP -> RTCM -> CSV -> GitHub"
    )
    print()

    gga_messages = load_gga_messages()

    if not gga_messages:
        print(
            "Program stopped because no GGA data was found."
        )
        return

    ensure_csv()

    print(
        f"NTRIP: {NTRIP_HOST}:{NTRIP_PORT}"
    )
    print(
        f"Mountpoint: {MOUNTPOINT}"
    )
    print(
        f"Publish interval: {PUBLISH_INTERVAL} seconds"
    )
    print(
        f"Maximum CSV rows: {MAX_ROWS}"
    )
    print()

    while running:

        try:
            monitor_connection(
                gga_messages
            )

        except KeyboardInterrupt:
            running = False
            break

        except Exception as exc:
            print()
            print(
                "NTRIP/monitor error:",
                exc
            )

            if running:
                print(
                    f"Reconnecting in "
                    f"{RECONNECT_DELAY} seconds..."
                )

                time.sleep(
                    RECONNECT_DELAY
                )


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        running = False
        print()
        print("Monitor stopped.")
