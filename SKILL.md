---
name: soildworks-main-skill
description: 从结构化正交三视图重建简单机械零件，并规划经验证的 3D→工程图流程 / Reconstruct simple mechanical parts from structured orthographic views and plan validated 3D-to-drawing workflows. Use only through this project's external-backend adapter boundary.
---

# soildworks-main-skill

## 项目边界 / Ownership boundary

本 Skill 是工程推理层，负责投影理解、特征假设、重建/工程图计划与验证。不得把第三方 `wzyn20051216/solidworks-automation-skill` 描述为本项目或自有 Skill。

This Skill is the engineering-reasoning layer. It owns projection understanding, feature hypotheses, reconstruction/drawing plans, and validation. Never describe the third-party `wzyn20051216/solidworks-automation-skill` as this project or as an owned Skill.

该仓库仅可作为**外部 SolidWorks 自动化后端**使用。不得复制其大规模源码；应通过依赖、配置的 checkout、adapter、import 或 CLI/subprocess 集成。需要的外部能力缺失时，先记录为 `UPSTREAM_GAP`，再添加最小本地兼容补充。

Treat that repository only as an **external SolidWorks automation backend**. Do not copy its broad source tree. Use a dependency, configured checkout, adapter, import, or CLI/subprocess integration. Record a missing required external capability as `UPSTREAM_GAP` before adding a minimal local supplement.

## 三视图重建流程 / Reconstruction workflow

对于标准且无歧义的正交投影输入：

1. 解析为 Projection Graph；投影坐标映射必须集中在单独模块。
2. 运行一致性检查；尺寸冲突时，在调用后端前返回 `INPUT_INCONSISTENT`。
3. 生成可审计的 Feature Hypotheses；孔、凸台或凹槽证据不足时返回 `AMBIGUOUS`，不得猜测。
4. 将已确认特征转换为后端无关的 Modeling Plan。
5. 仅通过 `backends/solidworks_automation` 执行。
6. 验证保存/重开后的模型几何、Feature Tree 与 B-Rep。
7. 重新生成标准视图并执行当前可用的最高级别闭环验证，准确陈述限制。

For standard, unambiguous orthographic inputs: parse a Projection Graph with centralized coordinate mapping; fail dimension conflicts as `INPUT_INCONSISTENT`; keep alternative feature hypotheses as `AMBIGUOUS`; compile confirmed features to a backend-neutral Modeling Plan; execute only through `backends/solidworks_automation`; validate saved/reopened geometry, Feature Tree, and B-Rep; then regenerate views and run the highest available round-trip validation level with precise limitations.

## 工程图流程 / Drawing workflow

Drawing Plan、布局、尺寸/注释计划、剖视图处理和 Drawing QA 必须独立于后端。可制造且无重叠的工程图需要最终验证门禁；API 成功返回并不等于交付合格。

Keep Drawing Plan, layout, dimension/annotation planning, section handling, and drawing QA independent of the backend. A non-overlapping, manufacturable drawing requires a final validation gate; a successful API return is insufficient.

修改后端 adapter 前阅读 [docs/upstream_integration.md](docs/upstream_integration.md)；新增或执行 benchmark 前阅读 [docs/benchmark_spec.md](docs/benchmark_spec.md)。

Read [docs/upstream_integration.md](docs/upstream_integration.md) before changing the backend adapter. Read [docs/benchmark_spec.md](docs/benchmark_spec.md) when adding or running a benchmark.
