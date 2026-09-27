cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab2_integration_tests)
target_include_directories(app PRIVATE ../../stm32_zephyr/src ../../bringup/motor_test/src)
target_sources(app PRIVATE
    src/actuators.c src/drive.c src/velocity.c src/bench.c src/throttle.c src/currents.c
    ../../stm32_zephyr/src/current_cache.c
    ../blinker_core/src/main.c ../blinker_core/src/self_test.c ../blinker_core/src/servo.c
    ../../stm32_zephyr/src/actuator_policy.c
    ../../stm32_zephyr/src/blinker_core.c ../../stm32_zephyr/src/self_test.c
    ../../stm32_zephyr/src/servo_core.c ../../stm32_zephyr/src/drive_control.c
    ../../stm32_zephyr/src/throttle_mapping.c
    ../../bringup/motor_test/src/velocity_control.c ../../bringup/motor_test/src/bench_control.c)
