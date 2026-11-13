# Vocabulary

Use these words exactly. The _Avoid_ words are vague or carry baggage.

## Terms

**Module**: anything with an interface and an implementation: a function, a
file, a package, a service.
_Avoid_: component, unit, layer (as a synonym)

**Interface**: everything a caller must know to use a module: signatures,
types, ordering, errors, side effects. Not just the type signature.
_Avoid_: API (unless it is a network API), contract

**Depth**: functionality behind the interface relative to the interface's
size. A **deep** module hides a lot behind a little; a **shallow** module's
interface is nearly as complex as its implementation. (Ousterhout)

**Seam**: a place where behavior can change without editing the code around
it. (Feathers)
_Avoid_: boundary, hook point

**Adapter**: a module that translates one interface into another at a seam,
usually to keep an external library or I/O out of the domain.
_Avoid_: wrapper, shim

**Locality**: what you need to understand a change lives in one place.
**Leverage**: one change in one place does a lot of work.

**Hotspot**: a file that is both large and changed often. **Change coupling**:
files that change in the same commits.

**Coupling strength (connascence)**, weakest to strongest: name, type, meaning,
position, algorithm, execution order, timing, identity. Prefer the weakest
form, and keep strong forms inside one module.

## Tests

- **Deletion test**: imagine deleting the module and inlining it at its
  callers. Complexity concentrates → the module earns its place. Complexity
  just moves → it is shallow.
- **The interface is the test surface**: tests that must reach past the
  interface mean the interface is wrong.
- **One adapter is a hypothetical seam, two is a real one**: don't add a seam
  for a second implementation that doesn't exist.

## Friction signals

Each signal comes from the `house-rules` skill in killall-craft; cite it in a candidate's `rules`.

- Understanding one concept means bouncing between many small modules.
- Pure functions extracted only for tests, while bugs hide in how they're
  called (no locality).
- A `utils`/`helpers`/`common` module: a domain without a name.
- Global or shared mutable state; classes with mutable fields outside
  adapters.
- Functions taking more than 3–4 arguments instead of a config object.
- Callers depend on a concrete type where an interface belongs.
- Tests that assert on strings or logs, or that can't be written without
  mocks of internals.
- Code reached only by its own tests: delete it.
- Names that disagree with the glossary, or two names for one concept.
- Comments restating the code; docs pinned to file paths that will move.
