#include "uart_link.h"
#include "protocol.h"

#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/byteorder.h>
#include <zephyr/sys/util.h>

#define UART_NODE DT_ALIAS(app_uart)

#if !DT_NODE_HAS_STATUS(UART_NODE, okay)
#error "app_uart alias is not defined or not enabled in the devicetree overlay."
#endif

static const struct device *uart_dev = DEVICE_DT_GET(UART_NODE);

static struct command_state latest_command;
static struct k_mutex command_mutex;
static int64_t last_valid_command_ms;

static uint8_t rx_frame[UART_COMMAND_LEN];
static uint8_t rx_index;
static bool receiving_frame;

static uint8_t tx_frame[UART_STATUS_LEN];

static int16_t read_i16_le(const uint8_t *p)
{
    uint16_t u = ((uint16_t)p[0]) | ((uint16_t)p[1] << 8);
    return (int16_t)u;
}

static uint16_t read_u16_le(const uint8_t *p)
{
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t read_u32_le(const uint8_t *p)
{
    return ((uint32_t)p[0]) |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static bool command_values_are_in_range(const struct command_state *cmd)
{
    /*
     * EDIT THESE LIMITS AFTER YOU RECORD YOUR ACTUAL WHEEL VALUES.
     *
     * These are deliberately conservative placeholders for a signed int16
     * transport. They are NOT the team's final steering/throttle/brake ranges.
     */
    const int16_t MIN_VALUE = -32768;
    const int16_t MAX_VALUE = 32767;

    return cmd->steering >= MIN_VALUE && cmd->steering <= MAX_VALUE &&
           cmd->throttle >= MIN_VALUE && cmd->throttle <= MAX_VALUE &&
           cmd->brake >= MIN_VALUE && cmd->brake <= MAX_VALUE;
}

static void accept_command(const uint8_t *frame)
{
    struct command_state candidate;

    candidate.sequence = read_u16_le(&frame[2]);
    candidate.steering = read_i16_le(&frame[4]);
    candidate.throttle = read_i16_le(&frame[6]);
    candidate.brake = read_i16_le(&frame[8]);
    candidate.buttons = read_u32_le(&frame[10]);
    candidate.valid = 0;

    if (!command_values_are_in_range(&candidate)) {
        return;
    }

    candidate.valid = 1;

    k_mutex_lock(&command_mutex, K_FOREVER);
    latest_command = candidate;
    last_valid_command_ms = k_uptime_get();
    k_mutex_unlock(&command_mutex);
}

static void process_rx_byte(uint8_t byte)
{
    if (!receiving_frame) {
        if (byte == UART_SYNC) {
            rx_frame[0] = byte;
            rx_index = 1;
            receiving_frame = true;
        }
        return;
    }

    rx_frame[rx_index++] = byte;

    if (rx_index == UART_COMMAND_LEN) {
        bool valid =
            rx_frame[0] == UART_SYNC &&
            rx_frame[1] == UART_FRAME_COMMAND &&
            rx_frame[UART_COMMAND_LEN - 1] ==
                protocol_checksum(rx_frame, UART_COMMAND_LEN - 1);

        if (valid) {
            accept_command(rx_frame);
        }

        /*
         * Regardless of success/failure, return to sync-search mode.
         * If a byte was dropped, the next 0xAA can start a new frame.
         */
        rx_index = 0;
        receiving_frame = false;
    }
}

static void uart_callback(const struct device *dev,
                          struct uart_event *evt,
                          void *user_data)
{
    ARG_UNUSED(dev);
    ARG_UNUSED(user_data);

    /*
     * Keep this callback short:
     *   - no logging
     *   - no dynamic allocation
     *   - no motor-control work
     *
     * It only feeds bytes into the parser.
     */
    switch (evt->type) {
    case UART_RX_RDY:
        for (size_t i = 0; i < evt->data.rx.len; ++i) {
            process_rx_byte(evt->data.rx.buf[evt->data.rx.offset + i]);
        }
        break;

    case UART_RX_DISABLED:
        /*
         * Re-enable reception if the driver stops receiving.
         * The buffer is static, so no allocation is needed.
         */
        (void)uart_rx_enable(uart_dev, evt->data.rx.buf,
                             evt->data.rx.len, 100);
        break;

    default:
        break;
    }
}

int uart_link_init(void)
{
    static uint8_t rx_buffer[64];

    if (!device_is_ready(uart_dev)) {
        return -1;
    }

    k_mutex_init(&command_mutex);
    last_valid_command_ms = k_uptime_get();
    latest_command.valid = 0;

    int ret = uart_callback_set(uart_dev, uart_callback, NULL);
    if (ret != 0) {
        return ret;
    }

    return uart_rx_enable(uart_dev, rx_buffer, sizeof(rx_buffer), 100);
}

int uart_link_get_command(struct command_state *out)
{
    if (out == NULL) {
        return -1;
    }

    k_mutex_lock(&command_mutex, K_FOREVER);
    *out = latest_command;
    k_mutex_unlock(&command_mutex);

    return out->valid ? 0 : -1;
}

int uart_link_timed_out(int timeout_ms)
{
    int64_t elapsed;

    k_mutex_lock(&command_mutex, K_FOREVER);
    elapsed = k_uptime_get() - last_valid_command_ms;
    k_mutex_unlock(&command_mutex);

    return elapsed >= timeout_ms;
}

int uart_link_send_status(const struct status_state *status)
{
    if (status == NULL) {
        return -1;
    }

    tx_frame[0] = UART_SYNC;
    tx_frame[1] = UART_FRAME_STATUS;

    static uint16_t sequence;
    tx_frame[2] = (uint8_t)(sequence & 0xFFu);
    tx_frame[3] = (uint8_t)((sequence >> 8) & 0xFFu);
    sequence++;

    tx_frame[4] = (uint8_t)(status->motor1_current & 0xFFu);
    tx_frame[5] = (uint8_t)((status->motor1_current >> 8) & 0xFFu);
    tx_frame[6] = (uint8_t)(status->motor2_current & 0xFFu);
    tx_frame[7] = (uint8_t)((status->motor2_current >> 8) & 0xFFu);
    tx_frame[8] = (uint8_t)(status->servo_current & 0xFFu);
    tx_frame[9] = (uint8_t)((status->servo_current >> 8) & 0xFFu);
    tx_frame[10] = status->zone_state;
    tx_frame[11] = protocol_checksum(tx_frame, UART_STATUS_LEN - 1);

    for (size_t i = 0; i < UART_STATUS_LEN; ++i) {
        uart_poll_out(uart_dev, tx_frame[i]);
    }

    return 0;
}
