# CHANGE_LOG

### 2026-03-18  - 修改: 修改文件结构 （人为修改）

- 修改: book文件夹下设置三个子文件: `prompt`, `rawjson`, `stdjson`
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

 
