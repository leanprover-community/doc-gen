/-
A short example to test the behavior of `get_instances`.
To actually test this, paste this code above the `HACK` lines in `export_json.lean`, as after those
lines notation becomes badly broken.
-/

class tc_explicit (x : Type*) (v : x).
class tc_implicit {x : Type*} (v : x).

structure foo := (n : ℕ)

instance foo.tc_explicit : tc_explicit foo ⟨1⟩ := ⟨⟩

instance foo.tc_implicit : tc_implicit (⟨1⟩ : foo) := ⟨⟩

def foo.some_prop (b : foo) : Prop := true

instance : decidable_pred foo.some_prop := λ x, decidable.true

#eval do
  (fwd, rev) ← get_instances,
  guard (rev.find "foo.some_prop" = ["foo.some_prop.decidable_pred"]),
  guard (rev.find "foo" = ["foo.has_sizeof_inst", "foo.tc_explicit"])