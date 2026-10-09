Bad test with bad comments

```rust
// monkey_builder.rs
//! A module for building monkeys that jump on any bed provided as a
//! configuration.

/// This function builds a monkey and takes a `&str`, `foo`, and a `u32`,
/// `bar`, as arguments. Returns a Result.
pub fn build_monkey(foo: &str, bar: u32) -> Result<Monkey, MonkeyError> {

    // hold the count of monkies
    let mut count_monkie = 0;
    ...
}

#[test]
fn test_monkey() {
    let m = build_monkey("safe-monkey", 9).unwrap();
    let f = trigger_fall(m);
    assert!(f.bed() == Bed::Soft, "bad bed");
    // now check the error case
    let e = build_monkey("bedless-monkey", 9).unwrap_err();
    assert_eq!(e.to_string(), "no bed configured");
}
```

Good test with a comment that describes the assertion

```rust
#[test]
fn falls_on_soft_bed() {
    // It falls on a soft bed when dropped from a low height
    let monkey = Monkey::builder().height(9).name("safe-monkey").build();

    let fallen = trigger_fall(monkey);

    assert_eq!(fallen.bed(), Bed::Soft);
}

#[test]
fn refuses_to_fall_without_a_bed() {
    // It refuses to drop a monkey when no bed is configured
    let monkey = Monkey::builder().height(9).build();

    let err = trigger_fall(monkey).unwrap_err();

    assert!(matches!(err, MonkeyError::NoBed));
}
```
