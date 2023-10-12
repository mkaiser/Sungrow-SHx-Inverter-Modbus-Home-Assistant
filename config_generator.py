#!/usr/bin/env python3

import fileinput
import os
import shutil
def generate_output(src_file, output_file, patterns):
    src_file = os.path.join(src_dir, src_file)
    output_file = os.path.join(src_dir, output_file)

    print("src_file:", src_file)
    print("output_file:", output_file)

    with open(output_file, "w") as output:
        with fileinput.FileInput(src_file) as file:
            for line in file:
                for pattern, content_file in patterns:
                    if pattern in line:
                        output.write(line)
                        output.write(open(os.path.join(src_folder, content_file)).read())
                        break
                else:
                    output.write(line)


# Determine the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = script_dir + "/src"

# Define file paths and patterns
src_folder = "src"
output_folder = "configurations"

pattern_inv1_device = "# MARKER: insert modbus device for inverter 1 here"
pattern_inv1_sensors = "# MARKER: insert modbus sensors for inverter 1 here"
pattern_template_binary_sensor = "# MARKER: template binary sensors are inserted here"
pattern_template_sensor = "# MARKER: template sensors are inserted here"
pattern_input_number = "# MARKER: input numbers are inserted here"
pattern_input_select = "# MARKER: input selects are inserted here"
pattern_automation = "# MARKER: automations are inserted here"

stub_file = "stub.yaml"
src_device = "modbus_device.yaml"
src_basic_sensors = "basic_sensors.yaml"
src_basic_sensors_sg = "basic_sensors_sg.yaml"
src_basic_sensors_sh = "basic_sensors_sh.yaml"
src_basic_template_binary_sensor_sg = "basic_template_binary_sensor_sg.yaml"
src_basic_template_binary_sensor_sh = "basic_template_binary_sensor_sh.yaml"
src_basic_template_sensor = "basic_template_sensor.yaml"
src_basic_template_sensor_sg = "basic_template_sensor_sg.yaml"
src_basic_template_sensor_sh = "basic_template_sensor_sh.yaml"
src_basic_input_number = "basic_input_number.yaml"
src_basic_input_select = "basic_input_select.yaml"
src_basic_automation = "basic_automation.yaml"
src_extended_sensors = "extended_sensors.yaml"
src_extended_template_sensor = "extended_template_sensor.yaml"
src_battery_sensors = "battery_sensors.yaml"
src_battery_template_sensor = "battery_template_binary_sensor.yaml"
src_battery_input_number = "battery_input_number.yaml"
src_battery_input_select = "battery_input_select.yaml"
src_battery_automation = "battery_automation.yaml"


# Define output files and patterns
output_files = [
    (stub_file, "1_inv_SG_basic.yaml", [
        (pattern_inv1_device, src_device),
        (pattern_inv1_sensors, src_basic_sensors),
        (pattern_inv1_sensors, src_basic_sensors_sg),
        (pattern_template_binary_sensor, src_basic_template_binary_sensor_sg),
        (pattern_template_sensor, src_basic_template_sensor),
        (pattern_template_sensor, src_basic_template_sensor_sg),
        (pattern_input_number, src_basic_input_number),
        (pattern_input_select, src_basic_input_select),
        (pattern_automation, src_basic_automation),
    ]),
    ("1_inv_SG_basic.yaml", "1_inv_SG_extended.yaml", [
        (pattern_inv1_sensors, src_extended_sensors),
        (pattern_template_sensor, src_extended_template_sensor),
    ]),
    (stub_file, "1_inv_SH_basic.yaml", [
        (pattern_inv1_device, src_device),
        (pattern_inv1_sensors, src_basic_sensors),
        (pattern_inv1_sensors, src_basic_sensors_sh),
        (pattern_template_binary_sensor, src_basic_template_binary_sensor_sh),
        (pattern_template_sensor, src_basic_template_sensor),
        (pattern_template_sensor, src_basic_template_sensor_sh),
        (pattern_input_number, src_basic_input_number),
        (pattern_input_select, src_basic_input_select),
        (pattern_automation, src_basic_automation),
    ]),
    ("1_inv_SH_basic.yaml", "1_inv_SH_extended.yaml", [
        (pattern_inv1_sensors, src_extended_sensors),
        (pattern_template_sensor, src_extended_template_sensor),
    ]),
    ("1_inv_SH_basic.yaml", "1_inv_SH_basic_battery.yaml", [
        (pattern_inv1_sensors, src_battery_sensors),
        (pattern_template_sensor, src_battery_template_sensor),
        (pattern_input_number, src_battery_input_number),
        (pattern_input_select, src_battery_input_select),
        (pattern_automation, src_battery_automation),
    ]),
    ("1_inv_SH_basic_battery.yaml", "1_inv_SH_extended_battery.yaml", [
        (pattern_inv1_sensors, src_extended_sensors),
        (pattern_template_sensor, src_extended_template_sensor),
    ]),
]

for source_file, output_file, patterns in output_files:
    generate_output(source_file, output_file, patterns)

print("Generation complete!")



print("Moving to folder /configurations...")
for source_file, output_file, patterns in output_files:
    srcFile = os.path.join(src_dir, output_file)
    dstFile = os.path.join(output_folder, output_file)
    
    # Create the destination folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    shutil.move(srcFile, dstFile)

    with fileinput.FileInput(dstFile, inplace=True) as file:
        for line in file:
            if "# MARKER" not in line:
              print(line, end="")

print("Finished")
