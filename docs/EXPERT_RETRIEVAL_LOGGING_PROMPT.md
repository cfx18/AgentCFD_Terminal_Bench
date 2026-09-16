# Retrieval decision log — proposed public prompt fragment

中文说明：新实验候选片段；要求查询前说清目标和关键词，查询后列出确实采纳的知识及影响。
没有记录、没有读到、没有采纳都可以如实说明。不是让模型补造完整思维链。

Status: proposed for a new experiment version; NOT injected into the historical Fable trials.

Use the normal tools and submission schema. Provide a brief, public decision log around
each documentation/search/read operation. Do not provide private internal chain-of-thought.
This log is for audit, not a new grading criterion, and does not give access to hidden references.
Write these concise public logs in Chinese; keep exact keywords, identifiers and technical names unchanged.

Before searching, state in 1–2 sentences:

- **Question:** the specific uncertainty you need to resolve.
- **Search:** the tool/source and exact keyword(s), filters, or document identifier you will use.

After receiving the result, state briefly:

- **Useful evidence:** which returned document ID/title and passage you actually used,
  and the specific knowledge it supplies. If none is useful, say so.
- **Decision:** what this evidence changes in the next action, or why you will not use it.
- **Remaining uncertainty:** what the source did not establish; distinguish retrieval
  from prior knowledge or inference. Do not imply that you read a page you only searched.

If a call fails, is truncated, or is rejected before execution, state that no new observation
was obtained. Proposing a read is not completing a read. If you clip a tool output,
acknowledge that only part of the result was inspected.

Keep logs concise. Do not invent a citation, tool result, or inferred selection merely to
fill this template. No requirement to search when existing information is sufficient.
