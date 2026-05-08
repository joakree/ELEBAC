#!/usr/bin/env python3
# UiS Aerospace Camera system
# Central recording manager running on the Raspberry Pi 5
# Handles camera node control, video reception and system monitoring

 # Stop any old streaming processes left from previous sessions
def kill_existing_streams():
    print("\nCleaning old streams on all nodes...")

    for node in NODES:
        target = f"{node['user']}@{node['host']}"
        cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=3",
            target,
            # Stop both camera encoding and network streaming processes
            "pkill -f rpicam-vid || true; pkill -f nc || true"
        ]
        run(cmd)

    time.sleep(1)

# Standard libraries and GPIO handling
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



# Used to stop the monitoring thread during cleanup
stop_temp_logging = False


# Camera node configuration, static ip addresses and SSH credentials for each camera node
NODES = [
    {"name": "cam1", "host": "192.168.1.10", "pi5_ip": "192.168.1.1", "user": "cameranode1", "port": 6001},
    {"name": "cam2", "host": "192.168.2.10", "pi5_ip": "192.168.2.1", "user": "cameranode2", "port": 6002},
    {"name": "cam3", "host": "192.168.3.10", "pi5_ip": "192.168.3.1", "user": "cameranode3", "port": 6003},
]

# GPIO input from the flight computer
# Recording starts when the signal goes LOW
TRIGGER_PIN = 17
trigger = Button(TRIGGER_PIN, pull_up=True, bounce_time=0.05)

# Video streaming settings, can be limited if wanted
BITRATE = 100_000_000

RECORD_DIR = Path.home() / "camerasystem/recordings"
RUN_TS = time.strftime("%Y%m%d_%H%M%S")

receiver_procs = []
receiver_files = {}
started_nodes = []

 # Simple terminal menu for selecting recording settings for testing and demonstration purposes
def choose_settings():
    print("🎥 Velg video-innstillinger:\n")
    print("1) 640x480 @ 30 fps")
    print("2) 1280x720 @ 30 fps")
    print("3) 1920x1080 @ 30 fps (ANBEFALT)")
    print("4) 2028x1080 @ 20 fps (FULL SENSOR, 4:3)")
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
        return 2028, 1080, 30
    elif choice == "5":
        w = int(input("Width: "))
        h = int(input("Height: "))
        fps = int(input("FPS: "))
        return w, h, fps
    else:
        print("Ugyldig valg, bruker default (1080p)")
        return 1920, 1080, 30

# Wrapper for subprocess.run used throughout the script
def run(cmd, check=False, capture=False):
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture
    )


# Quick network check before attempting SSH connection
def ping_reachable(node):
    cmd = [
        "ping",
        "-c", "1",
        "-W", "1",
        node["host"],
    ]
    result = run(cmd)
    return result.returncode == 0


 # Verify that the remote camera node is reachable and that a camera is detected
def node_reachable(node):
    target = f'{node["user"]}@{node["host"]}'

    try:
        result = subprocess.run(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=5",
                target,
                # Query available cameras on the remote node
                "rpicam-vid --list-cameras"
            ],
            text=True,
            capture_output=True,
            timeout=6
        )

        # Debug output used during testing
        print(f"\nDEBUG {node['name']}:")
        print("returncode:", result.returncode)
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)

        if result.returncode != 0:
            return False

        output = result.stdout.lower()

        return "available cameras" in output and ":" in output

    except Exception as e:
        print(f"Error checking {node['name']}: {e}")
        return False

 # Start local ffmpeg receiver on the Pi5
 # Incoming H264 stream is saved directly to MP4
