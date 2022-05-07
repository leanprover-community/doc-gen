/- A short example to test the behavior of `get_instances`. -/
import export_json

class tc_explicit (x : Type*) (v : x).
class tc_implicit {x : Type*} (v : x).

structure foo := (n : ℕ)

instance foo.tc_explicit : tc_explicit foo ⟨1⟩ := ⟨⟩

instance foo.tc_implicit : tc_implicit (⟨1⟩ : foo) := ⟨⟩

def foo.some_prop (b : foo) : Prop := true

def some_set : set ℕ := {1}

instance some_set.tc_implicit : tc_implicit ↥some_set := ⟨⟩

instance : decidable_pred foo.some_prop := λ x, decidable.true

#eval do
  (fwd, rev) ← get_instances,
  guard (rev.find "foo.some_prop" = ["foo.some_prop.decidable_pred"]),
  guard (rev.find "foo" = ["foo.has_sizeof_inst", "foo.tc_explicit"]),
  guard (rev.find "foo" = ["foo.has_sizeof_inst", "foo.tc_explicit"]),
  guard (rev.find "↥some_set" = ["some_set.tc_implicit"])
