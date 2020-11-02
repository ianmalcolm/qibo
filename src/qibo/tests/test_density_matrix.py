import numpy as np
import pytest
import qibo
from qibo import models, gates, callbacks
from qibo.tests.utils import random_density_matrix
# use native gates in this test because density matrices are not
# supported by custom gate kernels.


_BACKENDS = ["custom", "defaulteinsum", "matmuleinsum"]
_EINSUM_BACKENDS = ["defaulteinsum", "matmuleinsum"]
_atol = 1e-8


@pytest.mark.parametrize("backend", _BACKENDS)
def test_xgate_application_onequbit(backend):
    """Check applying one qubit gate to one qubit density matrix."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    initial_rho = random_density_matrix(1)
    gate = gates.X(0)
    gate.density_matrix = True
    final_rho = gate(initial_rho).numpy()

    pauliX = np.array([[0, 1], [1, 0]])
    target_rho = pauliX.dot(initial_rho).dot(pauliX)

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_hgate_application_twoqubit(backend):
    """Check applying one qubit gate to two qubit density matrix."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    initial_rho = random_density_matrix(2)
    gate = gates.H(1)
    gate.density_matrix = True
    final_rho = gate(initial_rho.reshape(4 * (2,))).numpy().reshape((4, 4))

    matrix = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    matrix = np.kron(np.eye(2), matrix)
    target_rho = matrix.dot(initial_rho).dot(matrix)

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_rygate_application_twoqubit(backend):
    """Check applying non-hermitian one qubit gate to one qubit density matrix."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    theta = 0.1234
    initial_rho = random_density_matrix(1)

    gate = gates.RY(0, theta=theta)
    gate.nqubits = 1
    gate.density_matrix = True
    final_rho = gate(initial_rho).numpy()

    phase = np.exp(1j * theta / 2.0)
    matrix = phase * np.array([[phase.real, -phase.imag], [phase.imag, phase.real]])
    target_rho = matrix.dot(initial_rho).dot(matrix.T.conj())

    np.testing.assert_allclose(final_rho, target_rho, atol=_atol)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", ["matmuleinsum"])
def test_cu1gate_application_twoqubit(backend):
    """Check applying two qubit gate to three qubit density matrix."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    theta = 0.1234
    nqubits = 3
    initial_rho = random_density_matrix(nqubits)

    gate = gates.CU1(0, 1, theta=theta)
    gate.density_matrix = True
    final_rho = initial_rho.reshape(2 * nqubits * (2,))
    final_rho = gate(final_rho).numpy().reshape(initial_rho.shape)

    matrix = np.eye(4, dtype=np.complex128)
    matrix[3, 3] = np.exp(1j * theta)
    matrix = np.kron(matrix, np.eye(2))
    target_rho = matrix.dot(initial_rho).dot(matrix.T.conj())

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


