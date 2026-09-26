cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab2_uart_link)
target_sources(app PRIVATE src/main.c src/throttle_mapping.c src/drive_control.c src/motor_driver.c
    ../bringup/motor_test/src/bench_encoders.c ../bringup/motor_test/src/velocity_control.c)
target_include_directories(app PRIVATE ../bringup/motor_test/src)
