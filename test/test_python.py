import sys
import textwrap
from pathlib import Path

# can be removed if we make `print_docs` an installable module
sys.path.append(str(Path(__file__).parent.parent)) 
import print_docs

def test_plaintext_summary():
    s = textwrap.dedent("""
    # Quaternions

    In this file we define quaternions `ℍ[R]` over a commutative ring `R`, and define some
    algebraic structures on `ℍ[R]`.

    ## Main definitions

    * `quaternion_algebra R a b`, `ℍ[R, a, b]` :
    [quaternion algebra](https://en.wikipedia.org/wiki/Quaternion_algebra) with coefficients `a`, `b`
    * `quaternion R`, `ℍ[R]` : the space of quaternions, a.k.a. `quaternion_algebra R (-1) (-1)`;
    * `quaternion.norm_sq` : square of the norm of a quaternion;
    * `quaternion.conj` : conjugate of a quaternion;

    We also define the following algebraic structures on `ℍ[R]`:

    * `ring ℍ[R, a, b]` and `algebra R ℍ[R, a, b]` : for any commutative ring `R`;
    * `ring ℍ[R]` and `algebra R ℍ[R]` : for any commutative ring `R`;
    * `domain ℍ[R]` : for a linear ordered commutative ring `R`;
    * `division_algebra ℍ[R]` : for a linear ordered field `R`.""")
    expected = (
        "Quaternions: In this file we define quaternions `ℍ[R]` over a commutative ring `R`, and "
        "define some algebraic structures on `ℍ[R]`. Main definitions: `quaternion_algebra R a b`, "
        "`ℍ[R, a, b]` : quaternion algebra with coefficients `a`, `b`; `quaternion R`, `ℍ[R]` : "
        "the space of quaternions, a.k.a. `quaternion_algebra R (-1) (-1)`; `quaternion.norm_sq` : "
        "square of the norm of a quaternion; `quaternion.conj` : conjugate of a quaternion; We "
        "also define the following algebraic structures on `ℍ[R]`: `ring ℍ[R, a, b]` and "
        "`algebra R ℍ[R, a, b]` : for any commutative ring `R`; `ring ℍ[R]` and `algebra R ℍ[R]` : "
        "for any commutative ring `R`; `domain ℍ[R]` : for a linear ordered commutative ring `R`; "
        "`division_algebra ℍ[R]` : for a linear ordered field `R`.")
    assert print_docs.plaintext_summary(s, max_chars=sys.maxsize) == expected
