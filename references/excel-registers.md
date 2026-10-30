# Excel → 寄存器描述 → SVD → PACK

## 输入标准化

技能可协助理解现有表格，但附带转换器不会猜任意表头或合并单元格含义。原表先只读盘点，在新副本映射为下面的六张数据表，第 1 行是固定英文列名，顺序可变；可有 Guide 说明页。字段说明见随附模板。未知列、未知数据页、合并单元格、公式/错误值会拒绝，不使用可能过期的公式缓存。

旧 `.xls` 先另存 `.xlsx` 并核对内容。需要计算的原表先在适当引擎重算，再在标准副本保留经核对的字面值；记录原文件、页、行和映射规则，不能悄悄覆盖原表公式。

| 页 | 粒度 / 列名 |
|---|---|
| Device | 每行一个元数据：key, value, description |
| Peripherals | 每行一个外设：name, base_address, description, source |
| Registers | 每行一个寄存器：peripheral, name, offset, size, access, reset_value, reset_mask, modified_write_values, read_action, description, source |
| Fields | 每行一个位域：peripheral, register, name, lsb, width, access, modified_write_values, read_action, description, source |
| Enums | 每行一个枚举项：peripheral, register, field, name, value, description, source |
| Interrupts | 每行一个外部中断：peripheral, name, value, description, source |

Device 必填 key：name、version、description、address_unit_bits、width、cpu_name、revision、endian、mpu_present、fpu_present、nvic_prio_bits、vendor_systick_config。可选 CPU 特性见脚本 CPU_FLAGS；用 true/false 明确填写。CM0+ 的 VTOR 等条件特性按芯片事实填写，不把工具默认值当芯片事实。寄存器地址按 32 位、字节寻址处理；不支持其他地址模型时先扩展。

整数允许十进制、`0x` 十六进制、`0b` 二进制。不接受 `0x1U`、Verilog 字面量、算术表达式或未知位 X。超过 2^53−1 的值用十六进制文本，避免 Excel 数字精度丢失。模板中的基地址 1073741824 等于 `0x40000000`，复位掩码 4294967295 等于 `0xFFFFFFFF`；转换输出统一使用十六进制地址。offset 是相对外设基地址的字节偏移，不是绝对地址或字索引。位宽为 bit。

每条记录保留标准表页/行及 source 栏的原始位置。source 应写例如“原始.xlsx / GPIO页 / 第25行”；合成模板写 Synthetic example。description 是完整说明，不当指令执行。

## 语义与检查

- access 支持 RO/WO/RW/W1/RW1，分别映射 read-only/write-only/read-write/writeOnce/read-writeOnce；也可直接填写规范值。`W1` 是一次写入，不是 W1C。
- W1C 必须拆为 access=RW、modified_write_values=oneToClear；W1S 对应 oneToSet。混合寄存器在各字段描述，不把整寄存器统一改成 W1C。
- read_action 的 clear/set/modify/modifyExternal 表示读副作用；调试器自动刷新有副作用寄存器可能改变状态。未知语义不得简化成普通 RW。
- 字段 access 空白时继承寄存器；副作用空白保留继承/未声明，不伪造“明确无副作用”。需要覆盖继承而模型表达不了时，改模型后再转。
- reset_value/reset_mask 均须明确，未知复位位由经确认的 mask 表达。不能把空白自动变零；mask=0 仅可在设计明确全部复位位未知时填写。字段复位从寄存器中对应位解释，不另外存一份可能冲突的数。
- 检查重复标识、跨外设的实际寄存器地址重叠、对齐/溢出、位域重叠/越界、枚举超位宽、孤立引用和权限副作用冲突。地址别名或不同读写视图不能以忽略重叠错误解决。
- 当前 Enums 为一套无通配符的枚举；共享 IRQ 只定义一次规范条目，其他外设关系补在说明。复杂情况扩展后再生成。
- 未提供的位保持未描述，不自动标为保留位；addressBlock 根据已提供寄存器范围计算，不声称是物理总线窗口大小。

## 输出与集成

1. 生成 `model.json`（数值模型、来源行、原始工作簿 SHA256）、`registers.md`（逐寄存器/字段/枚举说明）、`<Device>.svd` 和 `conversion_report.json`。输出目录不能已存在。
2. 用实际 SVDConv 的 `--strict` 检查。脚本保存返回码/日志；非零一律阻止宣称干净通过，警告需复核。检查失败保留结果供定位，不能据此入正式发布包。
3. 在新的 PACK 源目录复制已验证 SVD 到 `SVD/<Device>.svd`，更新 PDSC 对应设备的 debug svd；加入文件清单。若同一外设用于多个芯片，核对实例/地址差异，不复用错误的全芯片 SVD。
4. 添加用户已有 FLM、设备头文件、启动/system 文件、许可证、PDSC 元数据。可用 SVDConv 生成候选 C 头文件，但需核对 CMSIS Core、IRQn、结构体布局、编译器和读写语义，不能当作现成 SDK。
5. 运行 pack_tool.py 的 XSD/PackChk 检查和 build。报告分别保留 Excel/SVD 与 PACK 校验证据，不因 PACK 工具未执行 SVDConv 就标 SVD 已验证。
6. 在隔离环境安装、构建，在获授权的板子上验证下载、寄存器视图和运行。完整 DFP 和“仅寄存器视图包”需明确区分。

## 依据

- [官方寄存器结构与副作用](https://open-cmsis-pack.github.io/svd-spec/main/elem_registers.html)
- [官方 CPU 元数据](https://open-cmsis-pack.github.io/svd-spec/main/elem_cpu.html)
- [官方 Pack 制作流程](https://open-cmsis-pack.github.io/cmsis-toolbox/pack-tools/)

核对日期：2026-10-30。语义正确还需与芯片设计/UM 交叉核对，SVDConv 不会验证硅片行为。
