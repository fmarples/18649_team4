cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab2_full_starter)
target_sources(app PRIVATE
    src/main.c src/uart_link.c src/motor.c src/encoder.c src/pid.c
    src/drive_control.c src/steering.c src/blinker.c src/current_sensor.c
    src/safety.c src/status.c src/self_test.c)