def start_receiver(node):
    outdir = RECORD_DIR / RUN_TS
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f'{node["name"]}.mp4'

    # Netcat listens for incoming H264 video stream,
    # and ffmpeg remuxes it into a fragmented MP4 container.
    # The fragmentation flags make the file streamable and more resilient
    # to interruptions.
    cmd = (
        f'nc -l {node["port"]} | '
        f'ffmpeg {FFMPEG_STREAM_FLAGS} -r {FRAMERATE} -i - '
        f'-c copy -f mp4 {MP4_MOVFLAGS} "{outfile}"'
    )
    proc = subprocess.Popen(["bash", "-lc", cmd])
    receiver_procs.append(proc)
    receiver_files[node["name"]] = outfile
    print(f"\n{node['name']} ready for recording")


 # Start H264 video streaming on the remote camera node
def start_remote_stream(node):
    target = f'{node["user"]}@{node["host"]}'
    remote_record_dir = "/home/" + node["user"] + "/recordings"
    remote_cmd = (
        # Hardware-encoded H264 video is streamed continuously
        "nohup bash -lc "
        f"\"rpicam-vid -t 0 "
        f"--width {WIDTH} --height {HEIGHT} "
        f"--bitrate {BITRATE} --framerate {FRAMERATE} "
        # Inline SPS/PPS headers improve stream recovery reliability
        f"--codec h264 --inline --flush -n -o - "
        # Save local MP4 backup while simultaneously streaming to the Pi5
        f"| ffmpeg -hide_banner -loglevel error -fflags nobuffer -flags low_delay -flush_packets 1 -analyzeduration 0 -probesize 32 -r {FRAMERATE} -i - -c copy -f mp4 -movflags +frag_keyframe+empty_moov {remote_record_dir}/{node['name']}.mp4 | nc {node['pi5_ip']} {node['port']} "
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
        print(f"\n{node['name']} streaming | {WIDTH}x{HEIGHT} @ {FRAMERATE} fps")
        return True

    print(f"{node['name']} could not start stream, retrying...")
    time.sleep(1)
    result = run(cmd)
    if result.returncode == 0:
        started_nodes.append(node)
        print(f"{node['name']} streaming (retry) | {WIDTH}x{HEIGHT} @ {FRAMERATE} fps")
        return True
    print(f"{node['name']} failed again on retry")
    return False


 # Stop remote camera streaming
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


 # Estimate bitrate based on file growth over time
def show_bitrate_status(last_sizes, interval=1.0):
    parts = []

    for node in started_nodes:
        outfile = receiver_files.get(node["name"])
        if not outfile or not outfile.exists():
            parts.append(f"{node['name']}: 0.0 Mbps")
            continue

        current_size = outfile.stat().st_size
        previous_size = last_sizes.get(node["name"], current_size)
        # Estimate current bitrate from file size growth over time
        bitrate_mbps = max(0.0, (current_size - previous_size) * 8 / interval / 1_000_000)
        last_sizes[node["name"]] = current_size
        parts.append(f"{node['name']}: {bitrate_mbps:.1f} Mbps")

    if parts:
        sys.stdout.write("\r📊 Bitrate | " + " | ".join(parts))
        sys.stdout.flush()


 # Monitoring and logging functions
 # Read CPU temperature from a remote camera node
def get_temp(ip, user):
    try:
        # vcgencmd is used to read Raspberry Pi system temperature
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=2", f"{user}@{ip}", "vcgencmd measure_temp"],
            stderr=subprocess.DEVNULL
        )
        temp = out.decode().strip().replace("temp=", "").replace("'C", "")
        return float(temp)
    except:
        return None


 # Read local Pi5 temperature
def get_local_temp():
    try:
        out = subprocess.check_output(["vcgencmd", "measure_temp"])
        return float(out.decode().split("=")[1].replace("'C", ""))
    except:
        return None



 # Read CPU load from a remote node
def get_cpu_load(ip, user):
    try:
        # Read Linux load average from the remote node
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=2", f"{user}@{ip}", "cat /proc/loadavg"],
            stderr=subprocess.DEVNULL
        )
        return float(out.decode().split()[0])
    except:
        return None


 # Read current CPU frequency from a remote node
