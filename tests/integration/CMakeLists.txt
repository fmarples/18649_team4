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

# Run the real ADC backend against a hardware double at all supported bench
# populations. Keep the fake ADC header local to these objects, never firmware.
foreach(mask 0 5 7)
  add_library(adc_contract_${mask} OBJECT ../test_current_backend.c
      ../../stm32_zephyr/src/current_backend.c)
  target_link_libraries(adc_contract_${mask} PRIVATE zephyr_interface)
  target_include_directories(adc_contract_${mask} BEFORE PRIVATE
      ../current_adc_fake ../../stm32_zephyr/src)
  target_compile_definitions(adc_contract_${mask} PRIVATE
      CONFIG_LAB_CURRENT_CHANNEL_MASK=${mask}
      CONFIG_LAB_CURRENT_LEFT_ZERO_MV=2500 CONFIG_LAB_CURRENT_RIGHT_ZERO_MV=2500
      CONFIG_LAB_CURRENT_SERVO_ZERO_MV=2500
      CONFIG_LAB_CURRENT_LEFT_SENSITIVITY=185 CONFIG_LAB_CURRENT_RIGHT_SENSITIVITY=185
      CONFIG_LAB_CURRENT_SERVO_SENSITIVITY=185
      main=adc_contract_${mask}_entry test_adc=test_adc_${mask}
      device_is_ready=fake_ready_${mask} adc_read=fake_read_${mask}
      adc_channel_setup=fake_setup_${mask} current_backend_read=backend_read_${mask})
  target_sources(app PRIVATE $<TARGET_OBJECTS:adc_contract_${mask}>)
endforeach()
target_sources(app PRIVATE src/adc_backend.c)
