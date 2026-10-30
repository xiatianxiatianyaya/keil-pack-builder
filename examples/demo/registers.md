# DemoM0 寄存器描述

Synthetic Cortex-M0 example; not a real chip.

由 Excel 标准化表生成；来源行保留于 model.json。addressBlock 是已提供寄存器范围的计算结果。未提供的位不自动定义为保留位。

## DEMO — 0x40000000

Synthetic peripheral for conversion testing.

### CTRL

Synthetic control register.

地址：`0x40000000`；偏移：`0x0`；位宽：32；访问：read-write；复位：`0x0`；复位掩码：`0xffffffff`。
寄存器写副作用：未声明；读副作用：未声明。

| 字段 | 位段 | 访问 | 写副作用 | 读副作用 | 描述 | 枚举 |
|---|---|---|---|---|---|---|
| EN | 0:0 | read-write | 继承/未声明 | 继承/未声明 | Synthetic enable bit. | 0: DISABLED — Disabled.; 1: ENABLED — Enabled. |
| MODE | 2:1 | read-write | 继承/未声明 | 继承/未声明 | Synthetic mode selection. | 0: MODE_A — Synthetic mode A.; 1: MODE_B — Synthetic mode B.; 2: MODE_C — Synthetic mode C.; 3: MODE_D — Synthetic mode D. |

### STATUS

Synthetic status register with a W1C flag.

地址：`0x40000004`；偏移：`0x4`；位宽：32；访问：read-write；复位：`0x0`；复位掩码：`0xffffffff`。
寄存器写副作用：未声明；读副作用：未声明。

| 字段 | 位段 | 访问 | 写副作用 | 读副作用 | 描述 | 枚举 |
|---|---|---|---|---|---|---|
| FLAG | 0:0 | read-write | oneToClear | 继承/未声明 | Write one to clear this synthetic flag. |  |

中断 `DEMO`：外部 IRQ 编号 0，Synthetic external interrupt zero.。

