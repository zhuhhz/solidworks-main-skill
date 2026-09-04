# Testing / 测试规范

## Canonical entrypoint / 统一入口

当前 Windows 环境没有把 `pytest.exe` 所在目录加入 `PATH`。本项目所有单元测试、回归测试、benchmark 测试和集成测试统一通过 Python 模块入口执行：

```powershell
python -m pytest
```

The directory containing `pytest.exe` is not on `PATH` in the current Windows environment. Use the Python module entrypoint for every unit, regression, benchmark, and integration test.

## Common commands / 常用命令

运行单个测试文件：

```powershell
python -m pytest tests/unit/test_projection_graph.py
```

运行单个测试函数：

```powershell
python -m pytest tests/unit/test_projection_graph.py::test_xxx
```

显示详细测试条目：

```powershell
python -m pytest -v
```

立即显示标准输出：

```powershell
python -m pytest -s
```

同时启用详细条目与即时输出：

```powershell
python -m pytest -v -s
```

除非后续明确验证 pytest PATH 已配置，否则项目文档、执行脚本和 Codex 操作记录不得使用裸 `pytest` 或 `pytest.exe` 作为测试入口。安装依赖时出现包名 `pytest` 不属于测试入口调用，不需要改写。

Unless pytest PATH availability is later explicitly verified, project documentation, execution scripts, and Codex run records must not use bare `pytest` or `pytest.exe` as a test entrypoint. The package name `pytest` in dependency-install commands is not a test invocation and remains unchanged.
