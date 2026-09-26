cmake_minimum_required(VERSION 3.28.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(lab2_blinkers)
target_sources(app PRIVATE src/main.c src/blinker_core.c src/blinker_gpio.c)
