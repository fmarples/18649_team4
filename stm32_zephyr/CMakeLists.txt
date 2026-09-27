cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab2_integration)
target_sources(app PRIVATE src/main.c src/throttle_mapping.c src/drive_control.c src/motor_driver.c
    src/actuator_policy.c src/blinker_core.c src/blinker_gpio.c src/self_test.c
    src/servo_core.c src/servo_bench.c
    src/timing_trace.c src/current_cache.c src/current_sense.c src/current_backend.c
    ../bringup/motor_test/src/bench_encoders.c ../bringup/motor_test/src/velocity_control.c)
target_include_directories(app PRIVATE ../bringup/motor_test/src)
