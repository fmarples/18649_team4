typedef int atomic_t;
static inline int atomic_set(atomic_t *target, int value)
{ int old = *target; *target = value; return old; }
