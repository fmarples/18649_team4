#ifndef UART_LINK_H
#define UART_LINK_H

#include "protocol.h"
#include "udp_receiver.h"

int uart_open(const char *device);
int uart_send_command(const wheel_state_t *state, uint16_t sequence);
int uart_receive_status(uint8_t *frame, uint8_t max_len);
void uart_close(void);

#endif
