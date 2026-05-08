#!/usr/bin/env python3
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import subprocess
import threading
import time
import signal
import sys
from gpiozero import Button


# Global flag for temperature logging
stop_temp_logging = False


# Tilpass host/user hvis de er annerledes hos deg
NODES = [
    {"name": "cam1", "host": "192.168.1.10", "pi5_ip": "192.168.1.1", "user": "cameranode1", "port": 6001},
    {"name": "cam2", "host": "192.168.2.10", "pi5_ip": "192.168.2.1", "user": "cameranode2", "port": 6002},
    {"name": "cam3", "host": "192.168.3.10", "pi5_ip": "192.168.3.1", "user": "cameranode3", "port": 6003},
]

# GPIO trigger (change pin if needed)
TRIGGER_PIN = 17
trigger = Button(TRIGGER_PIN, pull_up=True, bounce_time=0.05)

# Streaming-innstillinger

BITRATE = 10_000_000

RECORD_DIR = Path.home() / "camerasystem/recordings"
RUN_TS = time.strftime("%Y%m%d_%H%M%S")

receiver_procs = []
receiver_files = {}
started_nodes = []

def choose_settings():
    print("🎥 Velg video-innstillinger:\n")
    print("1) 640x480 @ 30 fps")
    print("2) 1280x720 @ 30 fps")
    print("3) 1920x1080 @ 30 fps")
    print("4) Custom")

    choice = input("\nVelg (1-4): ")

    if choice == "1":
        return 640, 480, 30
    elif choice == "2":
        return 1280, 720, 30
    elif choice == "3":
        return 1920, 1080, 30
    elif choice == "4":
        w = int(input("Width: "))
        h = int(input("Height: "))
        fps = int(input("FPS: "))
        return w, h, fps
    else:
        print("Ugyldig valg, bruker default")
        return 640, 480, 30

def run(cmd, check=False, capture=False):
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
        stdout=subprocess.PIPE if not capture else subprocess.PIPE,
        stderr=subprocess.PIPE if not capture else subprocess.PIPE,
    )


def ping_reachable(node):
    cmd = [
        "ping",
        "-c", "1",
        "-W", "1",
        node["host"],
    ]
    result = run(cmd)
    return result.returncode == 0


def node_reachable(node):
    target = f'{node["user"]}@{node["host"]}'

    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=1",
        "-o", "ConnectionAttempts=1",
        target,
        "echo OK",
    ]

    result = run(cmd)
    return result.returncode == 0

def start_receiver(node):
    outdir = RECORD_DIR / RUN_TS
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f'{node["name"]}.mp4'

    cmd = f'nc -l {node["port"]} | ffmpeg -hide_banner -loglevel error -fflags nobuffer -flags low_delay -flush_packets 1 -analyzeduration 0 -probesize 32 -r {FRAMERATE} -i - -c copy -f mp4 -movflags +frag_keyframe+empty_moov "{outfile}"'
    proc = subprocess.Popen(["bash", "-lc", cmd])
    receiver_procs.append(proc)
    receiver_files[node["name"]] = outfile
    print(f"\n🎥 {node['name']} klar for opptak")


def start_remote_stream(node):
    target = f'{node["user"]}@{node["host"]}'
    remote_cmd = (
        "nohup bash -lc "
        f"\"rpicam-vid -t 0 "
        f"--width {WIDTH} --height {HEIGHT} "
        f"--bitrate {BITRATE} --framerate {FRAMERATE} "
        f"--codec h264 --inline --flush -n -o - "
        f"| nc {node['pi5_ip']} {node['port']}\" "
        f">/tmp/{node['name']}_stream.log 2>&1 &"
    )

    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=3",
        target,
        remote_cmd,
    ]
    result = run(cmd)
    if result.returncode == 0:
        started_nodes.append(node)
        print(f"\n▶️  {node['name']} streamer | {WIDTH}x{HEIGHT} @ {FRAMERATE} fps")
        return True

    print(f"❌ {node['name']} kunne ikke starte stream")
    return False


def stop_remote_stream(node):
    target = f'{node["user"]}@{node["host"]}'
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=3",
        target,
        "pkill -f rpicam-vid || true",
    ]
    run(cmd)


