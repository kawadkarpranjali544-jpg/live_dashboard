import socket
import base64
import csv
import os
import time
import threading
from io import BytesIO
from datetime import datetime

from pyrtcm import RTCMReader


# ============================================================
# NTRIP SETTINGS
# ============================================================

NTRIP_HOST = "caster.in-staging-all-freq-01.ce.swiftnav.com"
NTRIP_PORT = 2101
MOUNTPOINT = "MSM5"

# ------------------------------------------------------------
# PUT YOUR ACTUAL NTRIP CREDENTIALS HERE
# ------------------------------------------------------------

USERNAME = "airtel.staging.demo"
PASSWORD = "0krqz6atb25q"


# ============================================================
# INPUT / OUTPUT FILES
# ============================================================

GGA_FILE = "gga_log.csv"
RTCM_FILE = "rtcm_live_log.csv"


# ============================================================
# GGA SETTINGS
# ============================================================

# Time between sending recorded GGA messages.
# 1 second is suitable for testing.
GGA_INTERVAL = 1.0


# ============================================================
# REQUIRED RTCM MESSAGE TYPES
# ============================================================

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
# RTCM DESCRIPTIONS
# ============================================================

RTCM_DESCRIPTIONS = {

    1006: "Station ARP / Reference Station Position",

    1008: "Reference Station Antenna Information",

    1019: "GPS Satellite Ephemeris",

    1020: "GLONASS Satellite Ephemeris",

    1029: "Unicode Text / Broadcast Message",

    1033: "Receiver / Antenna Descriptor",

    1042: "BeiDou Satellite Ephemeris",

    1046: "Galileo Satellite Ephemeris",

    1075: "GPS MSM5 Observation Corrections",

    1095: "QZSS MSM5 Observation Corrections",

    1125: "BeiDou MSM5 Observation Corrections"
}


# ============================================================
# GLOBAL VARIABLES
# ============================================================

running = True

message_counts = {}

total_bytes = 0


# ============================================================
# LOAD RECORDED GGA DATA
# ============================================================

def load_gga_messages():

    if not os.path.exists(GGA_FILE):

        print()
        print("ERROR: GGA file not found.")
        print()
        print("Expected file:")
        print(
            os.path.abspath(GGA_FILE)
        )

        return []

    gga_messages = []

    print()
    print("Reading recorded GGA file...")
    print(
        "File:",
        os.path.abspath(GGA_FILE)
    )

    try:

        with open(
            GGA_FILE,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.reader(file)

            rows = list(reader)

        if not rows:

            print("ERROR: GGA file is empty.")

            return []


        # ----------------------------------------------------
        # Detect whether first row is a header
        # ----------------------------------------------------

        start_index = 0

        first_row = rows[0]

        if first_row:

            first_text = ",".join(first_row)

            if (
                "header" in first_text.lower()
                or "timestamp" in first_text.lower()
            ):

                start_index = 1


        # ----------------------------------------------------
        # Extract GGA sentences
        # ----------------------------------------------------

        for row in rows[start_index:]:

            if not row:
                continue

            gga_sentence = None

            # Case 1:
            # timestamp, GGA sentence

            for item in row:

                item = item.strip()

                if (
                    item.startswith("$GNGGA")
                    or item.startswith("$GPGGA")
                ):

                    gga_sentence = item

                    break


            if gga_sentence:

                if not gga_sentence.endswith("\r\n"):

                    gga_sentence += "\r\n"

                gga_messages.append(
                    gga_sentence
                )


        print(
            "Recorded GGA messages loaded:",
            len(gga_messages)
        )

        return gga_messages


    except Exception as e:

        print()
        print("ERROR reading GGA file:")
        print(e)

        return []


# ============================================================
# CREATE RTCM CSV FILE
# ============================================================

def create_csv():

    with open(
        RTCM_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "Timestamp",
            "RTCM_Message_ID",
            "Description",
            "Count",
            "Message_Length",
            "Status"
        ])


# ============================================================
# SAVE RTCM MESSAGE
# ============================================================

def save_message(
    timestamp,
    message_id,
    count,
    message_length
):

    description = RTCM_DESCRIPTIONS.get(
        message_id,
        "Other RTCM Message"
    )

    if message_id in TARGET_MESSAGES:

        status = "TARGET"

    else:

        status = "OTHER"


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
            status
        ])


# ============================================================
# SEND RECORDED GGA
# ============================================================

