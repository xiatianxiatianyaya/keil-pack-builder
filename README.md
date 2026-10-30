# Excel 寄存器表到 Keil PACK

通用 Codex Skill：将 Excel 寄存器规格转换为可追溯的寄存器说明和 CMSIS-SVD，再结合项目已有的设备资源制作 Keil/CMSIS PACK。

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
