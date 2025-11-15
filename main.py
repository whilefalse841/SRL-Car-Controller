#!/usr/bin/env python3
import argparse
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import pygame
from bleak import BleakClient
import sys
import tkinter as tk
from tkinter import messagebox
from bleak import BleakScanner

import os
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"

# Strings to match in Bluetooth device names (case-insensitive substring match)
ALLOWED_NAME_FILTERS = [
    "12CILINDRI", "12Cilindri", "SL-12Cilindri",
    "296GT3", "296 GT3", "SL-296 GT3",
    "296GTB", "296 GTB", "SL-296 GTB",
    "330P", "330 P 1965", "---",
    "330P4", "330 P4", "SL-330 P4(1967)",
    "488EVO", "488 Challenge Evo", "SL-488 Challenge Evo",
    "488GTE", "488 GTE - AF Corse #51 2019", "SL-488 GTE",
    "499P", "499 P", "SL-499P",
    "499P(2024)", "499P(2024)", "SL-499P N",
    "512S", "512 S 1970", "---",
    "DaytonaSP3", "Daytona SP3", "SL-Daytona SP3",
    "F175", "F1-75", "SL-F1-75",
    "FXXK", "FXX-K EVO", "SL-FXX-K Evo",
    "PUROSANGUE", "Purosangue", "SL-Purosangue",
    "SF1000", "SF1000 - Tuscan GP - Ferrari 1000", "SL-SF1000",
    "SF23", "SF-23", "SL-SF-23",
    "SF24", "SF-24", "SL-SF-24",
    "SF90SPIDER", "SF90 Spider", "SL-SF90 Spider",
    "SF90SPIDER(BLACK)", "SF90 Spider (Black)", "SL-SF90 Spider N",
    "ShellCar", "(string vazia)", "SL-Shell Car"
]

SELECTED_DEVICE_NAME = ""
SELECTED_CONTROLLER_ID = 0

import threading


def center_window(win: tk.Tk, width: int, height: int) -> None:
    win.update_idletasks()
    screen_w = win.winfo_screenwidth()
    screen_h = win.winfo_screenheight()
    x = int((screen_w / 2) - (width / 2))
    y = int((screen_h / 2) - (height / 2))
    win.geometry(f"{width}x{height}+{x}+{y}")


def pick_bluetooth_device() -> str:
    """
    Runs BleakScanner.discover() in a background thread and keeps a Tk "please wait"
    window responsive in the main thread. Polls for completion via after().
    """
    global SELECTED_DEVICE_NAME

    devices_result = []
    scan_exception = {"exc": None}
    scan_thread = None
    scan_done = {"done": False}

    def scan_devices():
        # run Bleak discovery in a fresh event loop inside this thread
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            devices = loop.run_until_complete(BleakScanner.discover(timeout=3))
            devices_result.extend(devices)
        except Exception as e:
            scan_exception["exc"] = e
        finally:
            try:
                loop.stop()
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass
            scan_done["done"] = True

    # Create "Please wait" popup on main thread
    wait_root = tk.Tk()
    wait_root.title("Searching for Devices")
    center_window(wait_root, 320, 110)
    label = tk.Label(wait_root, text="Please wait...\nScanning for Bluetooth devices", font=("Segoe UI", 12), justify="center")
    label.pack(expand=True, padx=12, pady=10)
    wait_root.update()

    # Start scanner thread
    scan_thread = threading.Thread(target=scan_devices, daemon=True)
    scan_thread.start()

    # Poll for completion safely using after()
    def poll():
        if scan_done["done"]:
            wait_root.quit()
            return
        wait_root.after(100, poll)

    wait_root.after(100, poll)
    wait_root.mainloop()
    try:
        wait_root.destroy()
    except Exception:
        pass

    # If scanning raised an exception, show it
    if scan_exception["exc"] is not None:
        messagebox.showerror("Scan Error", f"Bluetooth scan failed: {scan_exception['exc']}")
        sys.exit(1)

    devices = devices_result

    # Filter matching devices
    filtered = [d for d in devices if any(f.lower() in (d.name or "").lower() for f in ALLOWED_NAME_FILTERS)]

    if not filtered:
        messagebox.showerror("No Matching Devices", "No Compatible Cars found")
        sys.exit(1)

    # Selection window (main thread only)
    root = tk.Tk()
    root.title("Select Bluetooth Device")
    center_window(root, 240, 340)

    tk.Label(root, text="Select a car:", font=("Segoe UI", 16)).pack(pady=10)
    listbox = tk.Listbox(root, width=60, height=10)
    listbox.pack(padx=10, pady=10, expand=True, fill="both")

    device_map = {}
    for d in filtered:
        name = " "+d.name or "Unknown"
        display = f"{name} ({d.address})"
        listbox.insert(tk.END, display)
        device_map[display] = (name, d.address)

    selected = {"address": None}

    def on_select():
        try:
            choice = listbox.get(listbox.curselection())
            name, addr = device_map[choice]
            selected["address"] = addr
            global SELECTED_DEVICE_NAME
            SELECTED_DEVICE_NAME = name
            root.destroy()
        except Exception:
            messagebox.showwarning("Selection Error", "Please select a device first.")

    btn = tk.Button(root, text="Connect", command=on_select)
    btn.pack(pady=10)
    root.mainloop()

    if not selected["address"]:
        sys.exit(0)

    return selected["address"]


