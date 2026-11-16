| Algorithm | family | states | mutual exclusion | deadlock-free | starvation-free |
|---|---|---:|---|---|---|
| `dekker` | software | 324 | holds | yes | yes |
| `peterson` | software | 199 | holds | yes | yes |
| `lock_variable` | broken | 60 | **VIOLATED** | yes | **no** |
| `flag_spin` | broken | 55 | holds | **no** | yes |
| `tas` | hardware | 51 | holds | yes | **no** |
| `semaphore_binary` | primitive | 22 | holds | yes | yes |
| `semaphore_wrong_order` | broken | 48 | holds | **no** | yes |
| `monitor_mesa` | monitor | 54 | holds | yes | yes |
