#ifndef UART_LINK_H
#define UART_LINK_H

#include "app_state.h"

int uart_link_init(void);
int uart_link_send_status(const struct status_state *status);

/* Copy the newest validated command into out. */
int uart_link_get_command(struct command_state *out);

/* True when no VALID command has been received within the timeout. */
int uart_link_timed_out(int timeout_ms);

#endif
