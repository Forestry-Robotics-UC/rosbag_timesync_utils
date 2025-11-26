cmake_minimum_required(VERSION 3.13)

include(pico_sdk_import.cmake)
include(pico_extras_import.cmake)

project(prr_device_firmware C CXX ASM)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

pico_sdk_init()

#############################################################################################

add_executable(pico_pwm_generator 
        pico_pwm_generator.c
)

target_link_libraries(pico_pwm_generator
        pico_stdlib
        hardware_pwm
)

pico_enable_stdio_usb(pico_pwm_generator 1)
pico_enable_stdio_uart(pico_pwm_generator 0)

pico_add_extra_outputs(pico_pwm_generator)