def test_flatten_density_matrix():
    """Check ``Flatten`` gate works with density matrices."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    target_rho = random_density_matrix(3)
    initial_rho = np.zeros(6 * (2,))
    gate = gates.Flatten(target_rho)
    gate.density_matrix = True
    final_rho = gate(initial_rho).numpy().reshape((8, 8))
    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_circuit_compiled(backend):
    """Check passing density matrix as initial state to a compiled circuit."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    theta = 0.1234
    initial_rho = random_density_matrix(3)

    c = models.Circuit(3, density_matrix=True)
    c.add(gates.H(0))
    c.add(gates.H(1))
    c.add(gates.CNOT(0, 1))
    c.add(gates.H(2))
    final_rho = c(initial_rho).numpy().reshape(initial_rho.shape)

    h = np.array([[1, 1], [1, -1]]) / np.sqrt(2)
    cnot = np.array([[1, 0, 0, 0], [0, 1, 0, 0],
                     [0, 0, 0, 1], [0, 0, 1, 0]])
    m1 = np.kron(np.kron(h, h), np.eye(2))
    m2 = np.kron(cnot, np.eye(2))
    m3 = np.kron(np.eye(4), h)
    target_rho = m1.dot(initial_rho).dot(m1.T.conj())
    target_rho = m2.dot(target_rho).dot(m2.T.conj())
    target_rho = m3.dot(target_rho).dot(m3.T.conj())

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_circuit(backend):
    """Check passing density matrix as initial state to circuit."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    theta = 0.1234
    initial_rho = random_density_matrix(3)

    c = models.Circuit(3, density_matrix=True)
    c.add(gates.X(2))
    c.add(gates.CU1(0, 1, theta=theta))
    final_rho = c(initial_rho).numpy().reshape(initial_rho.shape)

    m1 = np.kron(np.eye(4), np.array([[0, 1], [1, 0]]))
    m2 = np.eye(4, dtype=np.complex128)
    m2[3, 3] = np.exp(1j * theta)
    m2 = np.kron(m2, np.eye(2))
    target_rho = m1.dot(initial_rho).dot(m1)
    target_rho = m2.dot(target_rho).dot(m2.T.conj())

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_controlled_by_simple(backend):
    """Check controlled_by method on gate."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    psi = np.zeros(4)
    psi[0] = 1
    initial_rho = np.outer(psi, psi.conj())

    c = models.Circuit(2, density_matrix=True)
    c.add(gates.X(0))
    c.add(gates.Y(1).controlled_by(0))
    final_rho = c(np.copy(initial_rho)).numpy()

    c = models.Circuit(2, density_matrix=True)
    c.add(gates.X(0))
    c.add(gates.Y(1))
    target_rho = c(np.copy(initial_rho)).numpy()

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_controlled_by_no_effect(backend):
    """Check controlled_by SWAP that should not be applied."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    psi = np.zeros(2 ** 4)
    psi[0] = 1
    initial_rho = np.outer(psi, psi.conj())

    c = models.Circuit(4, density_matrix=True)
    c.add(gates.X(0))
    c.add(gates.SWAP(1, 3).controlled_by(0, 2))
    final_rho = c(np.copy(initial_rho)).numpy()

    c = models.Circuit(4, density_matrix=True)
    c.add(gates.X(0))
    target_rho = c(np.copy(initial_rho)).numpy()

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_controlled_with_effect(backend):
    """Check controlled_by SWAP that should be applied."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    psi = np.zeros(2 ** 4)
    psi[0] = 1
    initial_rho = np.outer(psi, psi.conj())

    c = models.Circuit(4, density_matrix=True)
    c.add(gates.X(0))
    c.add(gates.X(2))
    c.add(gates.SWAP(1, 3).controlled_by(0, 2))
    final_rho = c(np.copy(initial_rho)).numpy()

    c = models.Circuit(4, density_matrix=True)
    c.add(gates.X(0))
    c.add(gates.X(2))
    c.add(gates.SWAP(1, 3))
    target_rho = c(np.copy(initial_rho)).numpy()

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_bitflip_noise(backend):
    """Test `gates.NoiseChannel` on random initial density matrix."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    initial_rho = random_density_matrix(2)

    c = models.Circuit(2, density_matrix=True)
    c.add(gates.NoiseChannel(1, px=0.3))
    final_rho = c(np.copy(initial_rho)).numpy()

    c = models.Circuit(2, density_matrix=True)
    c.add(gates.X(1))
    target_rho = 0.3 * c(np.copy(initial_rho)).numpy()
    target_rho += 0.7 * initial_rho.reshape(target_rho.shape)

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_circuit_switch_to_density_matrix(backend):
    """Test that using `gates.NoiseChnanel` switches vector to density matrix."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    c = models.Circuit(2, density_matrix=True)
    c.add(gates.H(0))
    c.add(gates.H(1))
    c.add(gates.NoiseChannel(0, px=0.5))
    c.add(gates.NoiseChannel(1, pz=0.3))
    final_rho = c().numpy()

    psi = np.ones(4) / 2
    initial_rho = np.outer(psi, psi.conj())
    c = models.Circuit(2, density_matrix=True)
    c.add(gates.NoiseChannel(0, px=0.5))
    c.add(gates.NoiseChannel(1, pz=0.3))
    target_rho = c(initial_rho).numpy()

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_circuit_reexecution(backend):
    """Test re-executing a circuit with `gates.NoiseChnanel`."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    c = models.Circuit(2, density_matrix=True)
    c.add(gates.H(0))
    c.add(gates.H(1))
    c.add(gates.NoiseChannel(0, px=0.5))
    c.add(gates.NoiseChannel(1, pz=0.3))
    final_rho = c().numpy()
    final_rho2 = c().numpy()
    np.testing.assert_allclose(final_rho, final_rho2)
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_general_channel(backend):
    """Test `gates.GeneralChannel`."""
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    initial_rho = random_density_matrix(2)

    c = models.Circuit(2, density_matrix=True)
    a1 = np.sqrt(0.4) * np.array([[0, 1], [1, 0]])
    a2 = np.sqrt(0.6) * np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
    gate = gates.GeneralChannel([((1,), a1), ((0, 1), a2)])
    assert gate.target_qubits == (0, 1)
    c.add(gate)
    final_rho = c(np.copy(initial_rho)).numpy()

    m1 = np.kron(np.eye(2), a1)
    m2 = a2
    target_rho = (m1.dot(initial_rho).dot(m1.conj().T) +
                  m2.dot(initial_rho).dot(m2.conj().T))

    np.testing.assert_allclose(final_rho, target_rho)
    qibo.set_backend(original_backend)


def test_controlled_by_channel():
    """Test that attempting to control channels raises error."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    c = models.Circuit(2, density_matrix=True)
    with pytest.raises(ValueError):
        c.add(gates.NoiseChannel(0, px=0.5).controlled_by(1))

    a1 = np.sqrt(0.4) * np.array([[0, 1], [1, 0]])
    a2 = np.sqrt(0.6) * np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1],
                                  [0, 0, 1, 0]])
    config = [((1,), a1), ((0, 1), a2)]
    with pytest.raises(ValueError):
        gate = gates.GeneralChannel(config).controlled_by(1)
    qibo.set_backend(original_backend)


