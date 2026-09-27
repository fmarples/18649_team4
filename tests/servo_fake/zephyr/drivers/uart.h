#ifndef FAKE_UART_H
#define FAKE_UART_H
#include <stdbool.h>
#include <stdint.h>
struct device { int unused; };
extern const struct device fake_console;
extern const char *fake_input;
extern void (*fake_rx_callback)(const struct device *, void *);
#define DT_CHOSEN(x) 0
#define DEVICE_DT_GET(x) (&fake_console)
static inline bool device_is_ready(const struct device *d) { (void)d; return true; }
static inline int uart_irq_update(const struct device *d) { (void)d; return 1; }
static inline int uart_irq_rx_ready(const struct device *d) { (void)d; return 1; }
static inline int uart_fifo_read(const struct device *d, uint8_t *ch, int size)
{ (void)d; (void)size; if (!fake_input || !*fake_input) return 0; *ch = *fake_input++; return 1; }
static inline int uart_irq_callback_user_data_set(const struct device *d, void (*cb)(const struct device *, void *), void *user)
{ (void)d; (void)user; fake_rx_callback = cb; return 0; }
static inline void uart_irq_rx_enable(const struct device *d) { (void)d; }
#endif
