# solidworks-automation-skill 能力测试报告

测试日期：2026-09-03。范围是只读源码审计与独立手工真机测试；未修改任何仓库核心代码。

## 1. 环境

| 项目 | 结果 |
|---|---|
| 工作目录 | `D:\LocalFile\DeskTop\sw` |
| 操作系统 | Windows 11 家庭中文版 10.0.26100，64 位 |
| Python | 3.14.5，`C:\Python314\python.exe` |
| pywin32 / COM | `win32com`、`pythoncom`、`comtypes` 均可导入；`scripts/sw_preflight.py` 通过 |
| SolidWorks | SOLIDWORKS 2024 SP04 中文版；COM Revision `32.4.0`；安装于 `D:\SW2024\SolidWorks2024\SOLIDWORKS\SLDWORKS.exe` |
| 工程图 PDF 审查依赖 | 本测试仅安装了项目声明的 `PyMuPDF 1.28.2`；未安装 OCP、ezdxf、FEA 等无关可选依赖 |

`cad_studio.py doctor` 检出 SolidWorks/COM 正常；其余 `ezdxf`、OCP、CalculiX 缺失不阻断本次原生 SolidWorks 建模与 PDF 测试。

## 2. 仓库版本

| 项目 | 值 |
|---|---|
| 仓库 | `https://github.com/wzyn20051216/solidworks-automation-skill` |
| 本地路径 | `D:\LocalFile\DeskTop\sw\solidworks-automation-skill` |
| Branch | `main` |
| Commit | `c7ba77fe1207b3881d36876c1abf128aa5e13056` |
| 工作树 | 初始干净；本测试仅新增未跟踪的 `tests/manual/plate_20260903/` |

## 3. 能力矩阵

“已实测”指本机 SW2024 的本轮真实 COM 调用；“已实现”仅代表源码中存在封装，尚未在本轮单独验收。

| 能力 | 结论 | 实际文件 / 函数 | 证据或限制 | 难度 |
|---|---|---|---|---|
| 新建零件 | 已实测通过 | `scripts/sw_session.py::new_part` | 生成 SLDPRT | 低 |
| 草图 / 矩形 / 圆 | 已实测通过 | `scripts/sw_part.py::sketch, sketch_rectangle, sketch_circle` | 草图自动尺寸 `AutoDimension2` 返回 0 | 低 |
| 拉伸凸台 | 已实测通过 | `sw_part.py::extrude_boss` | Feature Tree 为 `Base_100x60x20` / `Extrusion` | 低 |
| 拉伸切除 | 已实测通过 | `sw_part.py::extrude_cut`; `sw_hole_features.py::create_through_hole` | 5 个贯穿切除特征 | 低 |
| 旋转 | 已实现，未单测 | `sw_part.py::revolve_boss` | 没有本轮真机回归 | 中 |
| 普通孔 / 孔位批量 | 已实测通过 | `sw_hole_features.py::create_through_hole, create_hole_pattern` | Ø20×1、Ø8×4 均由 B-Rep 回读 | 中 |
| 线性 / 圆周阵列 | 已实现，未单测 | `sw_part.py::linear_pattern, circular_pattern` | 本轮孔阵列是 `create_hole_pattern` 的逐孔创建，不是原生 Pattern 特征 | 中 |
| 圆角 | 已实测通过 | `sw_part.py::fillet`; CNC 子技能 `select_exact_edges` | Feature Tree 回读 `Fillet_R5`；外圆柱面半径 5 mm | 中 |
| 倒角 | 已实测通过 | `sw_part.py::chamfer`; CNC 子技能语义选边 | Feature Tree 回读 `Chamfer_C2x45`；参数值不具备通用 FeatureData 复核 | 中 |
| 读取已有 SLDPRT | 已实测通过 | `sw_session.py::open`, `sw_connect.py::open_document` | 保存、关闭后以只读方式重开 | 中 |
| Feature Tree 读取 | 已实测通过 | `sw_review.py::collect_model_summary` | 回读 31 项树节点和特征类型 | 中 |
| 几何 / 孔读取 | 已实测通过 | `sw_review.py::collect_geometry_measurements, validate_hole_positions` | 包围盒和 5 个内圆柱面准确；通孔状态仅能由创建证据证明 | 中 |
| 工程图创建 | 已实测通过但不可交付 | `sw_session.py::new_drawing`; `drawing_workflow.py::setup_current_sheet_as_a3` | 已生成 SLDDRW、A3 图幅 | 中 |
| 主/俯/左三视图 | 部分通过 | `drawing_workflow.py::create_adaptive_standard_views` | 3 视图存在；结构审查确认主视与左视重叠 | 中 |
| 自动模型尺寸 | 部分通过 | `drawing_workflow.py::insert_dimensions, auto_arrange_drawing_dimensions` | 10 个真实尺寸实体；最终 PDF 仅可读 2 个数字文本，未满足所需完整标注 | 高 |
| 中心标记 | 已实测通过 | `drawing_workflow.py::auto_insert_center_marks` | 前视图回读 5 个 `center_mark` 实体 | 中 |
| 中心线 | 未实现为通用写入流程 | 审查器能读 `center_lines`，未发现创建函数 | 无中心线产物 | 高 |
| 剖视图 | 低层入口，未完成 | `drawing_workflow.py::add_section_view` | 仅封装 `CreateSectionViewAt5`；没有剖切线创建/选择高层 API | 高 |
| PDF 导出 | 已实测通过 | `drawing_workflow.py::export_sheet_to_pdf` | PDF 存在、PyMuPDF 能读取矢量文字框 | 低 |
| DXF | 失败 / 挂起 | `sw_export.py::export_to_dxf` | 调用后无返回、无 DXF，测试进程在 >50 秒后停止 | 中 |
| DWG | 未执行 | `sw_export.py::export_to_dxf(.dwg)` | DXF 挂起后流程未到达；不能宣称支持 | 中 |
| SLDDRW 保存 | 已实测通过 | `SolidWorksSession.save` | 文件存在且可重开审查 | 低 |
| MCP | 已实现，未接入实测 | `mcp-server/server.py` | 含 `solidworks_create_basic_part/open_document/generate_drawing/inspect_drawing/create_hole_feature` 等工具；本机缺 `mcp,pydantic`，本轮未启动服务 | 中 |