def test_krauss_operator_bad_shape():
    """Test that defining a Krauss operator with wrong shape raises error."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    a1 = np.sqrt(0.4) * np.array([[0, 1], [1, 0]])
    with pytest.raises(ValueError):
        gate = gates.GeneralChannel([((0, 1), a1)])
    qibo.set_backend(original_backend)


def test_circuit_with_noise_gates():
    """Check that ``circuit.with_noise()`` adds the proper noise channels."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    c = models.Circuit(2, density_matrix=True)
    c.add([gates.H(0), gates.H(1), gates.CNOT(0, 1)])
    noisy_c = c.with_noise((0.1, 0.2, 0.3))

    assert noisy_c.depth == 5
    assert noisy_c.ngates == 9
    from qibo.tensorflow import gates as native_gates
    for i in [1, 2, 4, 5, 7, 8]:
        assert isinstance(noisy_c.queue[i], native_gates.NoiseChannel)
    qibo.set_backend(original_backend)


def test_circuit_with_noise_execution():
    """Check ``circuit.with_noise()`` execution."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    c = models.Circuit(2, density_matrix=True)
    c.add([gates.H(0), gates.H(1)])
    noisy_c = c.with_noise((0.1, 0.2, 0.3))

    target_c = models.Circuit(2, density_matrix=True)
    target_c.add(gates.H(0))
    target_c.add(gates.NoiseChannel(0, 0.1, 0.2, 0.3))
    target_c.add(gates.NoiseChannel(1, 0.1, 0.2, 0.3))
    target_c.add(gates.H(1))
    target_c.add(gates.NoiseChannel(0, 0.1, 0.2, 0.3))
    target_c.add(gates.NoiseChannel(1, 0.1, 0.2, 0.3))

    final_state = noisy_c().numpy()
    target_state = target_c().numpy()
    np.testing.assert_allclose(target_state, final_state)
    qibo.set_backend(original_backend)


def test_circuit_with_noise_with_measurements():
    """Check ``circuit.with_noise() when using measurement noise."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    c = models.Circuit(2, density_matrix=True)
    c.add([gates.H(0), gates.H(1)])
    c.add(gates.M(0))
    noisy_c = c.with_noise(3 * (0.1,), measurement_noise = (0.3, 0.0, 0.0))

    target_c = models.Circuit(2, density_matrix=True)
    target_c.add(gates.H(0))
    target_c.add(gates.NoiseChannel(0, 0.1, 0.1, 0.1))
    target_c.add(gates.NoiseChannel(1, 0.1, 0.1, 0.1))
    target_c.add(gates.H(1))
    target_c.add(gates.NoiseChannel(0, 0.3, 0.0, 0.0))
    target_c.add(gates.NoiseChannel(1, 0.1, 0.1, 0.1))

    final_state = noisy_c().numpy()
    target_state = target_c().numpy()
    np.testing.assert_allclose(target_state, final_state)
    qibo.set_backend(original_backend)