def gga_sender(sock, gga_messages):

    global running

    print()
    print("------------------------------------------")
    print("RECORDED GGA TRANSMISSION")
    print("------------------------------------------")

    if not gga_messages:

        print("No GGA messages available.")

        running = False

        return


    index = 0

    while running:

        try:

            gga = gga_messages[index]

            sock.sendall(
                gga.encode("ascii", errors="ignore")
            )

            print(
                "GGA sent:",
                gga.strip()
            )


            # ------------------------------------------------
            # Move to next recorded GGA
            # ------------------------------------------------

            index += 1

            if index >= len(gga_messages):

                # Start again from the beginning.
                #
                # IMPORTANT:
                # These are still your RECORDED GGA messages.
                # No fake GGA is being generated.

                index = 0

                print()
                print(
                    "Recorded GGA file reached the end."
                )

                print(
                    "Restarting recorded GGA sequence..."
                )

            time.sleep(GGA_INTERVAL)


        except Exception as e:

            print()
            print("GGA transmission stopped:")
            print(e)

            running = False

            break


# ============================================================
# EXTRACT RTCM MESSAGE FROM BUFFER
# ============================================================

def extract_rtcm_frames(buffer):

    frames = []

    while True:

        # ----------------------------------------------------
        # RTCM3 messages start with 0xD3
        # ----------------------------------------------------

        start = buffer.find(b"\xD3")

        if start == -1:

            # No RTCM preamble found.
            # Keep only a small amount of data.

            return b"", frames


        # ----------------------------------------------------
        # Remove bytes before RTCM preamble
        # ----------------------------------------------------

        if start > 0:

            buffer = buffer[start:]


        # ----------------------------------------------------
        # Need at least 3 bytes for RTCM header
        # ----------------------------------------------------

        if len(buffer) < 3:

            return buffer, frames


        # ----------------------------------------------------
        # RTCM payload length
        # ----------------------------------------------------

        payload_length = (
            ((buffer[1] & 0x03) << 8)
            | buffer[2]
        )


        # ----------------------------------------------------
        # Complete frame:
        #
        # 3 bytes header
        # + payload
        # + 3 bytes CRC
        # ----------------------------------------------------

        frame_length = (
            3
            + payload_length
            + 3
        )


        if len(buffer) < frame_length:

            return buffer, frames


        # ----------------------------------------------------
        # Extract complete frame
        # ----------------------------------------------------

        frame = buffer[
            :frame_length
        ]

        frames.append(frame)

        buffer = buffer[
            frame_length:
        ]


# ============================================================
# DECODE RTCM FRAME
# ============================================================

def decode_rtcm_frame(frame):

    try:

        stream = BytesIO(frame)

        reader = RTCMReader(
            stream
        )

        raw_data, parsed_data = next(
            reader
        )

        identity = parsed_data.identity

        # Usually identity is like "1006"
        message_id = int(
            str(identity)
            .replace("RTCM", "")
            .strip()
        )

        return message_id

    except Exception:

        return None


# ============================================================
# MAIN PROGRAM
# ============================================================

print()
print("==========================================")
print("        GNSS RTCM LIVE MONITOR")
print("==========================================")

print()
print("Project mode:")
print("Recorded GGA → NTRIP → RTCM → Decoder → CSV")

print()
print("Target RTCM messages:")

for msg in sorted(TARGET_MESSAGES):

    print(
        msg,
        "-",
        RTCM_DESCRIPTIONS[msg]
    )


# ============================================================
# LOAD GGA
# ============================================================

gga_messages = load_gga_messages()

if not gga_messages:

    print()
    print("Program stopped because no GGA data was found.")

    raise SystemExit


# ============================================================
# CREATE OUTPUT CSV
# ============================================================

create_csv()

print()
print(
    "RTCM output file:",
    os.path.abspath(RTCM_FILE)
)


# ============================================================
# CONNECT TO NTRIP
# ============================================================

print()
print("------------------------------------------")
print("CONNECTING TO NTRIP CASTER")
print("------------------------------------------")

try:

    sock = socket.create_connection(
        (
            NTRIP_HOST,
            NTRIP_PORT
        ),
        timeout=15
    )

    print("TCP connection established.")


except Exception as e:

    print()
    print("ERROR connecting to NTRIP caster:")
    print(e)

    raise SystemExit


# ============================================================
# NTRIP AUTHENTICATION
# ============================================================

credentials = (
    USERNAME
    + ":"
    + PASSWORD
).encode()


auth = base64.b64encode(
    credentials
).decode()


# ============================================================
# NTRIP REQUEST
# ============================================================

request = (

    f"GET /{MOUNTPOINT} HTTP/1.0\r\n"

    f"Host: {NTRIP_HOST}\r\n"

    f"User-Agent: NTRIP Python RTCM Monitor/1.0\r\n"

    f"Authorization: Basic {auth}\r\n"

    f"Ntrip-Version: Ntrip/2.0\r\n"

    f"Accept: */*\r\n"

    f"Connection: close\r\n"

    f"\r\n"
)


sock.sendall(
    request.encode()
)


# ============================================================
# RECEIVE SERVER RESPONSE
# ============================================================

try:

    response = sock.recv(
        4096
    )

except Exception as e:

    print()
    print("ERROR receiving NTRIP response:")
    print(e)

    sock.close()

    raise SystemExit


print()
print("NTRIP server response:")
print(response[:500])


