cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab3_dual_can_demo)
get_filename_component(team_root "${CMAKE_CURRENT_SOURCE_DIR}/../../.." ABSOLUTE)
target_sources(app PRIVATE src/main.c src/can_protocol.c src/timing_trace.c src/timing_stats.c src/timing_probe.c)
if(CONFIG_LAB3_ZONE_N3)
    # Reuse the Lab 2 calculation directly; never link its encoder/motor hardware drivers.
    set(lab2_pid "${CMAKE_CURRENT_SOURCE_DIR}/../../../bringup/motor_test/src")
    target_sources(app PRIVATE src/pid_measurement.c "${lab2_pid}/velocity_control.c")
    target_include_directories(app PRIVATE "${lab2_pid}")
endif()
if(CONFIG_LAB3_ZONE_N2)
    # Reuse only Lab 2's mapping, not its PWM driver or automatic steering policy.
    set(calibration_file "${team_root}/config/servo_calibration.json")
    set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${calibration_file}")
    file(READ "${calibration_file}" calibration_json)
    foreach(point LEFT CENTER RIGHT)
        string(TOLOWER "${point}" key)
        string(JSON SERVO_${point}_US GET "${calibration_json}" "${key}_us")
        if(NOT "${SERVO_${point}_US}" MATCHES "^[0-9]+$" OR
           SERVO_${point}_US LESS 500 OR SERVO_${point}_US GREATER 2500)
            message(FATAL_ERROR "Invalid ${key} steering calibration")
        endif()
    endforeach()
    if(NOT ((SERVO_LEFT_US LESS SERVO_CENTER_US AND SERVO_CENTER_US LESS SERVO_RIGHT_US) OR
            (SERVO_LEFT_US GREATER SERVO_CENTER_US AND SERVO_CENTER_US GREATER SERVO_RIGHT_US)))
        message(FATAL_ERROR "Steering center must be between endpoints")
    endif()
    configure_file("${team_root}/stm32_zephyr/src/servo_calibration.h.in"
                   generated/servo_calibration.h @ONLY)
    target_sources(app PRIVATE src/steering_measurement.c "${team_root}/stm32_zephyr/src/servo_core.c")
    target_include_directories(app PRIVATE "${team_root}/stm32_zephyr/src"
                               "${CMAKE_CURRENT_BINARY_DIR}/generated")
endif()