## 4. 3D 建模测试

测试脚本：[run_plate_capability_test.py](run_plate_capability_test.py)。所有建模通过仓库已有 `sw_session`、`sw_part`、`sw_hole_features`、`sw_review` 及 CNC 子技能的语义选边函数完成；没有另写独立 COM 封装。

生成件：[plate_100x60x20.SLDPRT](artifacts/plate_100x60x20.SLDPRT)。模型审查报告为 [plate_review_report.json](artifacts/part_review/plate_review_report.json)，其规则评分为 `pass / 100`，并已输出四视预览。

验证结果：

- B-Rep 包围盒：100.0 × 60.0 × 20.0 mm。
- 内圆柱面：Ø20×1，中心 (0,0)；Ø8×4，中心为 (±40, ±20) mm；孔壁轴向长度均为 20 mm。
- Feature Tree 包含 `Base_100x60x20`、`ThroughHole_D20`、`CornerHole_D8_1..4`、`Fillet_R5`、`Chamfer_C2x45`。
- `auto_dimension_sketch` 返回 `status_code=0`，没有草图 API 异常。它证明自动尺寸调用成功，但不等价于严格“完全定义”状态回读；项目没有本轮使用的完整自由度审计器。
- R5 得到 Feature Tree 与 4 个外圆柱面（半径 5 mm）双重证据。C2×45 有 Feature Tree 及创建参数证据；尚未有项目通用的 ChamferFeatureData 参数回读器。

## 5. 工程图测试

生成 [plate_100x60x20.SLDDRW](artifacts/plate_100x60x20.SLDDRW) 和 [plate_100x60x20.pdf](artifacts/plate_100x60x20.pdf)。工程图结构回读：A3 图幅、3 个视图、10 个尺寸实体、5 个中心标记。

但工程图不合格：`review_drawing_layout` 确认 `DRAWING_VIEW_OVERLAP`（主视与左视）且报告 6 项估算尺寸碰撞风险。渲染 PDF 也显示左侧尺寸被裁切、图面绝大部分空白；PDF 只提取到 `0.00` 与 `R5.00`，所以未验证 Ø20、4×Ø8、100、60、20 的可读与正确标注。

未创建剖视图。`add_section_view(drawing,x,y)` 需要先由调用方创建并选择剖切线，而项目未提供对应的高层流程；不能把这个低层入口视作剖视图自动化已通过。

## 6. 导出测试

| 格式 | 结果 | 产物 / 备注 |
|---|---|---|
| SLDPRT | 通过 | 103,039 bytes，可重开 |
| SLDDRW | 通过 | 52,036 bytes，可由项目审查器读取 |
| PDF | 通过但图面不合格 | 18,833 bytes；无文字重叠，但标注不完整、布局重叠 |
| DXF | 失败 | `export_to_dxf(drawing, ...plate_100x60x20.dxf)` 挂起，无文件 |
| DWG | 未执行 | DXF 挂起中断了后续调用 |

## 7. 成功能力

- 基于脚本的基础零件、草图、拉伸、贯穿切除、普通孔和逐孔孔位阵列。
- 语义 B-Rep 选边后创建固定 R 圆角及 2 mm、45° 倒角。
- SLDPRT 保存/重开，Feature Tree 枚举，包围盒、内圆柱面、孔径/孔轴线读取。
- 创建并保存 A3 SLDDRW、三视图、中心标记、模型尺寸实体，以及 PDF 导出。

## 8. 失败能力

