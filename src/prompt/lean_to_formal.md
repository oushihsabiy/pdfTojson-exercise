You are given a JSON array of optimization problems. Each JSON object contains fields such as "index", "source_idx", "source", "题目类型", "预估难度", "problem", "proof", and "direct_answer".

Your task is to rewrite only the value of the "problem" field.

Goal:
Convert the current "problem" field, which may be written in a Lean-oriented or formally segmented style such as "Definition:", "Hypothesis:", and "Goal:", into a logically smooth, concise, and clear natural-language standard mathematical problem statement.

Domain:
All problems are exercises in optimization. Rewrite the statement in the style commonly used in optimization textbooks, homework sets, or mathematical exercise collections.

Requirements:
1. Modify only the "problem" field.
2. Preserve all other fields exactly as in the input.
3. Do not solve the problem.
4. Do not add proofs, hints, explanations, comments, or extra metadata.
5. Do not remove necessary mathematical assumptions, definitions, or constraints.
6. The rewritten "problem" must be a standard natural-language mathematical proposition/question, not a list of labeled items such as "Definition:", "Hypothesis:", or "Goal:".
7. The rewritten statement must be logically coherent, concise, and easy for a human reader to understand.
8. Keep all mathematical notation in LaTeX-compatible syntax.
9. Do not use Unicode characters; use only ASCII-compatible LaTeX notation.
10. Output must remain valid JSON.
11. Keep the original JSON structure unchanged except for the rewritten "problem" field.
12. The rewritten "problem" field must remain a JSON string.
13. Preserve the mathematical meaning exactly; improve only wording and presentation.
14. Prefer standard optimization-style phrasing such as:
   - "Let ..."
   - "Define ..."
   - "Consider ..."
   - "Is the set ... convex?"
   - "Show that ..."
   - "Determine whether ..."

Style guidance:
- Merge fragmented labeled clauses into one smooth statement.
- Present assumptions in a natural mathematical order.
- Avoid Lean-style scaffolding.
- Avoid redundant wording.
- Keep the tone formal, standard, and textbook-like.
- When the original problem defines a set and asks whether it is convex, rewrite it in the standard form:
  "Let ... . Define ... . Is the set ... convex?"
- When useful, inline simple definitions instead of listing them separately.

Example transformation style:
Input "problem":
"\\[\\begin{aligned}
&\\text{Definition: } k \\in \\mathbf{N}.\\\\
&\\text{Definition: } \\alpha, \\beta \\in \\mathbf{R}.\\\\
&\\text{Hypothesis: } \\alpha \\leq \\beta.\\\\
&\\text{Definition: } a = (a_1, \\dots, a_k) \\in \\mathbf{R}^k.\\\\
&\\text{Definition: } p : \\mathbf{R} \\to \\mathbf{R} \\text{ is defined by } p(t) = a_1 + a_2 t + \\cdots + a_k t^{k-1}.\\\\
&\\text{Definition: } S = \\{a \\in \\mathbf{R}^k \\mid p(0) = 1,\\ |p(t)| \\leq 1 \\text{ for all } t \\in [\\alpha, \\beta]\\}.\\\\
&\\text{Goal: determine whether } S \\text{ is convex.}
\\end{aligned}\\]"

Output "problem":
"Let k \\in \\mathbf{N} and let \\alpha, \\beta \\in \\mathbf{R} with \\alpha \\leq \\beta. For a = (a_1, \\dots, a_k) \\in \\mathbf{R}^k, define
\\[
p(t) = a_1 + a_2 t + \\cdots + a_k t^{k-1}.
\\]
Determine whether the set
\\[
S = \\{a \\in \\mathbf{R}^k \\mid p(0) = 1,\\ |p(t)| \\leq 1 \\text{ for all } t \\in [\\alpha, \\beta]\\}
\\]
is convex."

Return only the rewritten JSON.