cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab2_integration)

# Embed the same tracked calibration used by the optional USB calibration console.
set(servo_calibration "${CMAKE_CURRENT_SOURCE_DIR}/../config/servo_calibration.json")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS "${servo_calibration}")
file(READ "${servo_calibration}" servo_json)
string(JSON servo_period GET "${servo_json}" period_us)
if(NOT servo_period EQUAL 20000)
    message(FATAL_ERROR "Steering calibration requires a 20000 us period")
endif()
foreach(point LEFT CENTER RIGHT)
    string(TOLOWER "${point}" key)
    string(JSON SERVO_${point}_US GET "${servo_json}" "${key}_us")
    if(NOT "${SERVO_${point}_US}" MATCHES "^[0-9]+$" OR
       SERVO_${point}_US LESS 500 OR SERVO_${point}_US GREATER 2500)
        message(FATAL_ERROR "Invalid ${key} servo calibration pulse")
    endif()
endforeach()
if(NOT ((SERVO_LEFT_US LESS SERVO_CENTER_US AND SERVO_CENTER_US LESS SERVO_RIGHT_US) OR
        (SERVO_LEFT_US GREATER SERVO_CENTER_US AND SERVO_CENTER_US GREATER SERVO_RIGHT_US)))
    message(FATAL_ERROR "Servo center must be strictly between its endpoints")
endif()
configure_file(src/servo_calibration.h.in generated/servo_calibration.h @ONLY)
target_include_directories(app PRIVATE "${CMAKE_CURRENT_BINARY_DIR}/generated")
target_sources(app PRIVATE src/main.c src/throttle_mapping.c src/drive_control.c src/motor_driver.c
    src/actuator_policy.c src/blinker_core.c src/blinker_gpio.c src/self_test.c
    src/servo_core.c src/servo_bench.c
    src/timing_trace.c src/current_cache.c src/current_sense.c src/current_backend.c
    ../bringup/motor_test/src/bench_encoders.c ../bringup/motor_test/src/velocity_control.c)
target_include_directories(app PRIVATE ../bringup/motor_test/src)
