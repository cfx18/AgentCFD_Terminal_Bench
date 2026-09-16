# Tutorial Grader v4 数据包说明

Git 仓库只保存代码、测试、发布标准、以及轻量级 release manifest。
完整数据不直接进入 Git，需单独打包上传网盘/对象存储。

## 需要单独上传的包

### 1. 发布数据包

内容：

```text
tasks/releases/tutorial-grader-v4/
```

用途：

- 100 个 task 的完整发布包；
- 8 个可执行 metric grader 的 public observations、private grading policy、review 记录；
- 92 个 blocked task 的 package 和 blocker 状态。

当前体积约 56 MB。

推荐打包命令：

```bash
mkdir -p data-packages
tar --zstd -cf data-packages/agentcfd-tutorial-grader-v4-data-20260917.tar.zst \
  tasks/releases/tutorial-grader-v4
sha256sum data-packages/agentcfd-tutorial-grader-v4-data-20260917.tar.zst \
  > data-packages/agentcfd-tutorial-grader-v4-data-20260917.tar.zst.sha256
```

### 2. 审计证据包

内容：

```text
runs/tutorial-release-completion/20260916T191015Z-sol-high-codex-experiment-c6-v1/
```

用途：

- authoring/release-completion 原始输出；
- prompt、worker result、`RELEASE_READINESS.json`、`author-result.json`；
- 之后复查 provenance、LLM 草案和 blocked 原因。

当前体积约 1.4 GB。

推荐打包命令：

```bash
mkdir -p data-packages
tar --zstd -cf data-packages/agentcfd-tutorial-grader-v4-audit-20260917.tar.zst \
  runs/tutorial-release-completion/20260916T191015Z-sol-high-codex-experiment-c6-v1
sha256sum data-packages/agentcfd-tutorial-grader-v4-audit-20260917.tar.zst \
  > data-packages/agentcfd-tutorial-grader-v4-audit-20260917.tar.zst.sha256
```

## Git 中保留的轻量文件

```text
tasks/releases/tutorial-grader-v4/MANIFEST.json
tasks/releases/tutorial-grader-v4/README.md
docs/tutorial-grader-release-standard-20260917.md
docs/tutorial-grader-v4-data-package.md
```

## 恢复方式

在仓库根目录解压：

```bash
tar --zstd -xf agentcfd-tutorial-grader-v4-data-20260917.tar.zst
tar --zstd -xf agentcfd-tutorial-grader-v4-audit-20260917.tar.zst
```

然后运行：

```bash
PYTHONPATH=. pytest -q tests/test_tutorial_grader_release.py
```

## 当前发布状态摘要

```text
task_count: 100
metric_grader_executable_count: 8
release_status=review: 8
release_status=blocked: 92
clean released: 0
```
