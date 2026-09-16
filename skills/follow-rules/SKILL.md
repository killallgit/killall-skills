---
name: follow-the-rules
description: Core programming rules for all agents and users alike. The following documents contain the most important, fundamental, rules that every engineer - junior to principle - MUST follow.
---

# Programming Commandments (non-negotiable)

# **important, <IMPORTANT>, MUST, <ALWAYS>, ALWAYS** follow the following rules when writing ANY code.

## 1. If the code can be simplified, simplify it.
- We are not creating software to land rovers on the moon. Do not write code to pass this kind of review.

## 2. If the code can be deleted, delete it.
- Git exists for a reason. There is no reason to save text that has already been saved and isn't needed. 
- Follow functions, often times only a test will be calling a function which makes that code dead. Remove the function and test.

## 3. Code should be self documenting. Do NOT add unnecessary comments that describe what the code already describes.

Examples for each of the following languages: [python](./references/python-example.md), [golang](./references/go-example.md), [rust](./references/rust-example.md), [typescript](./references/typescript-example.md)

## 4. Never, under any circumstances take agent information at face value. ALWAYS validate, verify, and test. When working with other agents, assume they are junior developers with zero experience or knowlege of company requirements. Double check their work.

## 5. Code should read like prose.

- How you name variables, functions and how you organize files and write your tests all tell a story about the purpose of the code. Constantly ask yourself, "if i were reading this for the first time, start to finish, would i understand what this is doing in a day?"
- Code can be complex, the goal is to reduce the amount of time it takes someone to understand and work with the code. Optimization is important but when it comes at the cost of understanding, think about how you're telling the story.

# More flexible rules (but still important)

- Program to interfaces, methods should be open for extension not for modification.
- Avoid using global, mutable variables. There are very few circumstances where this is acceptable and you must ALWAYS confirm with the user and provide a clear reason why you want to build in this way. Encapsulate!
- Favor configuration/context objects over many arguments: Use imutable data classes or objects where possible. 
- Avoid passing more than 3-4 arguments to a function. This is not a hard rule but generally should be followed.
- Follow functional programming paradigms: Use pure functions, composability, and dependency injection.
- Follow TDD principles when programming.
- Do NOT, assert on logs, error message strings, or strings in general unless theres a very good reason for this. If you want to assert that an exception was raised, assert on the concrete exception type itself. If you cant do this easily that's a 'code smell' and a refactor might be warranted.
- Functions, methods should do a single thing. They should be named descriptively and you should have many of them. If it makes sense to have a single function in a single module, do that. 
- When you feel like you need a "utility" this is an indication that you dont have your domains defined well enough. Of course there are execptions but consider the pattern.
- Linting and typechecking need to always be green before code both pushes to a remote and through CI pipelines. 
- If a change we put in triggers a latent issue with a test, linting, or typecheck that has nothing to do with the code we were touching, we stop and fix it. The exception here is when we need to move quickly. Look for a parallel agent to fix this.
- Documentation goes stale quickly. Avoid documenting at a detal that tends toward stale. Always be looking to improve the documentation before our work.
- Separate unit tests from integration tests. Integration tests should be kept separately runnable. Tests need to follow the latest best practices for the test harness being used. Make sure your tests use DI and are functional
- Test function comments should describe the assertion and the test should follow the 3 A's of testing: Assemble, Act, Assert.
