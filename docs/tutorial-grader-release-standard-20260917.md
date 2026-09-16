# Tutorial Grader 发布标准（2026-09-17）

本标准用于把 100 个 OpenFOAM tutorial-derived candidate 从“LLM 生成的题面/草案”
推进到“可发布 grader”。LLM 可以参与阅读材料和生成字段建议，但不能单独决定发布。

## 分层结论

每个 task 同时记录两层状态：

1. `release_status`
   - `released`：可进入正式 leaderboard。
   - `review`：有可执行 grader 或接近完整，但仍需专家/溯源审查。
   - `blocked`：缺 input、GT、schema、grader，或存在 fatal blocker。

2. `grader-review.json:decision`
   - `released_candidate`：所有 gate 通过且无 blocker，等待最终发布确认。
   - `review`：程序可跑，但仍有非致命科学/溯源问题。
   - `blocked`：缺证据、缺 grader、GT 不可靠或物理 admissibility 问题。

## LLM 负责什么

LLM/草案材料可以提供：

- instruction 是否清楚；
- 哪些字段是 `core_fields` / `primary_fields` / `scored_fields`；
- 哪些字段只是 diagnostic；
- blocker 和 warnings 的自然语言整理；
- rubric 草案和 normalizer 建议；
- 人类可读 review。

当前实现优先读取 `public/rubric.json` 中的 `target`、`core_fields`、
`primary_fields`、`scored_fields`、以及带 `scored_target` role 的字段。
如果没有这些结构化建议，才 fallback 到 CSV 字段推断。

## 程序 gate 负责什么

程序必须独立检查：

- `query_ok == true`
- `input_complete == true`
- `gt_available == true`
- 存在可执行 metric grader；
- 存在非空 scored fields；
- 存在 frozen reward anchors；
- reference CSV 自测能得到 `reward=1.0`；
- 缺字段、NaN、行数不一致必须失败；
- fatal blocker 不能被 LLM 覆盖。

## 当前 reward 标准

本轮采用统一 dense reconstruction 标准：

- normalized RMSE ≤ 5% 且 normalized max error ≤ 20%：满分；
- normalized RMSE ≥ 30% 或 normalized max error ≥ 100%：零分；
- 中间线性插值；
- 总分取所有字段和指标中的最差值，避免一个字段严重错误被平均掩盖。

该标准只说明“候选输出是否重建了有限数值参考”，不宣称参考本身是
mesh-converged、实验验证或物理唯一解。

## 当前 v4 结果

发布目录：`tasks/releases/tutorial-grader-v4`

| 项目 | 数量 |
|---|---:|
| 总 task | 100 |
| 有可执行 metric grader | 8 |
| `release_status=review` | 8 |
| `release_status=blocked` | 92 |
| `grader-review decision=review` | 3 |
| `grader-review decision=blocked` | 97 |
| clean `released` | 0 |

8 个有 grader 的 task 均通过 self-reference：

```text
q-0051 pass 1.0
q-0064 pass 1.0
q-0094 pass 1.0
q-0131 pass 1.0
q-0146 pass 1.0
q-0176 pass 1.0
q-0291 pass 1.0
q-0505 pass 1.0
```

但其中只有 `q-0094`、`q-0146`、`q-0176` 当前属于 review 级别；
其余仍有 fatal provenance、GT 或 physical-admissibility blocker。

## 不能做的事

- 不能因为 LLM 说“可以”就把 `review/blocked` 升级为 `released`。
- 不能把旧的 draft rubric 当正式 grader。
- 不能静默丢弃 92 个 blocked task；它们必须保留在 manifest 分母和状态表中。
- 不能把 self-reference 满分解释成模型能通过，只能说明 grader 能识别自己的 GT。
