Bad test with bad comments

```typescript
// monkeyBuilder.ts
/**
 * A module for building monkeys that jump on any bed provided as a
 * configuration.
 */

/**
 * This function builds a monkey.
 * @param foo - a string
 * @param bar - a number
 * @returns a Monkey
 */
export function buildMonkey(foo: string, bar: number): Monkey {

  // hold the count of monkies
  let countMonkie = 0;
  ...
}

describe("buildMonkey", () => {
  it("works", () => {
    const m = buildMonkey("safe-monkey", 9);
    expect(triggerFall(m).bed).toBe(Bed.Soft);
    // now check the error case
    try {
      triggerFall(buildMonkey("bedless-monkey", 9));
    } catch (e: any) {
      expect(e.message).toBe("no bed configured");
    }
  });
});
```

Good test with a comment that describes the assertion

```typescript
it("falls on a soft bed when dropped from a low height", () => {
  const monkey = monkeyBuilder().height(9).name("safe-monkey").build();

  const fallen = triggerFall(monkey);

  expect(fallen.bed).toBe(Bed.Soft);
});

it("refuses to drop a monkey when no bed is configured", () => {
  const monkey = monkeyBuilder().height(9).build();

  expect(() => triggerFall(monkey)).toThrow(NoBedError);
});
```
