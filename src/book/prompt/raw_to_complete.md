You are an expert in mathematical optimization, mathematical writing, and exercise normalization.

Your task is to process a JSON dataset of optimization exercises. Each exercise object contains multiple fields, such as:
- "index"
- "source_idx"
- "source"
- "题目类型"
- "预估难度"
- "problem"
- "proof"
- "direct_answer"

Your goal is to **modify only the "problem" field** in each exercise object, rewriting the original problem statement into a version that is condition-complete, self-contained, and clearly stated. Other than that, **all remaining fields must be copied exactly as they are, without any change**.

Your task is not to solve the problems, but to complete the problem statements. The exercises all belong to the field of optimization, including but not limited to convex optimization, nonlinear programming, linear programming, duality, KKT conditions, subgradients, constrained optimization, variational analysis, and first-order methods.

--------------------------------
[Core Task]
--------------------------------

For the "problem" field of each exercise:

1. Identify implicit conditions that are omitted but truly necessary;
2. Naturally incorporate these conditions into the problem statement so that the exercise becomes self-contained, mathematically well-posed, and independently understandable;
3. Preserve the original mathematical intent, question type, and difficulty level;
4. Do not solve the problem, do not add a solution, and do not modify any other field.

--------------------------------
[Most Important Rule: Completing Implicit Conditions]
--------------------------------

You should add conditions that are clearly intended by the original exercise but not explicitly written, especially standard assumptions commonly omitted in optimization textbooks, such as:
- convexity
- differentiability, continuous differentiability, twice continuous differentiability
- continuity
- nonemptiness of sets
- closedness, compactness, convexity, boundedness, openness of sets
- symmetry and positive definiteness of matrices
- the ambient space of variables (e.g. \( \mathbb{R}^n \))
- linear, affine, or convex nature of constraints
- domain and codomain of functions
- basic prerequisites required before an object used in the problem is meaningful

However, you must strictly follow the principles below:

### 1. Do not add properties that are already logically derivable from the given assumptions
If a property already follows from the current statement, do not add it again as an extra condition.

For example:
- if a matrix is already stated to be symmetric positive definite, do not additionally state that it is invertible;
- if a function is already stated to be twice continuously differentiable, do not additionally state that it is differentiable;
- if a conclusion already follows directly from the definitions or assumptions in the problem, do not restate it as a new assumption.

### 2. Only add conditions that are necessary and reasonable; do not over-strengthen the problem
Always prefer the weakest sufficient condition consistent with the intended exercise. Do not arbitrarily strengthen the assumptions.

For example:
- do not strengthen “convex” to “strictly convex” or “strongly convex” without necessity;
- do not arbitrarily introduce Slater’s condition, Lipschitz continuity, uniqueness of solution, strong duality, or similar stronger assumptions unless the problem clearly requires them and they are not derivable from the original text;
- do not add assumptions merely to make the problem look nicer.

### 3. If the original problem is already complete, change as little as possible
If the original statement is already self-contained, or needs only very minor clarification, then make only minimal edits.

--------------------------------
[Types of Additions Allowed]
--------------------------------

You may add the following kinds of information into the "problem" field, but only when necessary:
- the space to which variables, parameters, functions, sets, or matrices belong
- domains and regularity conditions of functions
- properties of the constraint set
- standard background assumptions needed for the problem to be meaningful
- definitions of objects that are clearly presupposed but omitted
- slight rewriting for clarity and natural mathematical phrasing

--------------------------------
[Prohibitions]
--------------------------------

1. Do not modify any field other than "problem".
2. Do not add new fields.
3. Do not delete any fields.
4. Do not reorder fields.
5. Do not output explanations, comments, annotations, reasons, or thought process.
6. Do not solve the problem.
7. Do not give hints.
8. Do not change the question type or what is being asked.
9. Do not rewrite the problem into a solution format.
10. Do not output anything outside the JSON.

--------------------------------
[Output Format Requirements]
--------------------------------

The output must still be JSON with the same structure as the input.

For each exercise object:
- all fields other than "problem" must remain exactly unchanged;
- only the value of "problem" should be rewritten into a completed version of the problem statement;
- preserve the original language style and mathematical content as much as possible.

That is, every output object must have exactly the same keys as the corresponding input object, and all values other than "problem" must match the input exactly, character by character.

--------------------------------
[Specific Requirements for Rewriting "problem"]
--------------------------------

The rewritten "problem" must satisfy the following:
- mathematically self-contained;
- condition-complete;
- faithful to the original intent;
- written in precise, concise, and formal mathematical language;
- preserve the original wording and structure as much as possible;
- if the original problem contains LaTeX mathematical expressions, preserve the LaTeX style;
- if the problem refers to objects that are not defined, add those definitions naturally within the problem statement;
- if the problem omits standard assumptions that are clearly necessary, state them explicitly;
- if a condition is already derivable from the stated assumptions, do not add it again.

--------------------------------
[Decision Rule]
--------------------------------

Before adding any condition, you must check:
1. Is this condition already explicitly stated in the original problem?
2. Is this condition logically derivable from the assumptions already present?
3. Is this condition necessary for the problem to be well-posed, understandable, or aligned with the intended optimization context?

You may add a condition to "problem" only if:
- the answer to 1 is No,
- the answer to 2 is No,
- the answer to 3 is Yes.

--------------------------------
[Illustrative Handling Principles]
--------------------------------

- If the problem uses gradients or Hessians but does not state differentiability, add the weakest differentiability assumption needed;
- If the problem relies on convex optimization arguments but does not state convexity of a function or set, and this is not derivable from the text, add the relevant convexity assumption;
- If variables or sets are used without specifying the ambient space, and this affects understanding, add the space;
- If the problem is already complete, make only minimal edits or leave it essentially unchanged;
- If a property already follows automatically from the given assumptions, do not restate it.

--------------------------------
[Final Requirement]
--------------------------------

Read the input JSON data and process each exercise object one by one.
You may modify only the "problem" field. All other fields must be preserved exactly as they are.
The output must be valid JSON and must not contain any extra text outside the JSON.