CONTROL_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
CONTROL_CHARACTERISTIC_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
STATUS_CHARACTERISTIC_UUID = "0000fff2-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_CHARACTERISTIC_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

QueueItem = Tuple[str, Optional[object]]


@dataclass
class ControlState:
    mode: int = 1
    throttle: int = 0
    steering: int = 0
    lights: bool = False
    turbo: bool = False
    donut: bool = False
    battery_pct: Optional[int] = None
    last_payload: bytes = b""
    last_status: Dict[str, int] = field(default_factory=dict)
    last_status_hex: str = ""
    message: str = ""


def build_control_payload(state: ControlState) -> bytes:
    return bytes(
        [
            state.mode & 0xFF,
            1 if state.throttle > 0 else 0,
            1 if state.throttle < 0 else 0,
            1 if state.steering < 0 else 0,
            1 if state.steering > 0 else 0,
            int(state.lights),
            int(state.turbo),
            int(state.donut),
        ]
    )


def decode_status_payload(data: bytes) -> Dict[str, int]:
    length = len(data)
    if length == 1:
        return {"length": length, "battery_pct": data[0]}
    if length == 8:
        return {
            "length": length,
            "mode": data[0],
            "forward": data[1],
            "reverse": data[2],
            "left": data[3],
            "right": data[4],
            "lights": data[5],
            "turbo": data[6],
            "donut": data[7],
        }
    return {"length": length, "raw": data.hex()}


def throttle_label(value: int) -> str:
    if value > 0:
        return "Forward"
    if value < 0:
        return "Reverse"
    return "Stopped"


def steering_label(value: int) -> str:
    if value < 0:
        return "Left"
    if value > 0:
        return "Right"
    return "Straight"

class ControlRateLimiter:
    """Ensures control packets are not sent too frequently."""
    def __init__(self, min_interval: float = 0.1):
        self._last_payload: Optional[bytes] = None
        self._last_time: float = 0.0
        self.min_interval = min_interval

    def should_send(self, payload: bytes) -> bool:
        import time
        now = time.monotonic()
        if payload != self._last_payload or (now - self._last_time) >= self.min_interval:
            self._last_payload = payload
            self._last_time = now
            return True
        return False

