import socket
import base64
import csv
import time
import struct
import select
from datetime import datetime

# ============================================================
# NTRIP SETTINGS
# ============================================================

NTRIP_HOST = "caster.in-staging-all-freq-01.ce.swiftnav.com"
NTRIP_PORT = 2101
MOUNTPOINT = "MSM5"

USERNAME = "airtel.staging.demo"
PASSWORD = "0krqz6atb25q"

# ============================================================
# FILE SETTINGS
# ============================================================

GGA_FILE = "gga_log.csv"
OUTPUT_FILE = "rtcm_live_log.csv"

# Run for one hour
TEST_DURATION = 3600

# Your requested RTCM messages
TARGET_MESSAGES = {
    1006,
    1008,
    1019,
    1020,
    1029,
    1033,
    1042,
    1046,
    1075,
    1095,
    1125
}


# ============================================================
# READ RECORDED GGA
# ============================================================

def read_gga_file():

    gga_records = []

    with open(
        GGA_FILE,
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        reader = csv.reader(f)

        for row in reader:

            if len(row) < 2:
                continue

            timestamp_text = row[0].strip()
            gga = row[1].strip()

            if not gga.startswith("$"):
                continue

            try:
                timestamp = datetime.fromisoformat(
                    timestamp_text
                )

                gga_records.append(
                    (timestamp, gga)
                )

            except ValueError:
                continue

    return gga_records


# ============================================================
# RTCM MESSAGE TYPE DECODER
# ============================================================

def get_rtcm_message_type(frame):

    # RTCM3 frame:
    #
    # Byte 0      = D3
    # Bytes 1-2   = length
    # Payload     = message type in first 12 bits

    if len(frame) < 6:
        return None

    if frame[0] != 0xD3:
        return None

    payload_length = (
        ((frame[1] & 0x03) << 8)
        | frame[2]
    )

    if len(frame) < 3 + payload_length + 3:
        return None

    payload = frame[3:3 + payload_length]

    if len(payload) < 2:
        return None

    message_type = (
        (payload[0] << 4)
        | (payload[1] >> 4)
    )

    return message_type


# ============================================================
# RTCM FRAME EXTRACTION
# ============================================================

def extract_rtcm_frames(buffer):

    frames = []

    while True:

        # Find RTCM preamble
        start = buffer.find(b"\xD3")

        if start == -1:

            # Keep a few bytes in case a frame is split
            if len(buffer) > 2:
                buffer = buffer[-2:]

            break

        # Remove garbage before D3
        if start > 0:
            buffer = buffer[start:]

        # Need at least header
        if len(buffer) < 3:
            break

        payload_length = (
            ((buffer[1] & 0x03) << 8)
            | buffer[2]
        )

        # Complete RTCM frame:
        #
        # 3 bytes header
        # payload
        # 3 bytes CRC

        frame_length = 3 + payload_length + 3

        if len(buffer) < frame_length:
            break

        frame = buffer[:frame_length]

        frames.append(frame)

        buffer = buffer[frame_length:]

    return frames, buffer


# ============================================================
# NTRIP CONNECTION
# ============================================================

def connect_ntrip():

    print()
    print("=" * 60)
    print("CONNECTING TO NTRIP CASTER")
    print("=" * 60)

    sock = socket.create_connection(
        (NTRIP_HOST, NTRIP_PORT),
        timeout=15
    )

    credentials = (
        USERNAME + ":" + PASSWORD
    ).encode("utf-8")

    auth = base64.b64encode(
        credentials
    ).decode("ascii")

    request = (
        f"GET /{MOUNTPOINT} HTTP/1.0\r\n"
        f"Host: {NTRIP_HOST}\r\n"
        f"User-Agent: NTRIP Python RTCM Monitor/1.0\r\n"
        f"Authorization: Basic {auth}\r\n"
        f"Ntrip-Version: Ntrip/2.0\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )

    sock.sendall(request.encode("ascii"))

    # Receive HTTP/NTRIP response
    response = b""

    sock.settimeout(10)

    while b"\r\n\r\n" not in response:

        part = sock.recv(4096)

        if not part:
            break

        response += part

        if len(response) > 10000:
            break

    print()
    print("NTRIP SERVER RESPONSE:")
    print(response[:500])

    if (
        b"200 OK" not in response
        and b"ICY 200 OK" not in response
    ):

        print()
        print("ERROR: NTRIP connection was not accepted.")
        sock.close()
        return None, b""

    # Important:
    # Anything after HTTP headers is already RTCM data.

    header_end = response.find(b"\r\n\r\n")

    if header_end != -1:

        remaining_data = response[
            header_end + 4:
        ]

    else:

        remaining_data = b""

    sock.setblocking(False)

    print()
    print("NTRIP CONNECTION ESTABLISHED")
    print("Mountpoint:", MOUNTPOINT)

    return sock, remaining_data


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print()
    print("=" * 60)
    print("NTRIP + RECORDED GGA + RTCM MONITOR")
    print("=" * 60)

    # --------------------------------------------------------
    # Read GGA file
    # --------------------------------------------------------

    print()
    print("Reading:", GGA_FILE)

    gga_records = read_gga_file()

    if not gga_records:

        print("ERROR: No valid GGA records found.")
        return

    print(
        "Recorded GGA messages found:",
        len(gga_records)
    )

    print(
        "First GGA:",
        gga_records[0][1]
    )

    print(
        "Last GGA:",
        gga_records[-1][1]
    )

    # --------------------------------------------------------
    # Connect to NTRIP
    # --------------------------------------------------------

    sock, initial_data = connect_ntrip()

    if sock is None:
        return

    # --------------------------------------------------------
    # Prepare counters
    # --------------------------------------------------------

    message_counts = {}

    total_frames = 0
    total_bytes = 0

    start_time = time.time()

    next_gga_index = 0

    gga_start_timestamp = gga_records[0][0]

    # --------------------------------------------------------
    # Open CSV
    # --------------------------------------------------------

    csv_file = open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    )

    csv_writer = csv.writer(csv_file)

    csv_writer.writerow([
        "Receive_Time",
        "RTCM_Message",
        "Frame_Length",
        "Category"
    ])

    # --------------------------------------------------------
    # Process data function
    # --------------------------------------------------------

    def process_rtcm_data(data):

        nonlocal total_frames
        nonlocal total_bytes
        nonlocal initial_data

        initial_data += data

        frames, initial_data = extract_rtcm_frames(
            initial_data
        )

        for frame in frames:

            message_type = get_rtcm_message_type(
                frame
            )

            if message_type is None:
                continue

            total_frames += 1
            total_bytes += len(frame)

            message_counts[message_type] = (
                message_counts.get(message_type, 0) + 1
            )

            now = datetime.now()

            if message_type in TARGET_MESSAGES:

                category = "TARGET"

                print(
                    f"[{now.strftime('%H:%M:%S.%f')[:-3]}] "
                    f"RTCM {message_type} RECEIVED "
                    f"[TARGET]"
                )

            else:

                category = "OTHER"

                print(
                    f"[{now.strftime('%H:%M:%S.%f')[:-3]}] "
                    f"RTCM {message_type} received "
                    f"[OTHER]"
                )

            csv_writer.writerow([
                now.isoformat(),
                message_type,
                len(frame),
                category
            ])

            csv_file.flush()

    # --------------------------------------------------------
    # Process RTCM data that arrived with HTTP response
    # --------------------------------------------------------

    if initial_data:

        process_rtcm_data(b"")

    # --------------------------------------------------------
    # Start test
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("STARTING REAL-TIME RTCM MONITORING")
    print("=" * 60)

    print()
    print("Target messages:")

    print(
        sorted(TARGET_MESSAGES)
    )

    print()
    print("All other RTCM messages will ALSO be recorded.")

    print()
    print(
        "Test duration:",
        TEST_DURATION,
        "seconds"
    )

    print()
    print("Press Ctrl+C to stop early.")
    print()

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------

    try:

        while True:

            elapsed = time.time() - start_time

            if elapsed >= TEST_DURATION:
                break

            # =================================================
            # SEND RECORDED GGA
            # =================================================

            if next_gga_index < len(gga_records):

                original_timestamp, gga = (
                    gga_records[next_gga_index]
                )

                # Replay according to original timestamps
                original_elapsed = (
                    original_timestamp -
                    gga_start_timestamp
                ).total_seconds()

                if elapsed >= original_elapsed:

                    try:

                        sock.sendall(
                            (gga + "\r\n").encode(
                                "ascii"
                            )
                        )

                        print(
                            f"[GGA] Sent recorded GGA "
                            f"{next_gga_index + 1}/"
                            f"{len(gga_records)}"
                        )

                    except Exception as e:

                        print(
                            "GGA send error:",
                            e
                        )

                    next_gga_index += 1

            # =================================================
            # RECEIVE RTCM
            # =================================================

            try:

                readable, _, _ = select.select(
                    [sock],
                    [],
                    [],
                    0.1
                )

                if readable:

                    data = sock.recv(8192)

                    if not data:

                        print()
                        print(
                            "NTRIP caster closed the connection."
                        )

                        break

                    process_rtcm_data(data)

            except BlockingIOError:
                pass

            except Exception as e:

                print(
                    "RTCM receive error:",
                    e
                )

                break

    except KeyboardInterrupt:

        print()
        print("Stopping monitoring...")

    finally:

        try:
            sock.close()
        except:
            pass

        csv_file.close()

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 60)
    print("FINAL RTCM MESSAGE SUMMARY")
    print("=" * 60)

    print()
    print("Total RTCM frames:", total_frames)
    print("Total RTCM bytes :", total_bytes)

    print()
    print("TARGET MESSAGES")
    print("-" * 40)

    for message_type in sorted(TARGET_MESSAGES):

        count = message_counts.get(
            message_type,
            0
        )

        print(
            f"RTCM {message_type}: {count}"
        )

    print()
    print("OTHER RTCM MESSAGES")
    print("-" * 40)

    other_messages = sorted(
        msg for msg in message_counts
        if msg not in TARGET_MESSAGES
    )

    if other_messages:

        for message_type in other_messages:

            print(
                f"RTCM {message_type}: "
                f"{message_counts[message_type]}"
            )

    else:

        print("No other RTCM messages detected.")

    print()
    print("=" * 60)
    print("CSV FILE CREATED:")
    print(OUTPUT_FILE)
    print("=" * 60)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()