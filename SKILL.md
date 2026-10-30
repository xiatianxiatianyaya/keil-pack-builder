---
name: keil-pack-builder
description: Convert Excel register specifications into checked register descriptions and CMSIS-SVD, then create, update and validate Keil/CMSIS device family packs (DFP) using PDSC, supplied Flash algorithms and startup resources. Use for Excel-to-SVD-to-PACK workflows and PACK authoring; ordinary application debugging alone is outside this skill.
---

# Excel 寄存器表到 Keil PACK

交付可追溯的设备支持包和验证记录。通用脚本不含芯片寄存器、Flash 算法或厂商资源；芯片事实取自用户工程和已确认文档。

## 从 Excel 开始

输入是寄存器 Excel 时先读 [Excel 转换约定](references/excel-registers.md)。先盘点原表各页、合并单元格、列名、公式、外设和寄存器层次；保留原表，在单独副本中按明确映射标准化，记录原始位置。不要直接套模板列名、擅自前向填充、丢掉不认识的列或只转换方便的外设。

`assets/registers-template.xlsx` 是带虚构 Demo 数据的格式示例，不是任何真实芯片。用真实规格替换示例后，`scripts/excel_to_svd.py` 读取标准化 XLSX，生成 `model.json`、中文表头的 `registers.md`、CMSIS `.svd` 和校验报告。逐项比对外设/寄存器/字段/枚举数量及地址、位域、复位值、访问语义；不能把未映射内容静默忽略。

```powershell
python -m pip install -r requirements.txt
python scripts/excel_to_svd.py "path/to/normalized-registers.xlsx" --out "path/to/new-register-output" --svdconv "path/to/SVDConv.exe"
```

然后按下列 PACK 流程把生成 SVD 加入 PDSC 的 `debug svd` 和 `pack-files.json`，与项目提供的 FLM、头文件、启动/system 文件一起校验打包。Excel 不能推导 Flash 算法、解锁序列、芯片保护位或启动代码。若缺少这些资源，只交付寄存器描述/SVD 和明确的 PACK 缺项，不声称产出了完整可烧录 DFP。

标准转换器仅支持普通平面寄存器。数组、cluster、derivedFrom、地址别名、读写不同枚举及 writeConstraint 需按原规格扩展模型和测试；不能为通过现有脚本而改掉真实语义。需要 Word 寄存器手册时，从相同 model.json 排版并另作布局校验，不重新手录数值。

## 工作顺序

1. 确定新建 DFP、更新版本、修复安装/下载问题或检查既有 `.pack`。先找现有 PDSC、SVD、FLM、启动文件、设备头文件、system 文件及打包脚本。不要覆盖原包或已安装版本；未要求发布时只产出本地文件。
2. 阅读 [PDSC 与资源配置](references/authoring.md)。确认内核、Flash/RAM 地址和容量、芯片名、编译器、复位与下载约束。未知值列为缺项，不能从相似芯片推断。旧包不是正确性的依据。
3. 新建时复制 `assets/dfp-template/`，填好 `.pdsc.in` 并改名为 `<vendor>.<name>.pdsc`。模板不提供假 FLM/SVD；补入真实资源和适用的 Startup 组件。
4. PDSC 同目录建立 `pack-files.json`，显式列出入包文件。脚本不递归拷贝工程。组件依赖、内存继承、编译器条件和 FLM 逻辑需人工及官方工具核对。
5. 按 [工具与验证](references/validation.md) 检查/打包。使用匹配版本的 PACK.xsd、PackChk、SVDConv 并保留日志。不能以消除警告为由删必要依赖或盲目抑制消息。
6. 检查 ZIP 根目录和文件清单，在隔离环境验证安装、新建工程及编译。实机擦写、下载/解锁按用户授权范围执行；制作 PACK 不自动授权擦除芯片、改保护/校准区或公开上传资料。

## 脚本入口

以下命令相对于本技能；项目及工具路径换为实际路径。Python 3.10+；基础检查用标准库，`--xsd` 需在当前 Python 环境安装 `lxml`。

```powershell
python scripts/pack_tool.py inspect "path/to/Vendor.Device_DFP.1.0.0.pack"
python scripts/pack_tool.py check "path/to/pack-src/pack-files.json"
python scripts/pack_tool.py check "path/to/pack-src/pack-files.json" --packchk "path/to/PackChk.exe" --xsd "path/to/PACK.xsd" -i "path/to/ARM.CMSIS.pdsc"
python scripts/pack_tool.py build "path/to/pack-src/pack-files.json" --out "path/to/new-delivery" --packchk "path/to/PackChk.exe" --xsd "path/to/PACK.xsd" -i "path/to/ARM.CMSIS.pdsc"
# 工具尚缺时显式生成待校验草稿，不代表通过发布验证
python scripts/pack_tool.py build "path/to/pack-src/pack-files.json" --out "path/to/new-draft" --draft
```

打包在临时目录复制并校验清单快照，PDSC 位于 ZIP 根目录。输出目录必须尚不存在；输出包括 PACK、校验报告和逐文件 SHA256，报告不入包。同一内容在同一 Python/zlib 环境可重复生成相同 ZIP 字节。

## 结果表述

分别报告基础检查、XSD、PackChk、SVDConv、安装/设备列表、工程编译、Flash 擦写下载和实机运行。未做写“未验证”；PackChk 返回 0 仍需审阅警告，不能等同于硬件验证通过。提供输出路径、版本、哈希、缺项和验证边界。

公开共享前核对每个文件的授权来源；不把项目手册、真实测试记录、私有固件、第三方工具二进制混入通用技能。
