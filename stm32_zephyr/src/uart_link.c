#include "uart_link.h"
#include "safety.h"
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <stdbool.h>

#define UART_NODE DT_ALIAS(app_uart)
#if !DT_NODE_HAS_STATUS(UART_NODE, okay)
#error "Edit app.overlay: app_uart must point to your STM32 UART."
#endif
static const struct device *uart_dev = DEVICE_DT_GET(UART_NODE);
static uint8_t rx_frame[UART_COMMAND_LEN];
static uint8_t rx_pos;
static bool receiving;
static uint8_t tx_frame[UART_STATUS_LEN];

/* Implemented in main.c so the UART layer does not know about motor/servo code. */
extern void app_command_received(const command_frame_t *f);

static int16_t i16le(const uint8_t *p) { return (int16_t)((uint16_t)p[0] | ((uint16_t)p[1]<<8)); }
static uint16_t u16le(const uint8_t *p) { return (uint16_t)p[0] | ((uint16_t)p[1]<<8); }
static uint32_t u32le(const uint8_t *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }

static bool command_in_range(const command_frame_t *c) {
    /* TODO: Replace these placeholder limits with your recorded Part 1 ranges. */
    const int STEER_MIN=-32768, STEER_MAX=32767;
    const int THROTTLE_MIN=-32768, THROTTLE_MAX=32767;
    const int BRAKE_MIN=-32768, BRAKE_MAX=32767;
    return c->steering>=STEER_MIN && c->steering<=STEER_MAX &&
           c->throttle>=THROTTLE_MIN && c->throttle<=THROTTLE_MAX &&
           c->brake>=BRAKE_MIN && c->brake<=BRAKE_MAX;
}

static void process_byte(uint8_t b) {
    if (!receiving) {
        if (b==UART_SYNC) { rx_frame[0]=b; rx_pos=1; receiving=true; }
        return;
    }
    /* A new sync byte while waiting for a frame can be treated as a resync point. */
    if (b==UART_SYNC && rx_pos>1) { rx_frame[0]=b; rx_pos=1; return; }
    rx_frame[rx_pos++]=b;
    if (rx_pos==UART_COMMAND_LEN) {
        bool valid = rx_frame[1]==FRAME_COMMAND &&
                     rx_frame[UART_COMMAND_LEN-1]==protocol_checksum(rx_frame, UART_COMMAND_LEN-1);
        if (valid) {
            command_frame_t c={0};
            c.type=rx_frame[1]; c.sequence=u16le(&rx_frame[2]);
            c.steering=i16le(&rx_frame[4]); c.throttle=i16le(&rx_frame[6]); c.brake=i16le(&rx_frame[8]);
            c.buttons=u32le(&rx_frame[10]);
            if (command_in_range(&c)) { app_command_received(&c); }
            /* Invalid frames intentionally do NOT refresh the link watchdog. */
        }
        receiving=false; rx_pos=0;
    }
}

static void uart_cb(const struct device *dev, struct uart_event *evt, void *user_data) {
    ARG_UNUSED(dev); ARG_UNUSED(user_data);
    switch(evt->type) {
    case UART_RX_RDY:
        for (size_t i=0;i<evt->data.rx.len;i++) process_byte(evt->data.rx.buf[evt->data.rx.offset+i]);
        break;
    case UART_RX_DISABLED:
        /* TODO: If your Zephyr UART driver behaves differently, adapt this re-enable path. */
        (void)uart_rx_enable(uart_dev, evt->data.rx.buf, evt->data.rx.len, 100);
        break;
    default: break;
    }
}

int uart_link_init(void) {
    static uint8_t rx_buffer[64];
    if (!device_is_ready(uart_dev)) return -1;
    int rc=uart_callback_set(uart_dev, uart_cb, NULL);
    if (rc) return rc;
    return uart_rx_enable(uart_dev, rx_buffer, sizeof(rx_buffer), 100);
}

int uart_link_send_status(const status_frame_t *s) {
    if (!s) return -1;
    static uint16_t seq;
    tx_frame[0]=UART_SYNC; tx_frame[1]=FRAME_STATUS;
    tx_frame[2]=(uint8_t)seq; tx_frame[3]=(uint8_t)(seq>>8); seq++;
    tx_frame[4]=(uint8_t)s->motor1_current; tx_frame[5]=(uint8_t)(s->motor1_current>>8);
    tx_frame[6]=(uint8_t)s->motor2_current; tx_frame[7]=(uint8_t)(s->motor2_current>>8);
    tx_frame[8]=(uint8_t)s->servo_current; tx_frame[9]=(uint8_t)(s->servo_current>>8);
    tx_frame[10]=s->state; tx_frame[11]=protocol_checksum(tx_frame, UART_STATUS_LEN-1);
    for (size_t i=0;i<UART_STATUS_LEN;i++) uart_poll_out(uart_dev, tx_frame[i]);
    return 0;
}