def get_cpu_freq(ip, user):
    try:
        # Read ARM CPU clock frequency in Hz
        out = subprocess.check_output(
            ["ssh", "-o", "ConnectTimeout=2", f"{user}@{ip}", "vcgencmd measure_clock arm"],
            stderr=subprocess.DEVNULL
        )
        return int(out.decode().split("=")[1]) / 1_000_000
    except:
        return None

 # Check disk usage on the Pi5 storage device
def get_disk_usage():
    try:
        out = subprocess.check_output(["df", "/"]).decode().splitlines()[1]
        parts = out.split()
        return float(parts[4].replace("%", ""))  # percent used
    except:
        return None


 # Periodically log temperatures, CPU load, bitrate and disk usage
def temp_logger():
    logfile = RECORD_DIR / RUN_TS / "temp_log_live.csv"
    logfile.parent.mkdir(parents=True, exist_ok=True)

    with open(logfile, "w") as f:
        f.write("time,cam1,cam2,cam3,central,cpu1,cpu2,cpu3,freq1,freq2,freq3,br1,br2,br3,disk\n")

        last_sizes = {}

        # Continue monitoring until recording stops
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

            # Calculate approximate bitrate for each recording file
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
            # Flush immediately to avoid losing data during unexpected shutdown
            f.flush()

            print(f"\nTemp | cam1:{cam1} cam2:{cam2} cam3:{cam3} central:{central} | CPU:{cpu1},{cpu2},{cpu3} | Freq:{freq1},{freq2},{freq3} | BR:{bitrates} | Disk:{disk}%")

            time.sleep(5)


 # Gracefully stop all running streams and background processes
def cleanup(*_args):
    print("\n\n[Pi5] Stopping all streams ...")

    global stop_temp_logging
    stop_temp_logging = True

    for node in started_nodes:
        stop_remote_stream(node)

    for proc in receiver_procs:
        if proc.poll() is None:
            # Attempt graceful shutdown before force killing processes
            proc.terminate()

    time.sleep(1)

    for proc in receiver_procs:
        if proc.poll() is None:
            # Force termination if the process is still running
            proc.kill()

    print("[Pi5] Done.")
    sys.exit(0)


 # Main program flow
def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGHUP, cleanup)

    print("Checking camera nodes... \n")

    reachable = []
    for node in NODES:
        if not ping_reachable(node):
            print(f"{node['name']} not reachable")
            continue

        if node_reachable(node):
            print(f"{node['name']} connected (camera OK)")
            reachable.append(node)
        else:
            print(f"{node['name']} camera not detected or SSH failed")

    if not reachable:
        print("No camera nodes found")
        return

    # Remove leftover streaming processes before starting a new session
    kill_existing_streams()

    global WIDTH, HEIGHT, FRAMERATE
    WIDTH, HEIGHT, FRAMERATE = choose_settings()

    print(f"\nSelected: {WIDTH}x{HEIGHT} @ {FRAMERATE} fps\n")

    print("Waiting for GPIO trigger... (LOW = start, HIGH = stop)")

    # Wait for launch trigger from the flight computer
    trigger.wait_for_press()
    print("Trigger received! Starting recording...")

    # Prepare local receivers before enabling remote streams
    for node in reachable:
        start_receiver(node)

    # Give netcat enough time to start listening
    time.sleep(4)

    # Start streams sequentially to avoid race conditions
    for node in reachable:
        start_remote_stream(node)
        time.sleep(0.5)

    # Monitoring runs in a separate background thread
    threading.Thread(target=temp_logger, daemon=True).start()

    print(f"\nRecording active | {WIDTH}x{HEIGHT} @ {FRAMERATE} fps (release GPIO to stop)")

    last_sizes = {}

    while True:
        time.sleep(1)
        # Continuously display estimated live bitrate for each stream
        show_bitrate_status(last_sizes)

        # Stop recording when the trigger signal returns HIGH
        if not trigger.is_pressed:
            print("\nTrigger released - stopping recording...")
            cleanup()


if __name__ == "__main__":
    main()
