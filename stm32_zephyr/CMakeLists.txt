cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab2_steering_bench)
target_sources(app PRIVATE src/main.c src/blinker_core.c src/blinker_gpio.c src/self_test.c src/servo_core.c src/servo_bench.c)
