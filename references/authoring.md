# DFP 编写与故障定位

| 内容 | PDSC 关联 | 核对项 |
|---|---|---|
| 包身份 | vendor/name/releases | PDSC 为 vendor.name.pdsc；PACK 为 vendor.name.version.pack；历史 release 保留，新版本在前 |
| 元数据 | description/url/license | 真实发布位置和许可证；不能把技能许可证自动套给芯片资源 |
| 芯片 | family/subFamily/device/variant | Dvendor/Dfamily/Dname 一致；正式厂商 ID 不能随意编造 |
| 内核 | processor | 内核、FPU/MPU、字节序、多处理器 Pname 对应 |
| 内存 | memory | 起始地址、长度、访问属性、startup/default；容量不是结束地址 |
| 下载算法 | algorithm | 真 FLM、start/size、工作 RAM、页大小及扇区表与硬件一致 |
| 寄存器视图 | debug svd | 基地址、偏移、位宽、枚举、中断号及读写副作用 |
| 头文件 | compile header/components | 设备宏、IRQn、CMSIS Core 依赖、include 路径 |
| 启动支持 | Device:Startup | startup/system/向量表、编译器条件；ARMCC 汇编不能直接视为所有编译器兼容 |
| 示例 | examples/project 等 | 编译器、器件、依赖包、板级引脚；复制到安装目录外构建 |

设备属性可从 family/subFamily 继承，device 下没有某项不能直接判缺失。复杂 condition、目录、示例和跨包依赖用官方工具及人工核对；附带脚本只覆盖常见直接文件引用。

## FLM 与 SVD

FLM 是编译后的 Flash 算法，改文件名/PDSC 不会修改擦写逻辑。检查算法工程、Init/UnInit、EraseSector/EraseChip、ProgramPage、FlashDevice 的页/扇区描述；具体接口以采用的算法规范为准。不能从容量推导控制器地址、解锁序列或等待时序。

实机使用专用板及已备份/可擦除区域，覆盖跨页/跨扇区编程、读回比对、复位运行。失败先区分链路、供电、工作 RAM、写保护，不能自动升级为整片擦除。

SVD 语法正确不等于硬件正确。对照寄存器表检查 derivedFrom、数组步进、access/readAction/modifiedWriteValues，尤其读清和写 1 清除字段。

## 常见故障

- 找不到芯片：查 Pack Root、设备名称、schema/版本、ZIP 是否多套一层目录。
- 没有 Startup：查组件、文件、条件与 CMSIS 依赖；devices 节点本身不提供完整工程支持。
- FLM/SVD 缺失：查大小写、相对路径、入包清单；Windows 上能打开不代表大小写正确。
- 下载失败：查 Flash 范围、工作 RAM、供电/SWD、写保护，不能借用另一芯片算法替代。
- 本机能编译别人不能：干净目录、独立 Pack Root 验证，消除绝对工作区路径。

## 官方依据（2026-10-30 核对）

- [Pack Creation](https://open-cmsis-pack.github.io/cmsis-toolbox/pack-tools/)
- [Open-CMSIS-Pack 规范](https://open-cmsis-pack.github.io/Open-CMSIS-Pack-Spec/main/html/index.html)
- [官方 DFP 示例](https://github.com/Open-CMSIS-Pack/DFP-Pack-HandsOn)；使用前核对许可证及工具版本。
