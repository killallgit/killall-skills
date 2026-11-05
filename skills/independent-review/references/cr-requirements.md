# Requirements for running Code Rabbit in github

1. ***IMPORTANT***: Identify whether or not a review is required! Here is a non-exahustive list of when NOT to run coderabbit (or any other reviewer (unless explicitly asked to do so.)) 
  - Does the code change warrant a review in the first place? 
  - Is the change simply cosmetic? 
  - Does the change substantially alter logic or functionality? 
  - Is the change small enough that a faster, local review pass would suffice?
  - Are the files changed included in any reviewer ignore file, i.e. `coderabbit.yml`?
  - Are the changes only documentation?
2. Coderabbit must be available to run! Is it installed for the repo? Does it still have quota available? Is it the preferred reviewer for this project (another context instruction explicitly says so)
3. It has not already been ran. Once coderabbit has reviewed a PR, do not trigger another Code Rabbit review after the first pass of issues is resolved unless explicitly asked to do so.
4. Does another available reviewer exist that was asked for previously. Example: The current context has asked one or more times to review with another agent/skill/tool like ponytail-review and it's clear that this is the standard (for now).