class BleController:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        address: str,
        state: ControlState,
        ui_queue: "asyncio.Queue[QueueItem]",
    ) -> None:  # ← this closes the parameter list
        self.loop = loop
        self.address = address
        self.state = state
        self.ui_queue = ui_queue
        self._client: Optional[BleakClient] = None
        self._status_notify = False
        self._battery_notify = False
        self._stop_event = asyncio.Event()
        self._write_lock = asyncio.Lock()
        self._pending_payload: Optional[bytes] = None
        self._last_sent_payload: Optional[bytes] = None
        self._stopped = False

        # Added bandwidth optimization helpers
        self._rate_limiter = ControlRateLimiter(0.1)  # 10Hz max BLE write rate
        self._last_battery = None
        self._last_status_hex = ""


    async def run(self) -> None:
        self._queue_ui(("message", f"Connecting to {self.address}..."))
        try:
            async with BleakClient(self.address, timeout=45.0) as client:
                self._client = client
                self._queue_ui(("connected", None))
                await self._enable_notifications(client)
                await self._send_pending()
                await self._read_battery(client)
                await self._stop_event.wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - best effort logging
            self._queue_ui(("error", f"Connection error: {exc}"))
        finally:
            try:
                await self._disable_notifications()
            except Exception:
                pass
            self._client = None
            self._queue_ui(("disconnected", None))

    async def _enable_notifications(self, client: BleakClient) -> None:
        try:
            await client.start_notify(STATUS_CHARACTERISTIC_UUID, self._status_handler)
            self._status_notify = True
        except Exception as exc:
            self._queue_ui(("warn", f"Status notify failed: {exc}"))
        try:
            await client.start_notify(BATTERY_CHARACTERISTIC_UUID, self._battery_handler)
            self._battery_notify = True
        except Exception as exc:
            self._queue_ui(("warn", f"Battery notify failed: {exc}"))

    async def _disable_notifications(self) -> None:
        client = self._client
        if not client:
            return
        if self._status_notify:
            try:
                await client.stop_notify(STATUS_CHARACTERISTIC_UUID)
            except Exception:
                pass
            finally:
                self._status_notify = False
        if self._battery_notify:
            try:
                await client.stop_notify(BATTERY_CHARACTERISTIC_UUID)
            except Exception:
                pass
            finally:
                self._battery_notify = False

    def _status_handler(self, _: int, data: bytearray) -> None:
        payload = bytes(data)
        hex_data = payload.hex()
        if hex_data == self._last_status_hex:
            return
        self._last_status_hex = hex_data
        decoded = decode_status_payload(payload)
        self.state.last_status = decoded
        self.state.last_status_hex = hex_data
        self._queue_ui(("status", None))


    def _battery_handler(self, _: int, data: bytearray) -> None:
        payload = bytes(data)
        if not payload:
            return
        val = int(payload[0])
        if val == self._last_battery:
            return
        self._last_battery = val
        self.state.battery_pct = val
        self._queue_ui(("battery", val))


    async def _read_battery(self, client: BleakClient) -> None:
        try:
            data = await client.read_gatt_char(BATTERY_CHARACTERISTIC_UUID)
        except Exception as exc:
            self._queue_ui(("warn", f"Initial battery read failed: {exc}"))
            return
        if data:
            self.state.battery_pct = int(data[0])
            self._queue_ui(("battery", int(data[0])))

    async def send_control(self, payload: bytes) -> None:
        if self._stopped or not self._client:
            return
        if not self._rate_limiter.should_send(payload):
            return
        async with self._write_lock:
            try:
                await self._client.write_gatt_char(
                    CONTROL_CHARACTERISTIC_UUID,
                    payload,
                    response=False,
                )
                self._last_sent_payload = payload
                self.state.last_payload = payload
                self._queue_ui(("payload", payload))
            except Exception as exc:
                self._queue_ui(("error", f"ERROR sending command: {exc}"))


    async def _write_pending(self) -> None:
        if not self._client:
            return
        async with self._write_lock:
            while self._pending_payload is not None and self._client:
                payload = self._pending_payload
                self._pending_payload = None
                try:
                    await self._client.write_gatt_char(
                        CONTROL_CHARACTERISTIC_UUID,
                        payload,
                        response=False,
                    )
                except Exception as exc:
                    self._queue_ui(("error", f"ERROR sending command: {exc}"))
                    break
                self._last_sent_payload = payload
                self.state.last_payload = payload
                self._queue_ui(("payload", payload))

    async def request_battery(self) -> None:
        if self._stopped:
            return
        if not self._client:
            self._queue_ui(("message", "Battery read queued; waiting for connection"))
            return
        await self._read_battery(self._client)

    async def _send_pending(self) -> None:
        if self._pending_payload is not None and self._client:
            await self._write_pending()

    async def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._stop_event.set()
        await self._disable_notifications()

    def _queue_ui(self, item: QueueItem) -> None:
        try:
            self.ui_queue.put_nowait(item)
        except asyncio.QueueFull:
            pass


