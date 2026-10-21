cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab3_demo)
get_filename_component(team_root "${CMAKE_CURRENT_SOURCE_DIR}/../.." ABSOLUTE)
# Reuse the measured baseline's timing instrumentation and workloads, not copies.
set(baseline "${team_root}/lab3_wcet_baseline/lab3_wcet_baseline/stm32_zephyr/src")
target_sources(app PRIVATE src/main.c src/can_protocol.c src/frame_history.c
    src/zone_state.c src/timing_trace.c "${baseline}/timing_stats.c" "${baseline}/timing_probe.c")
target_include_directories(app PRIVATE src "${baseline}")
if(CONFIG_LAB3_ZONE_N3)
    # Lab 2 PID calculation on synthetic samples; no encoder or motor driver.
    set(lab2_pid "${team_root}/bringup/motor_test/src")
    target_sources(app PRIVATE "${baseline}/pid_measurement.c" "${lab2_pid}/velocity_control.c")
    target_include_directories(app PRIVATE "${lab2_pid}")
endif()
if(CONFIG_LAB3_ZONE_N2)
    # Lab 2 calibrated servo mapping from the tracked endpoints.
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
    target_sources(app PRIVATE "${baseline}/steering_measurement.c" "${team_root}/stm32_zephyr/src/servo_core.c")
    target_include_directories(app PRIVATE "${team_root}/stm32_zephyr/src"
                               "${CMAKE_CURRENT_BINARY_DIR}/generated")
endif()