def test_circuit_with_noise_noise_map():
    """Check ``circuit.with_noise() when giving noise map."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    noise_map = {0: (0.1, 0.2, 0.1), 1: (0.2, 0.3, 0.0),
                 2: (0.0, 0.0, 0.0)}

    c = models.Circuit(3, density_matrix=True)
    c.add([gates.H(0), gates.H(1), gates.X(2)])
    c.add(gates.M(2))
    noisy_c = c.with_noise(noise_map, measurement_noise = (0.3, 0.0, 0.0))

    target_c = models.Circuit(3, density_matrix=True)
    target_c.add(gates.H(0))
    target_c.add(gates.NoiseChannel(0, 0.1, 0.2, 0.1))
    target_c.add(gates.NoiseChannel(1, 0.2, 0.3, 0.0))
    target_c.add(gates.H(1))
    target_c.add(gates.NoiseChannel(0, 0.1, 0.2, 0.1))
    target_c.add(gates.NoiseChannel(1, 0.2, 0.3, 0.0))
    target_c.add(gates.X(2))
    target_c.add(gates.NoiseChannel(0, 0.1, 0.2, 0.1))
    target_c.add(gates.NoiseChannel(1, 0.2, 0.3, 0.0))
    target_c.add(gates.NoiseChannel(2, 0.3, 0.0, 0.0))

    final_state = noisy_c().numpy()
    target_state = target_c().numpy()
    np.testing.assert_allclose(target_state, final_state)
    qibo.set_backend(original_backend)


def test_circuit_with_noise_noise_map_exceptions():
    """Check that proper exceptions are raised when noise map is invalid."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    c = models.Circuit(2, density_matrix=True)
    c.add([gates.H(0), gates.H(1)])
    with pytest.raises(ValueError):
        noisy_c = c.with_noise((0.2, 0.3))
    with pytest.raises(ValueError):
        noisy_c = c.with_noise({0: (0.2, 0.3, 0.1), 1: (0.3, 0.1)})
    with pytest.raises(ValueError):
        noisy_c = c.with_noise({0: (0.2, 0.3, 0.1)})
    with pytest.raises(TypeError):
        noisy_c = c.with_noise({0, 1})
    with pytest.raises(ValueError):
        noisy_c = c.with_noise((0.2, 0.3, 0.1),
                               measurement_noise=(0.5, 0.0, 0.0))
    qibo.set_backend(original_backend)