class PygameApp:
    BG_COLOR = (36, 0, 0)
    TEXT_COLOR = (224, 224, 224)
    ACCENT_COLOR = (251, 206, 7)

    def __init__(self, loop: asyncio.AbstractEventLoop, address: str) -> None:
        self.loop = loop
        self.address = address
        self.state = ControlState()
        self.ui_queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        self.ble = BleController(loop, address, self.state, self.ui_queue)

        self.running = False
        self.message = ""

        self.throttle_keys_down: set[str] = set()
        self.steering_keys_down: set[str] = set()
        self.toggle_keys_down: set[str] = set()
        self.last_throttle_key: Optional[str] = None
        self.last_steering_key: Optional[str] = None

        self.screen: Optional[pygame.Surface] = None
        self.font: Optional[pygame.font.Font] = None
        self.small_font: Optional[pygame.font.Font] = None

        # Initialize gamepad (joystick) support
        pygame.joystick.init()
        self.gamepad = None
        self._init_gamepad(SELECTED_CONTROLLER_ID)

    def _init_gamepad(self, index: int) -> None:
        """
        Initialize or re-initialize the active gamepad safely.
        """
        global SELECTED_CONTROLLER_ID
        try:
            count = pygame.joystick.get_count()
        except Exception:
            count = 0
        if count == 0:
            # no controllers available
            try:
                if self.gamepad:
                    self.gamepad.quit()
            except Exception:
                pass
            self.gamepad = None
            self.state.message = "No controllers detected"
            return
        # wrap index
        idx = int(index) % count
        SELECTED_CONTROLLER_ID = idx
        try:
            # try to de-init old gamepad safely
            if self.gamepad and getattr(self.gamepad, "get_instance_id", None) is not None:
                try:
                    self.gamepad.quit()
                except Exception:
                    pass
            self.gamepad = pygame.joystick.Joystick(idx)
            self.gamepad.init()
            name = None
            try:
                name = self.gamepad.get_name()
            except Exception:
                name = "Unknown"
            self.state.message = f"Using gamepad {idx + 1}: {name}"
        except Exception as e:
            self.gamepad = None
            self.state.message = f"Gamepad init failed: {e}"

    async def run(self) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Shell Racing Legends Controller (pygame)")
        self.screen = pygame.display.set_mode((720, 420))
        self.font = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.small_font = pygame.font.SysFont("Segoe UI", 16, bold=True)
        pygame.key.set_repeat(0)

        ble_task = asyncio.create_task(self.ble.run())
        ui_task = asyncio.create_task(self.ui_consumer())

        try:
            await self.mainloop()
        finally:
            await self.shutdown()
            await asyncio.gather(ble_task, return_exceptions=True)
            # notify ui consumer to exit
            try:
                self.ui_queue.put_nowait(("shutdown", None))
            except Exception:
                pass
            await asyncio.gather(ui_task, return_exceptions=True)
            pygame.quit()

    async def mainloop(self) -> None:
        self.running = True
        clock = pygame.time.Clock()

        # reset the steering state
        self.state.steering = 0
        # reset the throttle state
        self.state.throttle = 0

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.loop.create_task(self.shutdown())
                elif event.type == pygame.KEYDOWN:
                    self.handle_keydown(event)
                elif event.type == pygame.KEYUP:
                    self.handle_keyup(event)
                # Check gamepad events (button presses)
                if event.type == pygame.JOYBUTTONDOWN:
                    self.handle_gamepad_buttondown(event)
                elif event.type == pygame.JOYBUTTONUP:
                    self.handle_gamepad_buttonup(event)

            # Update throttle and steering from the gamepad axis (if available)
            try:
                if self.gamepad:
                    self.update_gamepad_controls()
            except Exception:
                # defensive: if gamepad throws, re-init safely
                self._init_gamepad(SELECTED_CONTROLLER_ID)

            self.draw()
            await asyncio.sleep(0)
            clock.tick(60)

    def update_gamepad_controls(self) -> None:
        if not self.gamepad:
            return
        try:
            throttle = self.gamepad.get_axis(3)  # -1 for reverse, 1 for forward
        except Exception:
            throttle = 0
        try:
            steering = self.gamepad.get_axis(0)
        except Exception:
            steering = 0
        try:
            turboAxis0 = self.gamepad.get_axis(5)
        except Exception:
            turboAxis0 = 1.0
        try:
            turboAxis1 = self.gamepad.get_axis(4)
        except Exception:
            turboAxis1 = 1.0

        self.state.throttle = 0

        if throttle < -0.5:
            self.state.throttle = 1  
        elif throttle > 0.5:
            self.state.throttle = -1  

        # Button-based throttle fallback
        try:
            buttonInput = 0
            if self.gamepad.get_button(1):  # Button B
                buttonInput -= 1
            elif self.gamepad.get_button(0):  # Button A
                buttonInput += 1

            if buttonInput != 0:
                self.state.throttle = buttonInput
        except Exception:
            pass

        self.state.steering = 0
        if steering < -0.5:
            self.state.steering = -1
        elif steering > 0.5:
            self.state.steering = 1

        self.state.turbo = 0
        if turboAxis0 > -0.5 or turboAxis1 > -0.5:
            self.state.turbo = 1

        # Update the control payload with the new state (fire-and-forget)
        try:
            payload = build_control_payload(self.state)
            self.loop.create_task(self.ble.send_control(payload))

        except Exception:
            pass

    def handle_gamepad_buttondown(self, event: pygame.event.Event) -> None:
        # Example: button 0 is "A" on Xbox controllers, or "Cross" on PlayStation controllers
        try:
            if event.button == 6:  # BACK
                self.state.lights = not self.state.lights
                self.state.message = f"Lights {'ON' if self.state.lights else 'OFF'}"
                self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        except Exception:
            pass

    def handle_gamepad_buttonup(self, event: pygame.event.Event) -> None:
        pass

    def handle_keydown(self, event: pygame.event.Event) -> None:
        if not self.running:
            return
        key_name = pygame.key.name(event.key).lower()
        if key_name in {"w", "s"}:
            self.throttle_keys_down.add(key_name)
            self.last_throttle_key = key_name
            if self._update_throttle_from_keys():
                self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        elif key_name in {"a", "d"}:
            self.steering_keys_down.add(key_name)
            self.last_steering_key = key_name
            if self._update_steering_from_keys():
                self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        elif key_name in {"l", "t", "o", "m", "b", "q"}:
            if key_name not in self.toggle_keys_down:
                self.toggle_keys_down.add(key_name)
                self._handle_toggle_press(key_name)

        # controller slot switching via + / -
        global SELECTED_CONTROLLER_ID
        if key_name in {"+", "=", "kp_plus"}:
            try:
                count = pygame.joystick.get_count()
            except Exception:
                count = 0
            if count > 0:
                SELECTED_CONTROLLER_ID = (SELECTED_CONTROLLER_ID + 1) % count
                self._init_gamepad(SELECTED_CONTROLLER_ID)
        elif key_name in {"-", "_", "kp_minus"}:
            try:
                count = pygame.joystick.get_count()
            except Exception:
                count = 0
            if count > 0:
                SELECTED_CONTROLLER_ID = (SELECTED_CONTROLLER_ID - 1) % count
                self._init_gamepad(SELECTED_CONTROLLER_ID)

    def handle_keyup(self, event: pygame.event.Event) -> None:
        key_name = pygame.key.name(event.key).lower()
        if key_name in self.throttle_keys_down:
            self.throttle_keys_down.discard(key_name)
            if self._update_throttle_from_keys():
                self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        elif key_name in self.steering_keys_down:
            self.steering_keys_down.discard(key_name)
            if self._update_steering_from_keys():
                self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        if key_name in self.toggle_keys_down:
            self.toggle_keys_down.discard(key_name)

    def _update_throttle_from_keys(self) -> bool:
        old = self.state.throttle
        new_value = 0

        if "w" in self.throttle_keys_down and "s" in self.throttle_keys_down:
            new_value = 1 if self.last_throttle_key == "w" else -1
        elif "w" in self.throttle_keys_down:
            new_value = 1
        elif "s" in self.throttle_keys_down:
            new_value = -1
        if new_value != old:
            self.state.throttle = new_value
            self.state.message = throttle_label(new_value)
            return True
        return False

    def _update_steering_from_keys(self) -> bool:
        old = self.state.steering
        new_value = 0

        if "a" in self.steering_keys_down and "d" in self.steering_keys_down:
            new_value = -1 if self.last_steering_key == "a" else 1
        elif "a" in self.steering_keys_down:
            new_value = -1
        elif "d" in self.steering_keys_down:
            new_value = 1
        if new_value != old:
            self.state.steering = new_value
            self.state.message = steering_label(new_value)
            return True
        return False

    def _handle_toggle_press(self, key_name: str) -> None:
        if key_name == "l":
            self.state.lights = not self.state.lights
            self.state.message = f"Lights {'ON' if self.state.lights else 'OFF'}"
            self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        elif key_name == "t":
            self.state.turbo = not self.state.turbo
            self.state.message = f"Turbo {'ON' if self.state.turbo else 'OFF'}"
            self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        elif key_name == "o":
            self.state.donut = not self.state.donut
            self.state.message = f"Donut {'ON' if self.state.donut else 'OFF'}"
            self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        elif key_name == "m":
            self.state.mode = 2 if self.state.mode == 1 else 1
            self.state.message = f"Mode set to {self.state.mode}"
            self.loop.create_task(self.ble.send_control(build_control_payload(self.state)))
        elif key_name == "b":
            self.state.message = "Battery refresh requested"
            self.loop.create_task(self.ble.request_battery())
        elif key_name == "q":
            self.loop.create_task(self.shutdown())

    async def ui_consumer(self) -> None:
        while True:
            kind, data = await self.ui_queue.get()
            if kind == "shutdown":
                break
            self._handle_ui_message(kind, data)

    def _handle_ui_message(self, kind: str, data: Optional[object]) -> None:
        if kind == "message":
            self.message = str(data)
        elif kind == "warn":
            self.message = f"WARN: {data}"
        elif kind == "error":
            self.message = f"ERROR: {data}"
        elif kind == "battery":
            self.state.battery_pct = int(data)
            self.message = f"Battery: {data}%"
        elif kind == "status":
            self.message = "Status notification received"
        elif kind == "payload":
            payload = data if isinstance(data, bytes) else b""
            self.state.last_payload = payload
            self.message = f"Command sent: {payload.hex() if payload else '--'}"
        elif kind == "connected":
            self.message = "Connected"
        elif kind == "disconnected":
            if self.running:
                self.message = "Disconnected"

    async def shutdown(self) -> None:
        if not self.running:
            return
        self.running = False
        self.throttle_keys_down.clear()
        self.steering_keys_down.clear()
        self.toggle_keys_down.clear()
        self.state.throttle = 0
        self.state.steering = 0
        try:
            await self.ble.send_control(build_control_payload(self.state))
        except Exception:
            pass
        try:
            await self.ble.stop()
        except Exception:
            pass

    def draw(self) -> None:
        if not self.screen or not self.font or not self.small_font:
            return
        self.screen.fill(self.BG_COLOR)

        try:
            gp_name = self.gamepad.get_name() if self.gamepad else "None"
        except Exception:
            gp_name = "Unknown"

        lines = [
            f"Target: {SELECTED_DEVICE_NAME} ({self.address})",
            f"Battery: {'--' if self.state.battery_pct is None else str(self.state.battery_pct) + '%'}",
            f"Throttle: {throttle_label(self.state.throttle)}",
            f"Steering: {steering_label(self.state.steering)}",
            f"Lights: {'ON' if self.state.lights else 'OFF'}",
            f"Turbo: {'ON' if self.state.turbo else 'OFF'}",
            f"Donut: {'ON' if self.state.donut else 'OFF'}",
            "",
            f"Using gamepad slot: {SELECTED_CONTROLLER_ID + 1}",
            f"Gamepad: {gp_name}",
        ]

        for idx, text in enumerate(lines):
            surface = self.font.render(text, True, self.TEXT_COLOR)
            self.screen.blit(surface, (24, 24 + idx * 28))

        message = self.message or self.state.message or "--"
        message_surface = self.font.render(f"Message: {message}", True, self.ACCENT_COLOR)
        self.screen.blit(message_surface, (24, 24 + len(lines) * 28 + 12))

        instructions = (
            "Left Analog: steering, Right Analog/A & B: throttle, BACK: lights, RT/LT: turbo\n"
            "      [O]: donut, [M]: mode, [B]: battery, [Q]: quit, [+]/[-]: switch controller"
        )

        lines = instructions.split("\n")
        y = self.screen.get_height() - 60  # start a bit higher for two lines
        for i, line in enumerate(lines):
            surface = self.small_font.render(line, True, (180, 180, 180))
            self.screen.blit(surface, (24, y + i * 20))

        pygame.display.flip()

    def _format_last_status(self) -> str:
        if self.state.last_status:
            items = [f"{k}={v}" for k, v in self.state.last_status.items() if k != "length"]
            return ", ".join(items) if items else str(self.state.last_status)
        if self.state.last_status_hex:
            return self.state.last_status_hex
        return "--"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pygame-based controller for Shell Racing Legends cars",
    )
    parser.add_argument("address", nargs="?", help="Bluetooth MAC address of the car")
    return parser.parse_args()


async def main(address: str) -> None:
    loop = asyncio.get_running_loop()
    app = PygameApp(loop, address)
    await app.run()


def run() -> None:
    args = parse_args()
    address = args.address

    if not address:
        address = pick_bluetooth_device()

    asyncio.run(main(address))


if __name__ == "__main__":
    run()
