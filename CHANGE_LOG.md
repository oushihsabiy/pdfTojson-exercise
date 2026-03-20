# CHANGE_LOG

### 2026-03-18  - 修改: 修改文件结构 （人为修改）

- 修改: book文件夹下设置三个子文件夹: `prompt`, `rawjson`, `stdjson`
	- 功能: `prompt`用于存储提示词，`rawjson`是先前将pdf转换为初始json文件的源代码，
		`stdjson`是将初始json文件转换为lean_friendly文件的源代码。

- 添加: `stdjson`下设置`raw_to_complete.py`以及`complete_to_lean.py`
	- 功能: `raw_to_complete.py`计划用于补全隐式条件， `complete_to_lean.py`计划用于
		优化命题叙述，使其易于翻译成lean语言。

### 2026-03-18 （助理修改）

- 添加: src/stdjson/raw_to_complete.py 
	- 功能: 使用提示词 `src/prompt/raw_to_complete.md` 和 config.json 中的 OpenAI 配置，逐条重写 JSON 练习对象的 `problem` 字段；严格校验除 `problem` 外其他字段不允许变化；支持重试与流式兼容。

### 2026-03-18  — 新增: stdjson 处理流程入口 （助理修改）

- 添加: main.py: `process_json`
	- 功能: 为生成的 JSON 文件运行 `src/<mode>/stdjson/raw_to_complete.py` 和 `src/<mode>/stdjson/complete_to_lean.py`，支持原子输出与完整性校验；在 `process_one` 之后自动触发。
 
### 2026-03-18 — 修复与加强：stdjson 运行时健壮性（助理修改）

- 修复: `src/book/stdjson/raw_to_complete.py`
	- 行为改进：当提示词文件为空时使用内置回退提示 (`DEFAULT_FALLBACK_PROMPT`)，不再直接抛出错误。
	- 重试策略：将每个练习对象的默认 `--max-attempts` 提升为 8 次以提高成功率。
	- 错误容忍：单项重写失败时记录警告并保留该题目的原始 `problem` 字段，避免中断整个批处理。
	- 响应处理：优先请求 JSON 响应格式（若后端支持 `response_format={"type":"json_object"}`），并改进对流式响应的收集与解析逻辑以提高解析鲁棒性。

- 恢复: `src/book/prompt/raw_to_complete.md`
	- 如果仓库中的提示文件被意外清空或缺失，脚本会使用内置回退提示保证管道继续运行；同时已在仓库中恢复/填充该提示文件以便可读性与可审计性。

- 结果: 这些改动使得在长期运行（多条练习）时，偶发的模型解析错误或单条失败不会导致整个管道中止，已观察到 stdjson 阶段能够继续处理后续题目并生成分段输出文件。

### 2026-03-18 - 新增: test.json （人为修改） 
- 添加: `test.json`用于测试`raw_to_complete.py`是否真正能识别隐含条件
- remark : `test.pdf`只是随便一个pdf，只是用来让程序正常运行

### 2026-03-19 - 修改文件结构 （人为修改）
- 修改: 把`src/book`重命名为`src/exercise`，因为实际上里面处理的是习题
- 修改: 把`stdjson`提到上一级目录，因为无论是`paper`,`book`还是`exercise`,
		只要得到了rawjson，剩下的步骤是一样的

### 2026-03-19 — 更新: stdjson 分阶段调整（助理修改）

- 添加: `src/stdjson/complete_to_concise.py`
	- 功能: 使用提示词 `src/prompt/complete_to_concise.md` 将每个练习对象的 `problem` 字段改写为更清晰、简练、便于形式化的表述；严格保留除 `problem` 外的所有字段不变。
- 添加: `src/stdjson/concise_to_lean.py`
	- 功能: 使用提示词 `src/prompt/concise_to_lean.md` 将 `problem` 字段重写为 `Definition/Hypothesis/Goal` 的 Lean 友好结构；严格保留其他字段不变。
- 删除: `src/stdjson/complete_to_lean.py`
	- 说明: 原有的单步 `complete_to_lean` 被拆分为两步（complete->concise、concise->lean），因此该文件已移除。
- 修改: `main.py`
	- 功能: `ensure_scripts_exist` 与 `process_json` 已更新以支持三阶段 stdjson 流程：
	  `raw -> complete -> concise -> lean`。
	- 细节: `ensure_scripts_exist` 现在查找并返回 `complete_to_concise` 与 `concise_to_lean` 两个脚本路径；
	  `process_json` 会在 `work/` 下生成中间文件 `{stem}.complete.json` 与 `{stem}.concise.json`，最终产出 `{stem}.lean.json`。
- 其它: 清理了 `src/stdjson/__pycache__`，并对新增脚本做了语法检查（`python -m py_compile`）。
- 验证: 在当前开发环境执行过一次端到端试跑：

```
python main.py --mode exercise
```

  测试运行成功启动 stdjson 阶段（已开始处理 `exercise` 模式下的练习项）。

 
