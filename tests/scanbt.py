import asyncio
import struct
from bleak import BleakScanner, AdvertisementData  # Updated import
from bleak.backends.device import BLEDevice

# BTHome v2 sensor types (from https://bthome.io/format/)
SENSOR_TYPES = {
    0x00: ("packet_id", "uint8"),
    0x01: ("battery", "uint8", "%"),
    0x02: ("temperature", "sint16", "°C", 0.01),
    0x03: ("humidity", "uint16", "%", 0.01),
    # Add more as needed
}

def parse_bthome_v2(data: bytes) -> dict:
    """Parse BTHome v2 advertisement payload."""
    result = {}
    if not data or len(data) < 1:
        return result

    # Check first byte for flags
    flags = data[0]
    mac_included = (flags & 0x02) == 0x02  # Bit 1 indicates MAC address
    pos = 1

    # Extract MAC address if included
    if mac_included and len(data) >= pos + 6:
        mac = ":".join(f"{b:02x}" for b in data[pos:pos+6])
        result["mac"] = mac
        pos += 6

    # Parse sensor objects
    while pos < len(data):
        obj_id = data[pos]
        pos += 1
        if obj_id not in SENSOR_TYPES:
            break  # Unknown sensor type

        sensor_info = SENSOR_TYPES[obj_id]
        sensor_name, format_type = sensor_info[0], sensor_info[1]
        unit = sensor_info[2] if len(sensor_info) > 2 else ""
        scale = sensor_info[3] if len(sensor_info) > 3 else 1

        # Read value based on format
        if format_type == "uint8" and pos < len(data):
            value = data[pos]
            pos += 1
        elif format_type == "sint16" and pos + 1 < len(data):
            value = struct.unpack("<h", data[pos:pos+2])[0]
            pos += 2
        elif format_type == "uint16" and pos + 1 < len(data):
            value = struct.unpack("<H", data[pos:pos+2])[0]
            pos += 2
        else:
            break

        result[sensor_name] = value * scale
        if unit:
            result[sensor_name] = f"{result[sensor_name]}{unit}"

    return result

async def scan_bthome():
    """Scan for BTHome v2 devices and parse advertisements."""
    def callback(device: BLEDevice, advertisement: AdvertisementData):
        # print(f"Advertisement service_data: {advertisement.service_data}")
        # if device.address != "B424A7AE-FF2B-A048-97A0-BE671962F3E4":
        #     return

        # or advertisement.service_data is None:
        # Check for BTHome v2 service UUID
        # UUID for BTHome v2 is 0000fcd2-0000-1000-8000-00805f9b34fb
        if '0000fcd2-0000-1000-8000-00805f9b34fb' in advertisement.service_data:
            # print(f"Detected device: {device.address}, RSSI: {advertisement.rssi}")
            # print(f"Advertisement data: {advertisement}")
            data = advertisement.service_data['0000fcd2-0000-1000-8000-00805f9b34fb']
            if data:
                # print(f"---- data: {advertisement}")
                parsed = parse_bthome_v2(data)
                if parsed:
                    print(f"Device: {device.address}, Data: {parsed}")

    scanner = BleakScanner(detection_callback=callback)
    print("Scanning for BTHome v2 devices...")
    await scanner.start()
    try:
        while True:
            await asyncio.sleep(1)  # Keep scanning
    except KeyboardInterrupt:
        await scanner.stop()
        print("Stopped scanning")

if __name__ == "__main__":
    asyncio.run(scan_bthome())