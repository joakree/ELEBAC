#!/usr/bin/env python3

def kill_existing_streams():
    print("\n🧹 Rydder gamle streams på alle noder...")

    for node in NODES:
        target = f"{node['user']}@{node['host']}"
        cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=3",
            target,
            "pkill -f rpicam-vid || true; pkill -f nc || true"
        ]
        run(cmd)

    time.sleep(1)
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

BITRATE = 100_000_000

RECORD_DIR = Path.home() / "camerasystem/recordings"
RUN_TS = time.strftime("%Y%m%d_%H%M%S")

receiver_procs = []
receiver_files = {}
started_nodes = []

def choose_settings():
    print("🎥 Velg video-innstillinger:\n")
    print("1) 640x480 @ 30 fps")
    print("2) 1280x720 @ 30 fps")
    print("3) 1920x1080 @ 30 fps (ANBEFALT)")
    print("4) 2028x1520 @ 20 fps (FULL SENSOR, 4:3)")
    print("5) Custom")
    choice = input("\nVelg (1-5): ")

    if choice == "1":
        return 640, 480, 30
    elif choice == "2":
        return 1280, 720, 30
    elif choice == "3":
        return 1920, 1080, 30
    elif choice == "4":
        print("⚠️  4:3 mode – større synsfelt (ingen cropping)")
        return 2028, 1520, 30
    elif choice == "5":
        w = int(input("Width: "))
        h = int(input("Height: "))
        fps = int(input("FPS: "))
        return w, h, fps
    else:
        print("Ugyldig valg, bruker default (1080p)")
        return 1920, 1080, 30

def run(cmd, check=False, capture=False):
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture
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

    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=5",
                target,
                "rpicam-vid --list-cameras"
            ],
            text=True,
            capture_output=True,
            timeout=6
        )

        print(f"\nDEBUG {node['name']}:")
        print("returncode:", result.returncode)
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)

        if result.returncode != 0:
            return False

        output = result.stdout.lower()

        return "available cameras" in output and ":" in output

    except Exception as e:
        print(f"❌ Error checking {node['name']}: {e}")
        return False

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

    print(f"❌ {node['name']} kunne ikke starte stream, prøver igjen...")
    time.sleep(1)
    result = run(cmd)
    if result.returncode == 0:
        started_nodes.append(node)
        print(f"▶️  {node['name']} streamer (retry) | {WIDTH}x{HEIGHT} @ {FRAMERATE} fps")
        return True
    print(f"❌ {node['name']} feilet også på retry")
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



def get_cpu_load(ip, user):
    try:
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=2", f"{user}@{ip}", "cat /proc/loadavg"],
            stderr=subprocess.DEVNULL
        )
        return float(out.decode().split()[0])
    except:
        return None


def get_cpu_freq(ip, user):
    try:
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=2", f"{user}@{ip}", "vcgencmd measure_clock arm"],
            stderr=subprocess.DEVNULL
        )
        return int(out.decode().split("=")[1]) / 1_000_000
    except:
        return None

def get_disk_usage():
    try:
        out = subprocess.check_output(["df", "/"]).decode().splitlines()[1]
        parts = out.split()
        return float(parts[4].replace("%", ""))  # percent used
    except:
        return None


def temp_logger():
    logfile = RECORD_DIR / RUN_TS / "temp_log_live.csv"
    logfile.parent.mkdir(parents=True, exist_ok=True)

    with open(logfile, "w") as f:
        f.write("time,cam1,cam2,cam3,central,cpu1,cpu2,cpu3,freq1,freq2,freq3,br1,br2,br3,disk\n")

        last_sizes = {}

        while not stop_temp_logging:
            t = time.strftime("%H:%M:%S")

            cam1 = get_temp("192.168.1.10", "cameranode1")
            cam2 = get_temp("192.168.2.10", "cameranode2")
            cam3 = get_temp("192.168.3.10", "cameranode3")
            central = get_local_temp()

            cpu1 = get_cpu_load("192.168.1.10", "cameranode1")
            cpu2 = get_cpu_load("192.168.2.10", "cameranode2")
            cpu3 = get_cpu_load("192.168.3.10", "cameranode3")

            freq1 = get_cpu_freq("192.168.1.10", "cameranode1")
            freq2 = get_cpu_freq("192.168.2.10", "cameranode2")
            freq3 = get_cpu_freq("192.168.3.10", "cameranode3")

            bitrates = []
            for node in NODES:
                outfile = receiver_files.get(node["name"])
                if not outfile or not outfile.exists():
                    bitrates.append(None)
                    continue

                current_size = outfile.stat().st_size
                prev = last_sizes.get(node["name"], current_size)
                br = (current_size - prev) * 8 / 5 / 1_000_000
                last_sizes[node["name"]] = current_size
                bitrates.append(br)

            disk = get_disk_usage()

            line = f"{t},{cam1},{cam2},{cam3},{central},{cpu1},{cpu2},{cpu3},{freq1},{freq2},{freq3},{bitrates[0]},{bitrates[1]},{bitrates[2]},{disk}\n"
            f.write(line)
            f.flush()

            print(f"\n🌡️ Temp | cam1:{cam1} cam2:{cam2} cam3:{cam3} central:{central} | CPU:{cpu1},{cpu2},{cpu3} | Freq:{freq1},{freq2},{freq3} | BR:{bitrates} | Disk:{disk}%")

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

    # Rydd gamle streams etter at noder er bekreftet OK
    kill_existing_streams()

    global WIDTH, HEIGHT, FRAMERATE
    WIDTH, HEIGHT, FRAMERATE = choose_settings()

    print(f"\n👉 Valgt: {WIDTH}x{HEIGHT} @ {FRAMERATE} fps\n")

    print("⏳ Venter på trigger (GPIO)... (LOW = start, HIGH = stopp)")

    trigger.wait_for_press()
    print("🚀 Trigger mottatt! Starter opptak...")

    # Start streams after trigger

    for node in reachable:
        start_receiver(node)

    # Gi nc god tid til å begynne å lytte
    time.sleep(4)

    # Start streams sekvensielt (unngå race condition)
    for node in reachable:
        start_remote_stream(node)
        time.sleep(0.5)

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