| 调用 | 输入 | SolidWorks 返回 / Python 异常 | 判断 | 建议 |
|---|---|---|---|---|
| `select_exact_edges(vertical_corner_predicate(0,20,...))`（首次） | 模板假定 Z=0..20 | `expected=4, actual=0` | 测试参数坐标假定错误，不是 Skill 缺失；本机草图拉伸为 Z=-20..0 | 先从 B-Rep 读取坐标；修正为 `-20..0` 后 R5 成功 |
| 测试结果 JSON 写入（首次） | 含 COM 对象的 kwargs | `TypeError: CDispatch is not JSON serializable` | 独立测试记录器 Bug，不是仓库 Bug | 测试记录使用 `default=str` |
| `sw_export.export_to_dxf` | 已生成的 SLDDRW → `.dxf` | 无返回、无异常、>50 秒无日志；为避免占用会话而停止测试 Python 进程 | 真实失败；原因尚不能区分为 SW2024 API 兼容性、文件导出选项/模态对话框或封装 Bug | 在独立 SW 实例上加 COM 超时与 `SaveAs` 错误/警告码记录；先审查 SW2024 DXF/DWG ExportData 参数；不能以 `.dwg`→同一函数映射替代回归 |
| `add_section_view` | 无预选剖切线 | 未形成剖视图产物 | Skill 缺少端到端高层能力 | 增加剖切线草图、视图选择、`CreateSectionViewAt5`、重开回读及位置布局封装 |
| 完整尺寸/孔标注 | `insert_dimensions` 自动导入 | 10 个实体，但 PDF 仅 2 个可读文字；未包含孔标注 | 能力不足，非成功 | 引入按 ModelItem/DisplayDimension 选择的指定尺寸与孔标注 API，并以 PDF/BMP 验收 |

## 9. Bug / API 问题

1. `create_adaptive_standard_views` 返回后仍产生真实视图重叠。布局参数不能视作交付保证；必须执行 `review_drawing_layout`，并在失败时重新布局或阻断。
2. `inspect_drawing_structure` 的视图 `scale` 回读为极小非正规数，说明 COM 属性读取或元组解释存在兼容性问题；本轮不能据此确认比例值。
3. PDF/BMP 审查能发现风险，但没有自动修复布局。工程图能力应维持 `pilot`，不能作为无人值守工程图交付。
4. `sw_export.py` 把 `.dwg` 映射到 `export_to_dxf`；本机 DXF 已挂起，DWG 更没有实测证据。
5. 当前几何检查能可靠读取包围盒、圆柱孔和 Feature Tree；对倒角的角度/距离、圆角类型、草图完全定义状态没有通用的独立参数回读。

## 10. 对后续 3D → 2D 自动工程图项目的可复用部分

### A. 可以直接复用

- `SLDPRT` 打开/保存：`sw_session.py`、`sw_connect.py`。
- Feature Tree：`sw_review.collect_model_summary`。
- 几何特征基础读取：`collect_geometry_measurements`、`validate_hole_positions`，适合包围盒、圆柱孔、孔轴线/孔径。
- Drawing 创建与标准视图的底层创建：`drawing_workflow.py::setup_current_sheet_as_a3`、`create_adaptive_standard_views`。
- PDF 导出：`export_sheet_to_pdf`，但必须接后续视觉验收。

### B. 需要二次封装

- 自然语言：VibeCAD 目前产出计划，不是可靠的“自然语言直接执行器”；需要参数澄清、计划→特征调用编排和失败恢复。
- 圆角/倒角：CNC 子技能的 B-Rep 语义选边有价值，但需消除坐标系假定，并补 FeatureData 参数回读。
- 标准视图：必须将创建、边界回读、碰撞检测、自动重新排布组成闭环；本轮现有实现生成了重叠图。
- 尺寸标注：现有 `insert_dimensions` 只能导入模型已有尺寸，不能保证指定的 100/60/20、Ø20、4×Ø8 被放在正确视图并无碰撞。
- PDF/DXF/DWG：PDF 可用但质量门禁必须保留；DXF/DWG 需单独做超时保护和版本回归。

### C. 必须自己开发

- 端到端剖视图：剖切线生成、选择、创建、命名、布局与尺寸标注。
- 针对孔的标准孔标注/孔表，以及保证 4×Ø8 和 Ø20 的规格、数量、位置均可制造表达。
- GB/T 图框字段、标题栏、中心线、尺寸链、GD&T 和面向制造的图纸排版策略。
- 工程图自动修复循环：检测重叠后改变比例/位置/尺寸文字位置，重导 PDF 并进行视觉回归。
- 对圆角、倒角、孔深/通止、草图自由度的结构化、跨版本稳定 FeatureData 读取。

## 复现步骤

1. `py scripts/sw_preflight.py`
2. `py scripts/cad_studio.py doctor`
3. `py scripts/sw_capability_probe.py --output tests/manual/plate_20260903/capability_probe.json`
4. `py tests/manual/plate_20260903/run_plate_capability_test.py`
5. 对已落盘工程图运行 `inspect_drawing_structure`、`review_drawing_layout` 与 `inspect_pdf_text_layout`；将 PDF 渲染为 PNG 后人工检查。

本轮第 4 步在 DXF 导出挂起前已产生 SLDPRT、SLDDRW 和 PDF；不要把该脚本的零退出码视为工程图合格。最终判定以本报告的结构/视觉复核为准。
