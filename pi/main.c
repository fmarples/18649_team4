#include "udp_receiver.h"
#include "uart.h"

#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static volatile sig_atomic_t running = 1;

static void handle_signal(int sig)
{
    (void)sig;
    running = 0;
}

int main(void)
{
    wheel_state_t state;
    uint16_t sequence = 0;

    /*
     * EDIT THIS:
     *
     * Common Raspberry Pi UART device names include:
     *   /dev/serial0
     *   /dev/ttyAMA0
     *   /dev/ttyS0
     *
     * Use the device actually wired to your STM32.
     */
    const char *uart_device = "/dev/serial0";

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    if (udp_receiver_open() != 0) {
        return EXIT_FAILURE;
    }

    if (uart_open(uart_device) != 0) {
        udp_receiver_close();
        return EXIT_FAILURE;
    }

    printf("Pi bridge running. Press Ctrl-C to stop.\n");

    while (running) {
        int result = udp_receiver_receive(&state);

        if (result < 0) {
            break;
        }

        if (result == 1) {
            /*
             * The lab requires a command on every UDP state update.
             * The laptop proxy is expected to send updates at <= 50 ms.
             */
            if (uart_send_command(&state, sequence++) != 0) {
                break;
            }

            printf("seq=%u steer=%ld throttle=%ld brake=%ld buttons=0x%08lx\n",
                   (unsigned)((uint16_t)(sequence - 1)),
                   (long)state.steering_raw,
                   (long)state.throttle_raw,
                   (long)state.brake_raw,
                   (unsigned long)state.buttons);
            fflush(stdout);
        }
    }

    uart_close();
    udp_receiver_close();

    return EXIT_SUCCESS;
}
