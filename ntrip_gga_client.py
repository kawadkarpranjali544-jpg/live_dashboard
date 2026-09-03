import socket
import base64
import csv
import time

# ============================================================
# NTRIP SETTINGS
# ============================================================

NTRIP_HOST = "caster.in-staging-all-freq-01.ce.swiftnav.com"
NTRIP_PORT = 2101
MOUNTPOINT = "MSM5"

USERNAME = "airtel.staging.demo"
PASSWORD = "0krqz6atb25q"

GGA_FILE = "gga_log.csv"


# ============================================================
# READ RECORDED GGA
# ============================================================

def get_gga():

    with open(
        GGA_FILE,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        reader = csv.reader(file)

        # Skip CSV header
        next(reader, None)

        for row in reader:

            if len(row) < 2:
                continue

            message = ",".join(row[1:]).strip()

            if "$GNGGA" in message or "$GPGGA" in message:

                return message

    return None


# ============================================================
# GET RECORDED GGA
# ============================================================

gga = get_gga()

if not gga:

    print("ERROR: No GGA message found in gga_log.csv")
    raise SystemExit

print("------------------------------------------")
print("Recorded GGA found:")
print(gga)
print("------------------------------------------")


# ============================================================
# CONNECT TO NTRIP CASTER
# ============================================================

print("Connecting to NTRIP caster...")

try:

    sock = socket.create_connection(
        (NTRIP_HOST, NTRIP_PORT),
        timeout=10
    )

    print("TCP connection established.")

except Exception as e:

    print("NTRIP connection failed:")
    print(e)
    raise SystemExit


# ============================================================
# NTRIP AUTHENTICATION
# ============================================================

credentials = (
    USERNAME + ":" + PASSWORD
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
    f"User-Agent: NTRIP PythonClient/1.0\r\n"
    f"Authorization: Basic {auth}\r\n"
    f"Ntrip-Version: Ntrip/2.0\r\n"
    f"\r\n"
)

sock.sendall(request.encode())


# ============================================================
# READ SERVER RESPONSE
# ============================================================

response = sock.recv(4096)

print("\nNTRIP server response:")
print(response[:500])


# ============================================================
# CHECK CONNECTION
# ============================================================

if b"200 OK" in response:

    print("\n==========================================")
    print("NTRIP CONNECTION SUCCESSFUL")
    print("==========================================")

else:

    print("\nNTRIP connection was not successful.")
    print("Check username, password and mountpoint.")

    sock.close()
    raise SystemExit


# ============================================================
# SEND RECORDED GGA
# ============================================================

print("\nSending recorded GGA to NTRIP caster...")

gga_message = gga + "\r\n"

sock.sendall(
    gga_message.encode()
)

print("Recorded GGA sent successfully.")


# ============================================================
# RECEIVE RTCM STREAM
# ============================================================

print("\nWaiting for RTCM correction stream...")
print("Press Ctrl+C to stop.")
print("------------------------------------------")

total_bytes = 0

try:

    while True:

        data = sock.recv(4096)

        if not data:

            print("NTRIP server closed the connection.")
            break

        total_bytes += len(data)

        print(
            "RTCM data received:",
            len(data),
            "bytes | Total:",
            total_bytes,
            "bytes"
        )

except KeyboardInterrupt:

    print("\nStopped by user.")

finally:

    sock.close()

    print("------------------------------------------")
    print("NTRIP connection closed.")