# Excel 寄存器表到 Keil PACK

通用 Codex Skill：将 Excel 寄存器规格转换为可追溯的寄存器说明和 CMSIS-SVD，再结合项目已有的设备资源制作 Keil/CMSIS PACK。

适合需要维护芯片寄存器规格、制作调试器寄存器视图、整理设备支持包的工程师和团队。

**[查看 Excel 模板](assets/registers-template.xlsx) · [查看生成的寄存器说明](examples/demo/registers.md) · [定制需求咨询](https://github.com/xiatianxiatianyaya/keil-pack-builder/issues/new)**

## 示例：一份 Excel，生成三种可复用资料

随附 DemoM0 是虚构设备，包含 1 个外设、2 个寄存器、3 个位域、6 个枚举项和 1 个外部中断。示例中的 `STATUS.FLAG` 是写 1 清零位，用于展示转换时如何保留 W1C 语义。

| 输入 / 输出 | 用途 |
|---|---|
| [registers-template.xlsx](assets/registers-template.xlsx) | 维护设备、外设、寄存器、位域、枚举和中断规格 |
| [registers.md](examples/demo/registers.md) | 阅读地址、位域、访问权限、复位值及副作用说明 |
| [DemoM0.svd](examples/demo/DemoM0.svd) | 供支持 CMSIS-SVD 的工具读取寄存器定义 |
| [model.json](examples/demo/model.json) | 保留标准化数值、来源行及输入文件哈希，便于后续生成文档或检查差异 |

按下方快速开始命令即可复现转换。这是工具流程示例，不是真实芯片的验证案例；完整可烧录 PACK 还需要对应芯片的设备资源。

## 包含内容

- `SKILL.md`：完整工作流程和使用边界。
- `assets/registers-template.xlsx`：包含虚构示例的 Excel 模板。
- `scripts/excel_to_svd.py`：Excel → `model.json`、`registers.md`、SVD 与校验报告。
- `scripts/pack_tool.py`：PDSC、显式文件清单、XSD/PackChk 校验和 `.pack` 打包。
- `assets/dfp-template/`：PDSC 和文件清单模板。
- `references/`：表格规范、寄存器语义及工具使用说明。
- `scripts/test_*.py`：离线回归测试。

## 快速开始

Python 3.10+，在仓库根目录执行：

```powershell
python -m pip install -r requirements.txt
python scripts/excel_to_svd.py assets/registers-template.xlsx --out output/demo --svdconv "C:/Keil_v5/ARM/ctools/bin/SVDConv.exe"
python -m unittest discover -s scripts -p "test_*.py" -v
```

工具路径按本机实际安装位置修改。`output/demo` 必须是尚不存在的新目录。没有 SVDConv 时可省略该参数生成待校验结果，但不能视为官方工具验证通过。

原始 Excel 应保留不动，先按 [转换约定](references/excel-registers.md) 建立标准化副本。转换器不猜任意表头、合并单元格或未知复位值。模板数据全部虚构，不能直接用于芯片。

将核验后的 SVD 与真实 FLM、头文件、启动/system 文件放入 PACK 源目录，更新 PDSC 的 `debug svd` 及 `pack-files.json`，再运行：

```powershell
python scripts/pack_tool.py build path/to/pack-files.json --out output/pack --packchk "path/to/PackChk.exe" --xsd "path/to/PACK.xsd"
```

## 作为 Skill 使用

下载仓库后，将包含 `SKILL.md` 的目录命名为 `keil-pack-builder`，放入个人 skills 目录。使用时可以说：

> 使用 keil-pack-builder，把这份 Excel 寄存器表转换为寄存器说明、SVD，并结合我提供的设备资源制作 PACK。

## 已验证与边界

2026-10-30：28 项离线测试通过；虚构示例通过 SVDConv 3.3.43 严格检查（0 错误、0 警告）。生成的 SVD 已完成入包字节一致性验证，PACK XSD 检查通过。PackChk 1.3.97 在仅寄存器视图示例中报告 0 错误、1 个缺少 Startup 组件的警告。

未验证真实芯片寄存器、Keil 安装、启动工程编译或实机烧录。Flash 算法和芯片特定资源由使用者提供，不从 Excel 推测。高级数组、cluster、别名及读写不同枚举需按真实规格扩展转换模型。

仓库不包含公司芯片资料、真实测试记录或第三方工具二进制。通用代码按 [MIT License](LICENSE) 发布；用户提供资源的授权另行确认。

## 定制与商业支持

开源工具可按 MIT 许可证自行使用和商用。需要适配自己的规格或工程时，可提出以下付费定制需求；实际承接范围、报价、排期及验收标准在评估后约定。

| 服务 | 需要提供 | 可约定的交付内容 |
|---|---|---|
| Excel 格式适配 | 脱敏样表、列定义、地址与位域规则 | 转换映射、标准化模板、未映射项清单及适配脚本 |
| 寄存器资料生成 | 经确认的寄存器规格、内核及中断信息 | 寄存器说明、SVD、来源记录和校验报告 |
| Keil PACK 集成 | SVD、头文件、启动/system 文件、已有 FLM、内存布局 | PDSC、入包清单、PACK、工具检查日志和已知缺项 |
| 工程验证与问题排查 | 可复现工程、工具版本；涉及硬件时提供相应测试条件 | 约定范围内的诊断、修正及复测记录 |
| 使用培训与流程交接 | 团队现有流程和培训目标 | 操作演示、维护说明和交接材料 |

新开发 Flash 算法、实机验证及复杂寄存器结构适配需单独评估，不默认包含在基础转换中。交付报告区分格式检查、工具检查、工程编译和实机验证，未执行的项目明确注明。

### 如何咨询

在 [GitHub Issues](https://github.com/xiatianxiatianyaya/keil-pack-builder/issues/new) 提交需求概要，建议注明：

1. 希望交付哪些文件：寄存器说明、SVD、PACK，或完整工程验证。
2. 大约有多少外设、寄存器和工作表，是否存在数组、地址别名、W1C、读清零等特殊规则。
3. 已有哪些资源：FLM、启动文件、头文件、已有 PACK；Keil 和编译器版本。
4. 期望完成时间，以及可接受的预算范围（可选）。

Issues 为公开页面，请只提交非保密概要或虚构样表。私有芯片手册、完整寄存器规格和固件不应直接发布在公开讨论中；资料交换方式在确认合作范围后另行约定。

### 合作步骤

需求概要 → 评估资料与缺项 → 约定范围、费用及验收条件 → 实施与验证 → 交付和维护安排。

费用主要取决于原表规范程度、特殊寄存器语义、已有设备资源完整性及验证范围。当前不设置统一报价，也不承诺固定响应时间。
