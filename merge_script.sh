# 
pattern_inv1="# MARKER: insert modbus device for inverter 1 here"
pattern_inv2="# MARKER: insert modbus device for inverter 1 here"

pattern_inv1_sens="# MARKER: insert modbus sensors for inverter 1 here"
pattern_inv2_sens="# MARKER: insert modbus sensors for inverter 2 here"

pattern_template_binary_sensor="# MARKER: template binary sensors are inserted here"
pattern_template_sensor="# MARKER: template sensors are inserted here"
 
pattern_input_number="# MARKER: input numbers are inserted here"
pattern_input_select="# MARKER: input selects are inserted here"
pattern_automation="# MARKER: automations are inserted here"
 

stubFile="_stub.yaml"

src_device="_modbus_device.yaml"

src_basic_sensors="_basic_sensors.yaml"
src_basic_template_binary_sensor="_basic_template_binary_sensor.yaml"
src_basic_template_sensor="_basic_template_sensor.yaml"
src_basic_input_number="_basic_input_number.yaml"
src_basic_input_select="_basic_input_select.yaml"
src_basic_automation="_basic_automation.yaml"

src_extended_sensors="_extended_sensors.yaml"
src_extended_template_sensor="_extended_template_sensor.yaml"

src_battery_sensors="_battery_sensors.yaml"
src_battery_input_number="_battery_input_number.yaml"
src_battery_input_select="_battery_input_select.yaml"
src_battery_template_sensor="_battery_template_binary_sensor.yaml"
src_battery_automation="_battery_automation.yaml"

cd src

inv1_SH_basic="1_inv_SH_basic.yaml"
echo "Generating $inv1_SH_basic"
sed -e "/$pattern_inv1/ r $src_device" \
-e "/$pattern_inv1_sens/ r $src_basic_sensors" \
-e "/$pattern_template_binary_sensor/ r $src_basic_template_binary_sensor" \
-e "/$pattern_template_sensor/ r $src_basic_template_sensor" \
-e "/$pattern_input_number/ r $src_basic_input_number" \
-e "/$pattern_input_select/ r $src_basic_input_select" \
-e "/$pattern_automation/ r $src_basic_automation" \
$stubFile > $inv1_SH_basic


inv1_SH_basic_battery="1_inv_SH_basic_battery.yaml"
echo "Generating $inv1_SH_basic_battery based on $inv1_SH_basic"
sed -e "/$pattern_inv1/ r $src_device" \
-e "/$pattern_inv1_sens/ r $src_basic_sensors" \
-e "/$pattern_template_binary_sensor/ r $src_basic_template_binary_sensor" \
-e "/$pattern_template_sensor/ r $src_basic_template_sensor" \
-e "/$pattern_input_number/ r $src_basic_input_number" \
-e "/$pattern_input_select/ r $src_basic_input_select" \
-e "/$pattern_automation/ r $src_basic_automation" \
$inv1_SH_basic > $inv1_SH_basic_battery


inv1_SH_extended="1_inv_SH_extended.yaml"
echo "Generating $inv1_SH_extended based on $inv1_SH_basic"
sed -e "/$pattern_inv1_sens/ r $src_extended_sensors" \
-e "/$pattern_template_sensor/ r $src_extended_template_sensor" \
$inv1_SH_basic > $inv1_SH_extended


inv1_SH_extended_battery="1_inv_SH_extended_battery.yaml"
echo "Generating $inv1_SH_extended_battery based on $inv1_SH_extended" 
sed -e "/$pattern_inv1_sens/ r $src_battery_sensors" \
-e "/$pattern_template_binary_sensor/ r $src_battery_template_sensor" \
-e "/$pattern_input_number/ r $src_battery_input_number" \
-e "/$pattern_input_select/ r $src_battery_input_select" \
-e "/$pattern_automation/ r $src_battery_automation" \
$inv1_SH_extended > $inv1_SH_extended_battery



mv *1_inv* ../generated

cd ..
