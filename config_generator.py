#!/usr/bin/env python3

import fileinput
import os
import shutil

# Determine the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = script_dir + "/src"

# Define file paths and patterns
src_folder = "src"
output_folder = "configurations"

pattern_inv1_device = "# MARKER: insert modbus device for inverter 1 here"
pattern_inv2_device = "# MARKER: insert modbus device for inverter 2 here"
pattern_inv1_sensors = "# MARKER: insert modbus sensors for inverter 1 here"
pattern_inv2_sensors = "# MARKER: insert modbus sensors for inverter 2 here"
pattern_template_binary_sensor = "# MARKER: template binary sensors are inserted here"
pattern_template_sensor = "# MARKER: template sensors are inserted here"
pattern_input_number = "# MARKER: input numbers are inserted here"
pattern_input_select = "# MARKER: input selects are inserted here"
pattern_automation = "# MARKER: automations are inserted here"


def generate_output(output_file_name, src_file, patterns):
    src_file_path = os.path.join(src_dir, src_file)
    output_file_path = os.path.join(src_dir, output_file_name)

    print("src_file:", src_file)
    print("output_file:", output_file_name)

    with open(output_file_path, "w") as output:
        with fileinput.FileInput(src_file_path) as file:
            for line in file:
                for pattern, content_files in patterns:
                    if pattern in line:
                        output.write(line)
                        for content_file in content_files:
                            content_file_path = os.path.join(src_folder, content_file)
                            print("Appending content from:", content_file_path)
                            output.write(f"# inserted from {content_file}\n")
                            output.write(open(content_file_path).read())
                        break
                else:
                    output.write(line)
    print("")



output_files = [
    ("1_inv_SG_basic.yaml", "stub.yaml", [
        (pattern_inv1_device, ["modbus_device_sg1.yaml"]),
        (pattern_inv1_sensors, ["basic_sensors.yaml", "basic_sensors_sg.yaml"]),
        (pattern_template_binary_sensor, ["basic_template_binary_sensor_sg.yaml"]),
        (pattern_template_sensor, ["basic_template_sensor.yaml", "basic_template_sensor_sg.yaml"]),
        (pattern_input_number, ["basic_input_number.yaml"]),
        (pattern_input_select, ["basic_input_select.yaml"]),
        (pattern_automation, ["basic_automation.yaml"]),
    ]),
    ("1_inv_SG_extended.yaml", "1_inv_SG_basic.yaml", [
        (pattern_inv1_sensors, ["extended_sensors.yaml"]),
        (pattern_template_sensor, ["extended_template_sensor.yaml"]),
    ]),
    ("1_inv_SH_basic.yaml", "stub.yaml", [
        (pattern_inv1_device, ["modbus_device_sg1.yaml"]),
        (pattern_inv1_sensors, ["basic_sensors_sh.yaml", "basic_sensors.yaml"]),
        (pattern_template_binary_sensor, ["basic_template_binary_sensor_sh.yaml"]),
        (pattern_template_sensor, ["basic_template_sensor.yaml", "basic_template_sensor_sh.yaml"]),
        (pattern_input_number, ["basic_input_number.yaml"]),
        (pattern_input_select, ["basic_input_select.yaml"]),
        (pattern_automation, ["basic_automation.yaml"]),
    ]),
    ("1_inv_SH_extended.yaml", "1_inv_SH_basic.yaml", [
        (pattern_inv1_sensors, ["extended_sensors.yaml"]),
        (pattern_template_sensor, ["extended_template_sensor.yaml"]),
    ]),
    ("1_inv_SH_basic_battery.yaml", "1_inv_SH_basic.yaml", [
        (pattern_inv1_sensors, ["generic_battery_sensors.yaml"]),
        (pattern_template_sensor, ["generic_battery_template_sensor.yaml"]),
        (pattern_template_binary_sensor, ["generic_battery_template_binary_sensor.yaml"]),
        (pattern_input_number, ["generic_battery_input_number.yaml"]),
        (pattern_input_select, ["generic_battery_input_select.yaml"]),
        (pattern_automation, ["generic_battery_automation.yaml"]),
    ]),
    ("1_inv_SH_extended_battery.yaml", "1_inv_SH_basic_battery.yaml", [
        (pattern_inv1_sensors, ["extended_sensors.yaml"]),
        (pattern_template_sensor, ["extended_template_sensor.yaml"]),
    ]),
    ("2_inv_basic.yaml", "1_inv_SH_basic.yaml", [
        (pattern_inv2_device, ["modbus_device_sg2.yaml"]),
        (pattern_inv2_sensors, ["second_inverter_basic_sensor.yaml"]),
        (pattern_template_sensor, ["second_inverter_basic_template_sensor.yaml"]),
        (pattern_template_binary_sensor, ["second_inverter_basic_template_binary_sensor.yaml"]),
    ]),
    ("2_inv_basic_battery.yaml", "1_inv_SH_basic_battery.yaml", [
        (pattern_inv2_device, ["modbus_device_sg2.yaml"]),
        (pattern_inv2_sensors, ["second_inverter_basic_sensor.yaml"]),
        (pattern_template_sensor, ["second_inverter_basic_template_sensor.yaml"]),
        (pattern_template_binary_sensor, ["second_inverter_basic_template_binary_sensor.yaml"]),
    ]),
]



for output_file, source_file, patterns in output_files:
    generate_output(output_file, source_file, patterns)

print("Generation complete!")

print("Moving to folder /configurations...")
for output_file, source_file, patterns in output_files:
    src_file_path = os.path.join(src_dir, output_file)
    dst_file_path = os.path.join(output_folder, output_file)
    
    # Create the destination folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    shutil.move(src_file_path, dst_file_path)
    print("Moved:", src_file_path, "to", dst_file_path)

    with fileinput.FileInput(dst_file_path, inplace=True) as file:
        for line in file:
            if "# MARKER" not in line:
                print(line, end="")

print("...done")

