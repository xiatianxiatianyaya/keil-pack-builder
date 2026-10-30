# 工具与验证

先查工程工具路径，其次 PATH、Keil 目录和 Pack Root 内 ARM/CMSIS 的 Utilities。UV4 存在不代表有 PackChk/SVDConv。先读所用工具的 `--help` 或 `-h` 并记录版本；**PackChk 的 `-s` 在不同版本含义不同**，不能把旧版 SVD 开关照搬成新版 schema 参数。

封装仅传 `packchk <pdsc> -i <dependency.pdsc>`，不猜其他参数。依赖 PDSC 保留原资源目录。执行超时即失败，不无限重试。

`--xsd` 通过 lxml 验证本地 PACK.xsd（禁用网络），与 PackChk 分开记录。XSD 的本地 include/import 需保留。不要为消除错误盲目降低 schemaVersion。

推荐在虚拟环境安装 `requirements.txt` 中的依赖；Excel 读取需要 openpyxl，XSD 检查需要 lxml。基础 PACK 检查和草稿打包仅用标准库。离线回归命令：`python -m unittest discover -s scripts -p "test_*.py" -v`。这些测试用合成数据，不调用仪器、不写芯片。

## 清单与命令行为

`pack-files.json` 与 PDSC 同目录，结构见 assets/dfp-template。files 是明确文件列表，无 glob 或递归目录；路径用 `/`，大小写精确。清单通常不入包。

- inspect：只读 ZIP/PDSC，检查重复路径、危险路径、根目录 PDSC，不解压/安装/执行；不代表内容完整。
- check：基本 XML、身份/版本、常见引用与清单检查；可选 XSD/PackChk。JSON 输出，失败退出非零。
- build：复制清单快照后校验并生成 ZIP/报告。输出目录不得存在，避免覆盖。正常模式要求 XSD/PackChk 均通过。显式 `--draft` 可跳过缺失工具，但不绕过已发现错误。
- 草稿不改变 PDSC 版本或标准 PACK 命名，在输出目录及报告标识未完成验证，不可声称可发布。
- 原样保存官方工具 stdout/stderr；返回 0 仍需审阅警告。

基础检查不覆盖所有 CMSIS 元素、复杂 condition、继承语义、FLM 可执行性、SVD 寄存器正确性或许可证兼容性。

## 验证记录

| 层次 | 应记录证据 |
|---|---|
| 基础检查 | errors/warnings、逐文件哈希 |
| XSD | schema 路径/哈希、结果 |
| PackChk | 工具路径/哈希、依赖 PDSC、返回码/日志、警告处理 |
| SVDConv | 实际版本/参数/日志；没运行写未验证 |
| 安装 | Keil/Pack Installer 版本、Pack Root、器件可选 |
| 构建 | 编译器/版本、干净构建日志、链接内存范围 |
| 实机 | 板号/电压/调试器、擦写读回/复位运行；不上板不能填通过 |

资料：[现代工具](https://open-cmsis-pack.github.io/cmsis-toolbox/pack-tools/)、[旧版 PackChk](https://arm-software.github.io/CMSIS_5/5.8.0/Pack/html/packChk.html)、[官方 gen-pack](https://github.com/Open-CMSIS-Pack/gen-pack)。已有成熟流水线优先沿用，附带脚本适合简单显式清单。
