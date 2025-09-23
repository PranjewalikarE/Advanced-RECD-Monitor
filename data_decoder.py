def decode_hex_data(hex_value):
    try:
        print(f"\n[DEBUG] Original Hex Value: {hex_value}")
        hex_value = hex_value.zfill(16).upper()
        print(f"[DEBUG] Padded Hex Value: {hex_value}")

        # --- Runtime (Byte 7 + 8: 16-bit, MSB first) ---
        runtime_hex = hex_value[-4:-2] + hex_value[-2:]  # MSB + LSB
        runtime_minutes = int(runtime_hex, 16)
        runtime_hours = runtime_minutes // 60
        runtime_remaining_minutes = runtime_minutes % 60
        runtime_str = f"{runtime_hours} hr(s) {runtime_remaining_minutes} min(s)"
        print(f"[DEBUG] Runtime: {runtime_str}")

        # --- Fault Code (Byte 5 + 6: 16-bit, MSB first) ---
        fault_bytes = hex_value[-8:-6] + hex_value[-6:-4]
        fault_bin = bin(int(fault_bytes, 16))[2:].zfill(16)
        fault_codes = [i for i, bit in enumerate(reversed(fault_bin)) if bit == '1']
        print(f"[DEBUG] Fault Binary: {fault_bin}")
        print(f"[DEBUG] Fault Codes: {fault_codes}")

        fault_subcategories = []
        for code in fault_codes:
            if code in [3, 4, 12]:
                fault_subcategories.append((code, "Tempering Error"))
            elif code in [0, 1, 2]:
                fault_subcategories.append((code, "HV Fault"))
            elif code in [5, 6, 7, 9, 13, 14]:
                fault_subcategories.append((code, "Scraping for Motor"))
            elif code == 8:
                fault_subcategories.append((code, "Sootload warning"))
            elif code == 11:
                fault_subcategories.append((code, "Inducement Fault"))
            else:
                fault_subcategories.append((code, "Unknown"))
        print(f"[DEBUG] Fault Subcategories: {fault_subcategories}")

        # --- Leading Fault Error (Byte 4) ---
        leading_fault_error = int(hex_value[6:8], 16)
        leading_fault_desc = "Unknown"
        for code, desc in fault_subcategories:
            if code == leading_fault_error:
                leading_fault_desc = desc
                break
        print(f"[DEBUG] Leading Fault: {leading_fault_error} - {leading_fault_desc}")

        # --- Leading Fault Time Error (Byte 3) ---
        leading_fault_time_error = int(hex_value[4:6], 16)
        leading_fault_time_str = f"{leading_fault_time_error} hr(s)"
        print(f"[DEBUG] Leading Fault Time: {leading_fault_time_str}")

        # --- RECD + Thermostat + HV Voltage (Byte 2) ---
        byte2 = hex_value[2:4]
        byte2_bin = bin(int(byte2, 16))[2:].zfill(8)

        recd_status = "ON" if byte2_bin[0] == '1' else "OFF"          # Bit 7
        thermostat_status = "ON" if byte2_bin[1] == '1' else "OFF"   # Bit 6
        hv_voltage = int(byte2_bin[2:], 2)                            # Bits 0–5

        print(f"[DEBUG] Byte2: {byte2} -> {byte2_bin}")
        print(f"[DEBUG] Genset Signal: {recd_status}, Thermostat: {thermostat_status}, HV Voltage: {hv_voltage} kV")

        # --- HV Source Number + HV Current (Byte 1) ---
        byte1 = hex_value[0:2]
        byte1_bin = bin(int(byte1, 16))[2:].zfill(8)
        hv_current_bits = byte1_bin[3:]  # Bits 3 to 7
        hv_current = int(hv_current_bits, 2)

        hv_source_bits = byte1_bin[1:3]  # Bits 5 & 6
        hv_source_val = int(hv_source_bits, 2)
        hv_source_number = 1 if hv_source_val in [0, 1] else 2 if hv_source_val in [2, 3] else "Unknown"

        print(f"[DEBUG] Byte1: {byte1} -> {byte1_bin}")
        print(f"[DEBUG] HV Source: {hv_source_number}, HV Current: {hv_current} mA")

        return {
            "Runtime": runtime_str,
            "Fault Code": fault_codes[0] if fault_codes else 0,
            "Fault Codes": fault_codes if fault_codes else ["None"],
            "Fault Subcategories": [f"{code}: {desc}" for code, desc in fault_subcategories] if fault_codes else ["No Fault"],
            "Leading Fault": f"{leading_fault_error}: {leading_fault_desc}",
            "Leading Fault Time": leading_fault_time_str,
            "Genset Signal": recd_status,
            "Thermostat Status": thermostat_status,
            "HV Voltage": f"{hv_voltage} kV",
            "HV Current (mA)": f"{hv_current} mA",
            "HV Source Number": str(hv_source_number)
        }

        # ❌ Remove unsupported Unicode like → just in case
        result = {k: (v.replace("→", "->") if isinstance(v, str) else v) for k, v in result.items()}

        return result
    
    except Exception as e:
        print(f"[ERROR] Failed to decode hex data: {str(e)}")
        return {
            "Error": f"Failed to decode hex data: {str(e)}"
        }
