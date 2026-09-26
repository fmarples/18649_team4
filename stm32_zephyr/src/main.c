#include "app_state.h"
#include "uart_link.h"

#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

/*
 * The lab handout says:
 *   - command updates arrive at least every 50 ms
 *   - three missed updates / 150 ms means fail-safe
 *   - checkoff asks for fail-safe within 100 ms
 *
 * This starter uses the stricter 100 ms timeout so the implementation
 * satisfies the checkoff timing target. If your instructors explicitly
 * direct your team to use 150 ms instead, change this value and document it.
 */
#define FAILSAFE_TIMEOUT_MS 100

#define STATUS_PERIOD_MS 20

static struct status_state status = {
    /*
     * EDIT THESE once your ADC/current-sensor code exists.
     * These are placeholders only.
     */
    .motor1_current = 0,
    .motor2_current = 0,
    .servo_current = 0,
    .zone_state = ZONE_ERROR,
};

static void enter_error_state(void)
{
    /*
     * IMPORTANT:
     * Replace this placeholder with the actual safe outputs:
     *   - disable motor PWM / apply dynamic braking
     *   - put steering/blinker outputs into the required error state
     *   - turn hazards on at 2 Hz, 50% duty
     *
     * Do NOT put the complete motor-control implementation into the UART
     * callback. The callback should only detect/update communication state.
     */
    status.zone_state = ZONE_ERROR;

    /* TODO: call your brake/motor/blinker safety functions here. */
}

static void enter_normal_state(void)
{
    status.zone_state = ZONE_NORMAL;

    /* TODO: enable normal control once your application is ready. */
}

static void control_thread(void *p1, void *p2, void *p3)
{
    ARG_UNUSED(p1);
    ARG_UNUSED(p2);
    ARG_UNUSED(p3);

    struct command_state command;

    while (1) {
        if (uart_link_timed_out(FAILSAFE_TIMEOUT_MS)) {
            enter_error_state();
        } else if (uart_link_get_command(&command) == 0) {
            /*
             * This is where the command should be handed to the actual
             * steering/throttle/brake/blinker control code.
             *
             * IMPORTANT: do not drive hardware directly from the UART ISR.
             */

            if (command.brake != 0) {
                /*
                 * Brake must have priority over throttle.
                 * TODO: replace with your actual brake function.
                 */
            }

            /* TODO: steering_control(command.steering); */
            /* TODO: throttle_control(command.throttle); */
            /* TODO: blinker_control(command.buttons); */

            enter_normal_state();
        }

        k_sleep(K_MSEC(1));
    }
}

static void status_thread(void *p1, void *p2, void *p3)
{
    ARG_UNUSED(p1);
    ARG_UNUSED(p2);
    ARG_UNUSED(p3);

    while (1) {
        /*
         * TODO: replace these with your ADC/current-sensor readings.
         * The lab requires all three readings in every status frame.
         */
        status.motor1_current = 0;
        status.motor2_current = 0;
        status.servo_current = 0;

        (void)uart_link_send_status(&status);

        /*
         * 20 ms period. The handout allows ±10%, i.e. approximately
         * 18-22 ms.
         */
        k_sleep(K_MSEC(STATUS_PERIOD_MS));
    }
}

K_THREAD_DEFINE(control_tid, 2048, control_thread, NULL, NULL, NULL,
                5, 0, 0);

K_THREAD_DEFINE(status_tid, 2048, status_thread, NULL, NULL, NULL,
                8, 0, 0);

int main(void)
{
    int ret = uart_link_init();

    if (ret != 0) {
        enter_error_state();
        printk("UART initialization failed: %d\n", ret);
        return ret;
    }

    /*
     * Cold start is intentionally ERROR until a valid command is received.
     */
    enter_error_state();

    printk("Lab 2 UART receiver started\n");

    return 0;
}
