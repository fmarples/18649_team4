cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(motor_bench)
target_sources(app PRIVATE src/main.c src/bench_control.c src/bench_encoders.c)
