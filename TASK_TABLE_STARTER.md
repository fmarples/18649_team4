# Zephyr Task Table — Starter

Fill this out from the implementation your team actually chooses.

| Task | Starter period | Starter priority | Deadline / purpose | Talks to |
|---|---:|---:|---|---|
| UART RX | interrupt/event driven | driver/ISR | receive promptly | UART parser |
| Drive control | 2 ms | 2 | document measured control deadline | encoders, PID, motor driver |
| Heartbeat/status | 20 ms | 5 | 20 ms ±10% period | current sensors, UART TX |
| Blinker update | called from control starter | 2 | 1 Hz ±10%, 50% duty | wheel state, GPIO |
| Steering update | called from control starter | 2 | document measured response | wheel state, servo PWM |
| Current ADC | starter reads from heartbeat | 5 | document ADC deadline | ADC, status |
| Self test | called from control starter | 2 | checkoff asks <=100 ms | wheel button, safety |
| Link watchdog | checked by control thread | 2 | starter uses 100 ms | UART validity, safety |

These values are a starting point, not final measured results. The lab asks for
period, priority, deadline, and what each task talks to.
