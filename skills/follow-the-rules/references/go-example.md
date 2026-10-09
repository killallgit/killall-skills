Bad test with bad comments

```go
// monkey_builder.go

// Package monkey is a package for building monkeys that jump on any bed
// provided as a configuration.
package monkey

// BuildMonkey builds a monkey. It takes a string, foo, and an int, bar, and
// returns a Monkey and an error.
func BuildMonkey(foo string, bar int) (*Monkey, error) {

	// hold the count of monkies
	countMonkie := 0
	...
}

// TestBuildMonkey1 tests the build monkey function
func TestBuildMonkey1(t *testing.T) {
	m, err := BuildMonkey("safe-monkey", 9)
	if err != nil && err.Error() != "bed is missing" {
		t.Fatal("it broke")
	}
	f := TriggerFall(m)
	if f.Bed() != BedSoft {
		t.Fatal("bad bed")
	}
	// now check a tall one
	m2, _ := BuildMonkey("doomed-monkey", 400)
	if TriggerFall(m2).Bed() != BedHard {
		t.Fatal("bad bed")
	}
}
```

Good test with a comment that describes the assertion

```go
func TestFallOnSoftBed(t *testing.T) {
	// It falls on a soft bed when dropped from a low height
	monkey := NewMonkey().WithHeight(9).WithName("safe-monkey").Build()

	fallen := TriggerFall(monkey)

	if got := fallen.Bed(); got != BedSoft {
		t.Errorf("Bed() = %v, want %v", got, BedSoft)
	}
}

func TestFallWithoutBed(t *testing.T) {
	// It refuses to drop a monkey when no bed is configured
	monkey := NewMonkey().WithHeight(9).Build()

	_, err := TriggerFallOrErr(monkey)

	if !errors.Is(err, ErrNoBed) {
		t.Errorf("err = %v, want %v", err, ErrNoBed)
	}
}
```