def show_bitrate_status(last_sizes, interval=1.0):
    parts = []

    for node in started_nodes:
        outfile = receiver_files.get(node["name"])
        if not outfile or not outfile.exists():
            parts.append(f"{node['name']}: 0.0 Mbps")
            continue

        current_size = outfile.stat().st_size
        previous_size = last_sizes.get(node["name"], current_size)
        bitrate_mbps = max(0.0, (current_size - previous_size) * 8 / interval / 1_000_000)
        last_sizes[node["name"]] = current_size
        parts.append(f"{node['name']}: {bitrate_mbps:.1f} Mbps")

    if parts:
        sys.stdout.write("\r📊 Bitrate | " + " | ".join(parts))
        sys.stdout.flush()


# --- Temperatur-logging funksjoner ---
def get_temp(ip, user):
    try:
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=2", f"{user}@{ip}", "vcgencmd measure_temp"],
            stderr=subprocess.DEVNULL
        )
        temp = out.decode().strip().replace("temp=", "").replace("'C", "")
        return float(temp)
    except:
        return None


def get_local_temp():
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"])
        return float(out.decode().split("=")[1].replace("'C", ""))
    except:
        return None


def temp_logger():
    logfile = RECORD_DIR / RUN_TS / "temp_log_live.csv"
    logfile.parent.mkdir(parents=True, exist_ok=True)

    with open(logfile, "w") as f:
        f.write("time,cam1,cam2,cam3,central\n")

        while not stop_temp_logging:
            t = time.strftime("%H:%M:%S")

            cam1 = get_temp("192.168.1.10", "cameranode1")
            cam2 = get_temp("192.168.2.10", "cameranode2")
            cam3 = get_temp("192.168.3.10", "cameranode3")
            central = get_local_temp()

            line = f"{t},{cam1},{cam2},{cam3},{central}\n"
            f.write(line)
            f.flush()

            print(f"\n🌡️ Temp | cam1:{cam1} cam2:{cam2} cam3:{cam3} central:{central}")

            time.sleep(5)


def cleanup(*_args):
    print("\n\n[Pi5] Stopper alle streams ...")

    global stop_temp_logging
    stop_temp_logging = True

    for node in started_nodes:
        stop_remote_stream(node)

    for proc in receiver_procs:
        if proc.poll() is None:
            proc.terminate()

    time.sleep(1)

    for proc in receiver_procs:
        if proc.poll() is None:
            proc.kill()

    print("[Pi5] Ferdig.")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGHUP, cleanup)

    print("🔎 Sjekker kameranoder... \n")

    reachable = []
    for node in NODES:
        if not ping_reachable(node):
            print(f"❌ {node['name']} ikke tilkoblet")
            continue

        if node_reachable(node):
            print(f"✅ {node['name']} tilkoblet (kamera OK)")
            reachable.append(node)
        else:
            print(f"⚠️  {node['name']} ingen kamera eller SSH feiler")

    if not reachable:
        print("❌ Ingen kameranoder funnet")
        return
# 👇 LEGG TIL HER
    global WIDTH, HEIGHT, FRAMERATE
    WIDTH, HEIGHT, FRAMERATE = choose_settings()

    print(f"\n👉 Valgt: {WIDTH}x{HEIGHT} @ {FRAMERATE} fps\n")

    print("⏳ Venter på trigger (GPIO)... (LOW = start, HIGH = stopp)")

    trigger.wait_for_press()
    print("🚀 Trigger mottatt! Starter opptak...")

    # Start streams after trigger

    for node in reachable:
        start_receiver(node)

    # Gi nc litt tid til å begynne å lytte
    time.sleep(1)

    for node in reachable:
        start_remote_stream(node)

    # Start temperatur-logging
    threading.Thread(target=temp_logger, daemon=True).start()

    print(f"\n🚀 Kameraopptak kjører | {WIDTH}x{HEIGHT} @ {FRAMERATE} fps (slipp GPIO for stopp)")

    last_sizes = {}

    while True:
        time.sleep(1)
        show_bitrate_status(last_sizes)

        # Stop if trigger released (goes HIGH again)
        if not trigger.is_pressed:
            print("\n🛑 Trigger sluppet – stopper opptak...")
            cleanup()


if __name__ == "__main__":
    main()