def test_circuit_with_noise_exception():
    """Check that calling ``with_noise`` in a noisy circuit raises error."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    c = models.Circuit(2, density_matrix=True)
    c.add([gates.H(0), gates.H(1), gates.NoiseChannel(0, px=0.2)])
    with pytest.raises(ValueError):
        noisy_c = c.with_noise((0.2, 0.3, 0.0))
    qibo.set_backend(original_backend)


def test_density_matrix_measurement():
    """Check measurement gate on density matrices."""
    from qibo.tests.test_measurements import assert_results
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    state = np.zeros(4)
    state[2] = 1
    rho = np.outer(state, state.conj())
    mgate = gates.M(0, 1)
    mgate.density_matrix = True
    result = mgate(rho, nshots=100)

    target_binary_samples = np.zeros((100, 2))
    target_binary_samples[:, 0] = 1
    assert_results(result,
                   decimal_samples=2 * np.ones((100,)),
                   binary_samples=target_binary_samples,
                   decimal_frequencies={2: 100},
                   binary_frequencies={"10": 100})
    qibo.set_backend(original_backend)


@pytest.mark.parametrize("backend", _EINSUM_BACKENDS)
def test_density_matrix_circuit_measurement(backend):
    """Check measurement gate on density matrices using circuit."""
    from qibo.tests.test_measurements import assert_results
    from qibo.tests.test_measurements import assert_register_results
    original_backend = qibo.get_backend()
    qibo.set_backend(backend)
    state = np.zeros(16)
    state[0] = 1
    init_rho = np.outer(state, state.conj())

    c = models.Circuit(4, density_matrix=True)
    c.add(gates.X(1))
    c.add(gates.X(3))
    c.add(gates.M(0, 1, register_name="A"))
    c.add(gates.M(3, 2, register_name="B"))
    result = c(init_rho, nshots=100)

    target_binary_samples = np.zeros((100, 4))
    target_binary_samples[:, 1] = 1
    target_binary_samples[:, 2] = 1
    assert_results(result,
                   decimal_samples=6 * np.ones((100,)),
                   binary_samples=target_binary_samples,
                   decimal_frequencies={6: 100},
                   binary_frequencies={"0110": 100})

    target = {}
    target["decimal_samples"] = {"A": np.ones((100,)),
                                 "B": 2 * np.ones((100,))}
    target["binary_samples"] = {"A": np.zeros((100, 2)),
                                "B": np.zeros((100, 2))}
    target["binary_samples"]["A"][:, 1] = 1
    target["binary_samples"]["B"][:, 0] = 1
    target["decimal_frequencies"] = {"A": {1: 100}, "B": {2: 100}}
    target["binary_frequencies"] = {"A": {"01": 100}, "B": {"10": 100}}
    assert_register_results(result, **target)
    qibo.set_backend(original_backend)


def test_entanglement_entropy():
    """Check that entanglement entropy calculation works for density matrices."""
    original_backend = qibo.get_backend()
    qibo.set_backend("matmuleinsum")
    rho = random_density_matrix(4)
    # this rho is not always positive. Make rho positive for this application
    _, u = np.linalg.eigh(rho)
    rho = u.dot(np.diag(5 * np.random.random(u.shape[0]))).dot(u.conj().T)
    # this is a positive rho

    entropy = callbacks.EntanglementEntropy([0, 2])
    final_ent = entropy(rho, is_density_matrix=True)

    rho = rho.reshape(8 * (2,))
    reduced_rho = np.einsum("abcdafch->bdfh", rho).reshape((4, 4))
    eigvals = np.linalg.eigvalsh(reduced_rho).real
    # assert that all eigenvalues are non-negative
    assert (eigvals >= 0).prod()
    mask = eigvals > 0
    target_ent = - (eigvals[mask] * np.log2(eigvals[mask])).sum()

    np.testing.assert_allclose(final_ent, target_ent)
    qibo.set_backend(original_backend)
