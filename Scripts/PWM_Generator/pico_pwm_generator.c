/**
 * Raspberry Pi Pico - Dual PWM Generator (1Hz and 15Hz, 25% duty cycle)
 * Using PWM with C SDK at 12MHz system clock
 *
 * Compilation:
 * Add to CMakeLists.txt:
 * target_link_libraries(your_project pico_stdlib hardware_pwm)
 */

#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include "hardware/clocks.h"

#define PWM_PIN_LIDAR 2      // SLICE 1
#define PWM_PIN_IMU 6        // SLICE 3
#define PWM_PIN_REALSENSE 10 // SLICE 5

#define FREQUENCY_1HZ 1
#define FREQUENCY_30HZ 30
#define DUTY_CYCLE_PERCENT 25

int main()
{
    clock_configure(clk_sys, CLOCKS_CLK_SYS_CTRL_SRC_VALUE_CLK_REF, 0, 12 * MHZ, 12 * MHZ);
    uint32_t sys_clock_hz = clock_get_hz(clk_sys);

    gpio_set_function(PWM_PIN_LIDAR, GPIO_FUNC_PWM);
    gpio_set_function(PWM_PIN_IMU, GPIO_FUNC_PWM);
    gpio_set_function(PWM_PIN_REALSENSE, GPIO_FUNC_PWM);

    uint slice_num_lidar = pwm_gpio_to_slice_num(PWM_PIN_LIDAR);
    uint slice_num_imu = pwm_gpio_to_slice_num(PWM_PIN_IMU);
    uint slice_num_realsense = pwm_gpio_to_slice_num(PWM_PIN_REALSENSE);

    float divider_1hz = 255.0f;
    uint32_t wrap_1hz = (sys_clock_hz / (FREQUENCY_1HZ * divider_1hz)) - 1;
    uint16_t level_1hz = ((wrap_1hz + 1) * DUTY_CYCLE_PERCENT) / 100;

    pwm_config config_1hz = pwm_get_default_config();
    pwm_config_set_clkdiv(&config_1hz, divider_1hz);
    pwm_config_set_wrap(&config_1hz, wrap_1hz);

    uint32_t wrap_30hz = 2068;
    float divider_30hz = (float)sys_clock_hz / (FREQUENCY_30HZ * (wrap_30hz + 1));
    uint16_t level_30hz = ((wrap_30hz + 1) * DUTY_CYCLE_PERCENT) / 100;

    pwm_config config_30hz = pwm_get_default_config();
    pwm_config_set_clkdiv(&config_30hz, divider_30hz);
    pwm_config_set_wrap(&config_30hz, wrap_30hz);

    pwm_init(slice_num_lidar, &config_1hz, false);
    pwm_init(slice_num_imu, &config_1hz, false);
    pwm_init(slice_num_realsense, &config_30hz, false);

    pwm_set_gpio_level(PWM_PIN_LIDAR, level_1hz);
    pwm_set_gpio_level(PWM_PIN_IMU, level_1hz);
    pwm_set_gpio_level(PWM_PIN_REALSENSE, level_30hz);

    pwm_set_enabled(slice_num_lidar, true);
    pwm_set_enabled(slice_num_imu, true);
    pwm_set_enabled(slice_num_realsense, true);

    while (true)
        sleep_ms(10000);

    return 0;
}