# ============================================================
# CHECK CONNECTION
# ============================================================

if b"200 OK" not in response:

    print()
    print("==========================================")
    print("NTRIP CONNECTION FAILED")
    print("==========================================")

    sock.close()

    raise SystemExit


print()
print("==========================================")
print("NTRIP CONNECTION SUCCESSFUL")
print("==========================================")


# ============================================================
# IMPORTANT:
# SERVER RESPONSE MAY CONTAIN RTCM DATA
# AFTER HTTP HEADERS.
# ============================================================

header_end = response.find(
    b"\r\n\r\n"
)

if header_end != -1:

    initial_rtcm_data = response[
        header_end + 4:
    ]

else:

    initial_rtcm_data = b""


# ============================================================
# SET SOCKET TIMEOUT
# ============================================================

sock.settimeout(
    2.0
)


# ============================================================
# START GGA THREAD
# ============================================================

gga_thread = threading.Thread(
    target=gga_sender,
    args=(
        sock,
        gga_messages
    ),
    daemon=True
)

gga_thread.start()


print()
print("------------------------------------------")
print("RTCM MONITOR STARTED")
print("------------------------------------------")

print()
print("Recorded GGA is being sent to caster.")

print(
    "Waiting for RTCM correction messages..."
)

print()
print("Monitoring ALL RTCM message types.")

print()
print("Press Ctrl+C to stop.")

print()
print("------------------------------------------")


# ============================================================
# RTCM BUFFER
# ============================================================

buffer = initial_rtcm_data


# ============================================================
# MAIN RTCM LOOP
# ============================================================

try:

    while running:

        try:

            data = sock.recv(
                4096
            )


            # ------------------------------------------------
            # Empty data means connection closed
            # ------------------------------------------------

            if not data:

                print()
                print(
                    "NTRIP caster closed the connection."
                )

                break


            # ------------------------------------------------
            # Add data to buffer
            # ------------------------------------------------

            buffer += data

            total_bytes += len(data)


            # ------------------------------------------------
            # Extract complete RTCM frames
            # ------------------------------------------------

            buffer, frames = extract_rtcm_frames(
                buffer
            )


            # ------------------------------------------------
            # Decode every RTCM frame
            # ------------------------------------------------

            for frame in frames:

                message_id = decode_rtcm_frame(
                    frame
                )


                # ------------------------------------------------
                # Could not decode frame
                # ------------------------------------------------

                if message_id is None:

                    continue


                # ------------------------------------------------
                # Update count
                # ------------------------------------------------

                message_counts[message_id] = (

                    message_counts.get(
                        message_id,
                        0
                    )
                    + 1

                )


                count = message_counts[
                    message_id
                ]


                timestamp = (
                    datetime.now()
                    .strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    )[:-3]
                )


                # ------------------------------------------------
                # Description
                # ------------------------------------------------

                description = (
                    RTCM_DESCRIPTIONS.get(
                        message_id,
                        "Other RTCM Message"
                    )
                )


                # ------------------------------------------------
                # Display target messages
                # ------------------------------------------------

                if message_id in TARGET_MESSAGES:

                    print(
                        f"[TARGET] "
                        f"{timestamp} | "
                        f"RTCM {message_id} | "
                        f"{description} | "
                        f"Count: {count}"
                    )

                else:

                    print(
                        f"[OTHER ] "
                        f"{timestamp} | "
                        f"RTCM {message_id} | "
                        f"{description} | "
                        f"Count: {count}"
                    )


                # ------------------------------------------------
                # Save to CSV
                # ------------------------------------------------

                save_message(
                    timestamp,
                    message_id,
                    count,
                    len(frame)
                )


        except socket.timeout:

            # ------------------------------------------------
            # This is NOT a fatal error.
            #
            # We use a short timeout so that the program
            # can continue sending GGA.
            # ------------------------------------------------

            continue


        except ConnectionResetError:

            print()
            print(
                "NTRIP connection was reset."
            )

            break


except KeyboardInterrupt:

    print()
    print()
    print("==========================================")
    print("MONITORING STOPPED")
    print("==========================================")


finally:

    running = False

    try:

        sock.close()

    except Exception:

        pass


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("==========================================")
    print("RTCM MESSAGE SUMMARY")
    print("==========================================")


    if message_counts:

        for message_id in sorted(
            message_counts
        ):

            count = message_counts[
                message_id
            ]

            if message_id in TARGET_MESSAGES:

                label = "TARGET"

            else:

                label = "OTHER"


            print(
                f"RTCM {message_id}: "
                f"{count} ({label})"
            )


    else:

        print(
            "No RTCM messages were decoded."
        )


    print()
    print(
        "Total RTCM bytes received:",
        total_bytes
    )


    print()
    print(
        "CSV saved at:"
    )

    print(
        os.path.abspath(RTCM_FILE)
    )


    print()
    print("==========================================")
    print("PROGRAM FINISHED")
    print("==========================================")