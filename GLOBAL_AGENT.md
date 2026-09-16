# * IMPORTANT PROGRAMMING RULES *

1. If the code can be simplified, simplify it.
2. If the code can be deleted, delete it.
3. Code should be self documenting. Do NOT add unnecessary comments explaining files, that simply describe what is obvious about the noun. 

Example:



Every comment in this file is completely useless. Why comment the name of the file? The file name explains what it does: "self documenting code", the function is well typed and does not need to repeat what is clearly visible and why on earth would you add a comment that only wastes bytes, makes the code harder to read, and the second someone decides to rename the variable: `dead_parrots` when the business requirements change, you now have a comment that simply confuses the code.

4. Never, under any circumstances take agent information at face value. ALWAYS validate, verify, and test. When working with other agents, assume they are intern developers with zero experience or knowlege of company requirements. Double check their work.
5. Follow well established programming patterns: Program to interfaces, methods should be open for extension not for modification, and other hard won patterns that improve solid software.
6. Do NOT use global, mutable variables. There are very few circumstances where this is acceptable and you must ALWAYS confirm with the user and provide a clear reason why you want to build in this way. Encapsulate! 
7. Favor configuration objects over many arguments: Use imutable data classes where possible. Avoid passing more than 3-4 arguments to a function. This is not a hard rule but generally should be followed.
8. Follow functional programming paradigms. Pure functions, composability, and dependency injection rule. Leave classes with mutable fields to the external libraries and adapt them as quickly as possible when needed.
9. Prob the most important rule of all: NONE OF THESE RULES ARE SET IN STONE! There are always execptions to these rules. Identify when and where that might be but always point it out to the user.
10. Follow TDD principles when programming.
11. ABSOLUTELY, NEVER, EVER, UNDER NO CIRCUMSTANCES assert on logs, error message strings, or strings in general unless theres a very good reason for this. If you want to assert that an exception was raised, assert on the concrete exception type itself. If you cant do this easily that's a 'code smell'.
12. Functions, methods should do a single thing. They should be named descriptively and you should have many of them. If it makes sense to have a single function in a single module, do that. Code should read like prose.
13. There is no such thing as a "utility". A "util" is an indication that you dont have your domains defined well enough. Of course there are execptions but rarely.
14. Linting and typechecking need to always be green. If a change we put in triggers a latent issue with a test, linting, or typecheck we stop and fix it even if that means we need to get a PR in before the one we are working on. In most cases, the fix needs to be piggy-backed onto our PR and this is acceptable. If it's an aggregous issue. This is why we must always make sure our checks pass before merging.
15. Documentation goes stale quickly. Avoid documenting at a detal that will require many changes like paths to files and file names unless they are well established top level domains that are less likely to be refactored.
16. Separate unit tests from integration tests. Integration tests should be kept separately runnable. Tests need to follow the latest best practices. Use functional patterns over inheretance.
17. Test function comments should describe the assertion and the test should follow the 3 A's of testing: Assemble, Act, Assert.

Example of a good test function comment:

```python



```

In the above example i can read the comment and know exactly what is asserted. I clearly have functional code and i'm able to build a test monkey easily.

18. All tests and checks MUST be green before a PR is put in. There are some exceptions when dealing with hotfixes and time sensitive work.
19. Keep a CHANGELOG.md at the project root and always make sure it's updated when code goes in.
20. Always, always, always, make sure your PR's are up to date with their base origin branch. If you push a branch and there's merge conflicts you must fix them before anything else can happen. Again, exceptions do exist but are rare.
