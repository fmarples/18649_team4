#ifndef UART_LINK_H
#define UART_LINK_H
#include "protocol.h"
int uart_link_init(void);
int uart_link_send_status(const status_frame_t *status);
#endif
