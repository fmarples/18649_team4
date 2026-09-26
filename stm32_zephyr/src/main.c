#include <zephyr/kernel.h>
#include "app_state.h"
#include "uart_link.h"
#include "drive_control.h"
#include "steering.h"
#include "blinker.h"
#include "current_sensor.h"
#include "safety.h"
#include "status.h"
#include "self_test.h"

static command_state_t cmd;
static K_MUTEX_DEFINE(cmd_mutex);

static void control_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (1) {
        command_state_t local;
        k_mutex_lock(&cmd_mutex, K_FOREVER);
        local = cmd;
        k_mutex_unlock(&cmd_mutex);
        safety_check_link();
        drive_control_step(local.throttle, local.brake, safety_in_error());
        steering_set_from_wheel(local.steering);
        blinker_update(local.steering, local.buttons, safety_in_error());
        self_test_update(local.buttons);
        k_sleep(K_MSEC(2));
    }
}

static void heartbeat_thread(void *a, void *b, void *c) {
    ARG_UNUSED(a); ARG_UNUSED(b); ARG_UNUSED(c);
    while (1) {
        status_send(safety_in_error(), current_motor_left_ma(), current_motor_right_ma(), current_servo_ma());
        k_sleep(K_MSEC(20));
    }
}

/* Called by uart_link.c after a validated command. */
void app_command_received(const command_frame_t *f) {
    k_mutex_lock(&cmd_mutex, K_FOREVER);
    cmd.steering=f->steering; cmd.throttle=f->throttle; cmd.brake=f->brake;
    cmd.buttons=f->buttons; cmd.sequence=f->sequence; cmd.valid=true;
    k_mutex_unlock(&cmd_mutex);
    safety_note_valid_command();
    safety_clear_error();
}

K_THREAD_DEFINE(control_tid, 2048, control_thread, NULL, NULL, NULL, 2, 0, 0);
K_THREAD_DEFINE(heartbeat_tid, 2048, heartbeat_thread, NULL, NULL, NULL, 5, 0, 0);

int main(void) {
    safety_init();
    drive_control_init(); steering_init(); blinker_init(); current_sensor_init(); self_test_init(); uart_link_init();
    /* TODO: Keep the system in error until the first valid command arrives. */
    return 0;
}
