Bad test with bad comments


```python
# monkey_builder.py
"""
A module for building monkeys that jump on any bed provided as a configuration.
"""

# This function builds a monkey and takes a string, "foo", and a int, "bar" as arguments
def build_monkey(foo: str, bar: int):

    # hold the count of monkies
    count_monkie = 0
```

Good test with a comment that describes the assertion

```python
def test_fall_on_soft_bed():
    """
    It falls on a soft bed when at a low height
    """
    
    mock_monkey = build_monkey().set_height(9).set_name("safe-monkey").build()

    fallen_monkey = trigger_fall(mock_monkey)

    expect(fallen_monkey.get_bed()).to_be(MonkeyBeds.SOFT)
```